"""Streaming digests and deterministic source/settings fingerprints."""

from __future__ import annotations

import hashlib
import struct

from .armature_reader import read_bone_states
from .canonical import sha256
from ..contracts import ALGORITHM_VERSION


def weight_digest(mesh_obj):
    digest = hashlib.sha256()
    groups = {group.index: group.name for group in mesh_obj.vertex_groups}
    for vertex in mesh_obj.data.vertices:
        digest.update(struct.pack("<Q", vertex.index))
        for membership in sorted(vertex.groups, key=lambda item: groups.get(item.group, "")):
            name = groups.get(membership.group, "").encode("utf-8")
            digest.update(struct.pack("<I", len(name)))
            digest.update(name)
            digest.update(struct.pack("<f", float(membership.weight)))
    return digest.hexdigest()


def base_mesh_digest(mesh_obj):
    return sha256(
        (
            tuple(tuple(float(value) for value in vertex.co) for vertex in mesh_obj.data.vertices),
            tuple(tuple(edge.vertices) for edge in mesh_obj.data.edges),
            tuple(tuple(polygon.vertices) for polygon in mesh_obj.data.polygons),
        )
    )


def modifier_digest(mesh_obj):
    return sha256(
        tuple(
            (
                modifier.name, modifier.type,
                getattr(getattr(modifier, "object", None), "name", None),
                getattr(modifier, "use_vertex_groups", None),
                getattr(modifier, "use_bone_envelopes", None),
                getattr(modifier, "use_deform_preserve_volume", None),
                modifier.show_viewport,
            )
            for modifier in mesh_obj.modifiers
        )
    )


def settings_payload(settings):
    excluded = {"rna_type", "last_export_directory", "preview_show_joint_graph", "preview_show_virtual_tips", "preview_show_candidate_axes", "preview_show_old_axes", "preview_show_new_axes", "preview_show_weight_centroid"}
    values = {}
    for prop in settings.bl_rna.properties:
        if prop.identifier in excluded or prop.identifier == "terminal_overrides" or prop.type == "POINTER":
            continue
        values[prop.identifier] = getattr(settings, prop.identifier)
    values["terminal_overrides"] = tuple(
        (item.bone_name, item.mode, tuple(item.direction), item.length, item.mesh_object_name, item.vertex_index, item.enabled)
        for item in settings.terminal_overrides
    )
    values["algorithm_version"] = ALGORITHM_VERSION
    return values


def settings_fingerprint(settings):
    return sha256(settings_payload(settings))


def source_fingerprint_from_states(armature, bone_states, mesh_states):
    matrix = tuple(float(armature.matrix_world[row][column]) for row in range(4) for column in range(4))
    meshes = tuple(
        (state.object_name, state.vertex_group_digest, state.base_mesh_digest, state.modifier_digest)
        for state in mesh_states
    )
    return sha256((ALGORITHM_VERSION, armature.name, armature.data.name, matrix, bone_states, meshes))


def current_source_fingerprint(context, plan):
    armature = context.scene.objects.get(plan.armature_object_name)
    if armature is None or armature.data.name != plan.armature_data_name:
        return ""
    states = read_bone_states(armature, tuple(state.name for state in plan.bone_states))
    meshes = []
    for expected in plan.mesh_states:
        mesh = context.scene.objects.get(expected.object_name)
        if mesh is None:
            return ""
        meshes.append((mesh.name, weight_digest(mesh), base_mesh_digest(mesh), modifier_digest(mesh)))
    matrix = tuple(float(armature.matrix_world[row][column]) for row in range(4) for column in range(4))
    return sha256((ALGORITHM_VERSION, armature.name, armature.data.name, matrix, states, tuple(meshes)))
