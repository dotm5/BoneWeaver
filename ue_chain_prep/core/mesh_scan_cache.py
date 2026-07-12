"""One-operation shared mesh scan for digests and weight evidence."""

from __future__ import annotations

import hashlib
import math
import struct
import time
from array import array
from dataclasses import dataclass

from .canonical import sha256
from .weight_islands import CompactPerMeshWeightedInput


def _modifier_digest(mesh_obj):
    return sha256(
        tuple(
            (
                modifier.name,
                modifier.type,
                getattr(getattr(modifier, "object", None), "name", None),
                getattr(modifier, "use_vertex_groups", None),
                getattr(modifier, "use_bone_envelopes", None),
                getattr(modifier, "use_deform_preserve_volume", None),
                modifier.show_viewport,
            )
            for modifier in mesh_obj.modifiers
        )
    )


def _update_vertex_digests(base_digest, weight_digest, vertex, group_names):
    base_digest.update(struct.pack("<Q3d", vertex.index, *(float(value) for value in vertex.co)))
    weight_digest.update(struct.pack("<Q", vertex.index))
    for membership in sorted(vertex.groups, key=lambda item: group_names.get(item.group, "")):
        name = group_names.get(membership.group, "").encode("utf-8")
        weight_digest.update(struct.pack("<I", len(name)))
        weight_digest.update(name)
        weight_digest.update(struct.pack("<f", float(membership.weight)))


def _finish_base_digest(base_digest, mesh):
    for edge in mesh.edges:
        first, second = sorted(tuple(edge.vertices))
        base_digest.update(struct.pack("<2Q", first, second))
    for polygon in mesh.polygons:
        vertices = tuple(int(index) for index in polygon.vertices)
        base_digest.update(struct.pack("<I", len(vertices)))
        for index in vertices:
            base_digest.update(struct.pack("<Q", index))


def mesh_digest_pair(mesh_obj):
    """Compute weight and base-coordinate digests in one full vertex pass."""
    mesh = mesh_obj.data
    base_digest = hashlib.sha256(b"UECP_BASE_MESH_V2")
    weight_digest = hashlib.sha256()
    group_names = {group.index: group.name for group in mesh_obj.vertex_groups}
    for vertex in mesh.vertices:
        _update_vertex_digests(base_digest, weight_digest, vertex, group_names)
    _finish_base_digest(base_digest, mesh)
    return weight_digest.hexdigest(), base_digest.hexdigest()


def _compact_topology(mesh):
    """Build a shared CSR adjacency index once for every bone on this mesh."""
    vertex_total = len(mesh.vertices)
    degrees = array("I", [0]) * vertex_total
    edge_buffer = array("I")
    for edge in mesh.edges:
        first, second = (int(index) for index in edge.vertices)
        if first > second:
            first, second = second, first
        edge_buffer.extend((first, second))
        degrees[first] += 1
        degrees[second] += 1

    offsets = array("I", [0])
    running = 0
    for degree in degrees:
        running += int(degree)
        offsets.append(running)
    neighbors = array("I", [0]) * running
    cursors = array("I", offsets[:-1])
    for offset in range(0, len(edge_buffer), 2):
        first = int(edge_buffer[offset])
        second = int(edge_buffer[offset + 1])
        neighbors[cursors[first]] = second
        cursors[first] += 1
        neighbors[cursors[second]] = first
        cursors[second] += 1
    working_bytes = sum(
        buffer.buffer_info()[1] * buffer.itemsize
        for buffer in (edge_buffer, degrees, offsets, neighbors, cursors)
    )
    return edge_buffer, offsets, neighbors, working_bytes


@dataclass(frozen=True, slots=True)
class MeshScanResult:
    object_name: str
    data_name: str
    vertex_count: int
    polygon_count: int
    vertex_group_names: tuple[str, ...]
    weight_digest: str
    base_mesh_digest: str
    modifier_digest: str


@dataclass(frozen=True, slots=True)
class MeshScanCache:
    meshes: tuple[MeshScanResult, ...]
    per_mesh_inputs_by_bone: dict[str, tuple[CompactPerMeshWeightedInput, ...]]
    vertex_count: int
    membership_count: int
    vertex_pass_count: int
    membership_pass_count: int
    mesh_scan_time: float
    peak_temporary_memory: int

    @classmethod
    def scan(
        cls,
        armature_obj,
        mesh_objects,
        target_bone_names,
        *,
        minimum_weight,
        weight_exponent,
        use_vertex_area_weight,
        exclusivity_mode,
    ):
        started = time.perf_counter()
        targets = tuple(sorted(set(target_bone_names)))
        per_bone = {name: [] for name in targets}
        scans = []
        vertex_count = membership_count = 0
        peak_memory = 0
        for mesh_obj in mesh_objects:
            mesh = mesh_obj.data
            transform = armature_obj.matrix_world.inverted_safe() @ mesh_obj.matrix_world
            areas = [1.0] * len(mesh.vertices)
            if use_vertex_area_weight and mesh.polygons:
                areas = [0.0] * len(mesh.vertices)
                mesh.calc_loop_triangles()
                for triangle in mesh.loop_triangles:
                    first, second, third = (
                        transform @ mesh.vertices[index].co for index in triangle.vertices
                    )
                    area = (second - first).cross(third - first).length * 0.5
                    for index in triangle.vertices:
                        areas[index] += area / 3.0
            group_names = {group.index: group.name for group in mesh_obj.vertex_groups}
            target_indices = {index: name for index, name in group_names.items() if name in per_bone}
            builders = {
                name: (array("I"), array("d"), array("d"))
                for name in targets
            }
            base_hasher = hashlib.sha256(b"UECP_BASE_MESH_V2")
            weight_hasher = hashlib.sha256()
            for vertex in mesh.vertices:
                vertex_count += 1
                _update_vertex_digests(base_hasher, weight_hasher, vertex, group_names)
                position = transform @ vertex.co
                memberships = []
                for membership in vertex.groups:
                    membership_count += 1
                    name = target_indices.get(membership.group)
                    if name is not None:
                        memberships.append((name, float(membership.weight)))
                denominator = sum(weight for _, weight in memberships)
                for name, raw_weight in memberships:
                    adjusted = max(raw_weight - minimum_weight, 0.0) ** weight_exponent
                    if adjusted <= 0.0:
                        continue
                    exclusivity = (
                        raw_weight / max(denominator, 1.0e-12)
                        if exclusivity_mode in {"CHAIN_NORMALIZED", "SELECTED_SET_NORMALIZED"}
                        else 1.0
                    )
                    statistical_weight = areas[vertex.index] * adjusted * exclusivity
                    if statistical_weight <= 0.0:
                        continue
                    indices, coordinates, weights = builders[name]
                    indices.append(vertex.index)
                    coordinates.extend(float(value) for value in position)
                    weights.append(statistical_weight)
            _finish_base_digest(base_hasher, mesh)
            (
                edge_buffer,
                adjacency_offsets,
                adjacency_neighbors,
                topology_working_bytes,
            ) = _compact_topology(mesh)
            for name, (indices, coordinates, weights) in builders.items():
                if indices:
                    per_bone[name].append(
                        CompactPerMeshWeightedInput(
                            mesh_obj.name,
                            indices,
                            coordinates,
                            weights,
                            edge_buffer,
                            adjacency_offsets,
                            adjacency_neighbors,
                        )
                    )
            builder_bytes = sum(
                indices.buffer_info()[1] * indices.itemsize
                + coordinates.buffer_info()[1] * coordinates.itemsize
                + weights.buffer_info()[1] * weights.itemsize
                for indices, coordinates, weights in builders.values()
            )
            peak_memory = max(
                peak_memory,
                builder_bytes + topology_working_bytes + len(areas) * 8,
            )
            scans.append(
                MeshScanResult(
                    mesh_obj.name,
                    mesh.name,
                    len(mesh.vertices),
                    len(mesh.polygons),
                    tuple(group.name for group in mesh_obj.vertex_groups),
                    weight_hasher.hexdigest(),
                    base_hasher.hexdigest(),
                    _modifier_digest(mesh_obj),
                )
            )
        return cls(
            tuple(scans),
            {name: tuple(inputs) for name, inputs in per_bone.items()},
            vertex_count,
            membership_count,
            len(tuple(mesh_objects)),
            len(tuple(mesh_objects)),
            time.perf_counter() - started,
            peak_memory,
        )
