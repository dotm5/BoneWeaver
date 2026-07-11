"""Streaming digests and deterministic source/settings fingerprints."""

from __future__ import annotations

import hashlib
import struct

from .armature_reader import read_bone_states
from .canonical import sha256
from ..contracts import ALGORITHM_VERSION
from .mesh_scan_cache import mesh_digest_pair


def weight_digest(mesh_obj):
    return mesh_digest_pair(mesh_obj)[0]


def base_mesh_digest(mesh_obj):
    return mesh_digest_pair(mesh_obj)[1]


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
    excluded = {"rna_type", "last_export_directory", "preview_show_joint_graph", "preview_show_virtual_tips", "preview_show_candidate_axes", "preview_show_old_axes", "preview_show_new_axes", "preview_show_weight_centroid", "preview_axis_scale"}
    values = {}
    for prop in settings.bl_rna.properties:
        if prop.identifier in excluded or prop.identifier in {"terminal_overrides", "branch_overrides"} or prop.type == "POINTER":
            continue
        values[prop.identifier] = getattr(settings, prop.identifier)
    values["terminal_overrides"] = tuple(
        (
            item.armature_data_name,
            item.armature_structural_fingerprint,
            item.bone_name,
            item.chain_id,
            item.mode,
            getattr(item.reference_object, "name", None),
            tuple(item.direction),
            item.length,
            item.mesh_object_name,
            item.vertex_index,
            item.enabled,
        )
        for item in settings.terminal_overrides
    )
    values["branch_overrides"] = tuple(
        (
            item.armature_data_name,
            item.armature_structural_fingerprint,
            item.branch_bone_name,
            item.selected_child_name,
            item.enabled,
        )
        for item in settings.branch_overrides
    )
    values["radial_reference_object"] = getattr(settings.radial_reference_object, "name", None)
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
        current_weight_digest, current_base_mesh_digest = mesh_digest_pair(mesh)
        meshes.append((mesh.name, current_weight_digest, current_base_mesh_digest, modifier_digest(mesh)))
    matrix = tuple(float(armature.matrix_world[row][column]) for row in range(4) for column in range(4))
    return sha256((ALGORITHM_VERSION, armature.name, armature.data.name, matrix, states, tuple(meshes)))
