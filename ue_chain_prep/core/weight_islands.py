"""Topology-aware per-mesh weight evidence selection."""

from __future__ import annotations

import math
from array import array
from dataclasses import dataclass

from ..contracts import WeightIslandPolicy
from .models import PerMeshWeightCloudStats, WeightComponentStats


@dataclass(frozen=True, slots=True)
class PerMeshWeightedInput:
    mesh_name: str
    weighted_vertices: tuple[tuple[int, tuple[float, float, float], float], ...]
    edges: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class CompactPerMeshWeightedInput:
    mesh_name: str
    indices: array
    coordinates: array
    weights: array
    edges: array
    adjacency_offsets: array | None = None
    adjacency_neighbors: array | None = None

    def iter_weighted_vertices(self):
        for offset, index in enumerate(self.indices):
            base = offset * 3
            yield (
                int(index),
                (
                    float(self.coordinates[base]),
                    float(self.coordinates[base + 1]),
                    float(self.coordinates[base + 2]),
                ),
                float(self.weights[offset]),
            )

    def iter_edges(self):
        for offset in range(0, len(self.edges), 2):
            yield int(self.edges[offset]), int(self.edges[offset + 1])

    def connected_components(self, eligible):
        """Return induced weighted components without rescanning every mesh edge."""
        if self.adjacency_offsets is None or self.adjacency_neighbors is None:
            return None
        remaining = set(eligible)
        components = []
        while remaining:
            root = min(remaining)
            remaining.remove(root)
            stack = [root]
            component = []
            while stack:
                current = stack.pop()
                component.append(current)
                start = int(self.adjacency_offsets[current])
                end = int(self.adjacency_offsets[current + 1])
                for offset in range(start, end):
                    neighbor = int(self.adjacency_neighbors[offset])
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
            components.append(tuple(sorted(component)))
        return tuple(components)


def _weighted_vertices(source):
    if hasattr(source, "iter_weighted_vertices"):
        return source.iter_weighted_vertices()
    return source.weighted_vertices


def _edges(source):
    if hasattr(source, "iter_edges"):
        return source.iter_edges()
    return source.edges


@dataclass(frozen=True, slots=True)
class WeightIslandResolution:
    bone_name: str
    selected_weighted_points: tuple[tuple[tuple[float, float, float], float], ...]
    per_mesh_clouds: tuple[PerMeshWeightCloudStats, ...]
    warnings: tuple[str, ...]


def _normalize(vector):
    length = math.sqrt(sum(float(value) * float(value) for value in vector))
    return tuple(float(value) / length for value in vector) if length > 1.0e-12 else None


def _component_indices(source, eligible):
    if hasattr(source, "connected_components"):
        components = source.connected_components(eligible)
        if components is not None:
            return components
    eligible = set(eligible)
    adjacency = {index: [] for index in eligible}
    for first, second in _edges(source):
        if first in eligible and second in eligible:
            adjacency[first].append(second)
            adjacency[second].append(first)
    components = []
    remaining = set(eligible)
    while remaining:
        root = min(remaining)
        remaining.remove(root)
        stack = [root]
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(components)


def _weighted_centroid(points):
    total = sum(weight for _, weight in points)
    if total <= 0.0:
        return None
    return tuple(sum(point[index] * weight for point, weight in points) / total for index in range(3))


def _component_direction(head, component):
    if component.principal_axis is not None:
        return _normalize(component.principal_axis)
    if component.centroid is not None:
        return _normalize(tuple(component.centroid[index] - head[index] for index in range(3)))
    return None


def _components_are_compatible(head, components, angle_degrees):
    directions = tuple(_component_direction(head, component) for component in components)
    if any(direction is None for direction in directions):
        return False
    cosine_limit = math.cos(math.radians(angle_degrees))
    return all(
        sum(first[index] * second[index] for index in range(3)) >= cosine_limit
        for first_index, first in enumerate(directions)
        for second in directions[first_index + 1 :]
    )


def _mesh_resolution(
    bone_name,
    head,
    source,
    policy,
    dominant_ratio_threshold,
    compatible_direction_angle_degrees,
):
    from .weight_cloud import analyze_weight_cloud

    by_index = {
        index: (tuple(float(value) for value in point), float(weight))
        for index, point, weight in _weighted_vertices(source)
        if weight > 0.0
    }
    components = []
    component_points = []
    for indices in _component_indices(source, by_index):
        points = tuple(by_index[index] for index in indices)
        cloud = analyze_weight_cloud(bone_name, head, points, (source.mesh_name,))
        components.append(
            WeightComponentStats(
                len(points), sum(weight for _, weight in points),
                _weighted_centroid(points), cloud.principal_axis,
            )
        )
        component_points.append(points)
    if not components:
        return PerMeshWeightCloudStats(source.mesh_name, 0, (), 0.0, None, None, 0.0), (), ()
    ranked = tuple(sorted(range(len(components)), key=lambda index: (-components[index].statistical_weight, index)))
    total = sum(component.statistical_weight for component in components)
    dominant_index = ranked[0]
    dominant_ratio = components[dominant_index].statistical_weight / total if total > 0.0 else 0.0
    warnings = set()
    if policy == WeightIslandPolicy.DOMINANT_COMPONENT.value:
        selected = component_points[dominant_index] if dominant_ratio >= dominant_ratio_threshold else ()
    elif policy == WeightIslandPolicy.REQUIRE_SINGLE_COMPONENT.value:
        selected = component_points[0] if len(components) == 1 else ()
    else:
        compatible = len(components) == 1 or _components_are_compatible(
            head, components, compatible_direction_angle_degrees,
        )
        selected = tuple(point for points in component_points for point in points) if compatible else ()
        if not compatible:
            warnings.add("UECP_WEIGHT_DIRECTION_CONFLICT")
    if len(components) > 1 and not selected:
        warnings.add("UECP_DISCONNECTED_WEIGHT_ISLANDS")
        warnings.add("UECP_WEIGHT_ISLAND_POLICY_BLOCKED")
    selected_cloud = analyze_weight_cloud(bone_name, head, selected, (source.mesh_name,)) if selected else None
    stats = PerMeshWeightCloudStats(
        source.mesh_name,
        len(components),
        tuple(components),
        dominant_ratio,
        _weighted_centroid(selected) if selected else None,
        selected_cloud.principal_axis if selected_cloud else None,
        sum(weight for _, weight in selected),
    )
    return stats, selected, tuple(sorted(warnings))


def _cloud_direction(head, stats):
    if stats.selected_principal_axis is not None:
        return _normalize(stats.selected_principal_axis)
    if stats.selected_centroid is not None:
        return _normalize(tuple(stats.selected_centroid[index] - head[index] for index in range(3)))
    return None


def resolve_weight_islands(
    bone_name,
    head,
    per_mesh_inputs,
    *,
    policy=WeightIslandPolicy.DOMINANT_COMPONENT.value,
    dominant_ratio_threshold=0.70,
    compatible_direction_angle_degrees=45.0,
):
    policy = getattr(policy, "value", policy)
    valid_policies = {item.value for item in WeightIslandPolicy}
    if policy not in valid_policies:
        raise ValueError(f"unsupported weight island policy: {policy}")
    per_mesh = []
    selected_by_mesh = []
    warnings = set()
    for source in sorted(per_mesh_inputs, key=lambda item: item.mesh_name):
        stats, selected, mesh_warnings = _mesh_resolution(
            bone_name,
            head,
            source,
            policy,
            dominant_ratio_threshold,
            compatible_direction_angle_degrees,
        )
        per_mesh.append(stats)
        warnings.update(mesh_warnings)
        if selected:
            selected_by_mesh.append((stats, selected))
    directions = tuple(
        (stats, points, _cloud_direction(head, stats))
        for stats, points in selected_by_mesh
    )
    cosine_limit = math.cos(math.radians(compatible_direction_angle_degrees))
    conflict = (
        len(directions) > 1
        and any(item[2] is None for item in directions)
    ) or any(
        sum(first[2][index] * second[2][index] for index in range(3)) < cosine_limit
        for first_index, first in enumerate(directions)
        if first[2] is not None
        for second in directions[first_index + 1 :]
        if second[2] is not None
    )
    if conflict:
        warnings.add("UECP_WEIGHT_DIRECTION_CONFLICT")
        total = sum(stats.selected_statistical_weight for stats, _ in selected_by_mesh)
        dominant = max(selected_by_mesh, key=lambda item: (item[0].selected_statistical_weight, item[0].mesh_name))
        ratio = dominant[0].selected_statistical_weight / total if total > 0.0 else 0.0
        selected_points = dominant[1] if ratio >= dominant_ratio_threshold else ()
    else:
        selected_points = tuple(point for _, points in selected_by_mesh for point in points)
    return WeightIslandResolution(
        bone_name,
        tuple(selected_points),
        tuple(per_mesh),
        tuple(sorted(warnings)),
    )
