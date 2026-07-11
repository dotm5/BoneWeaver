"""Strict, read-only preflight for REST_ONLY_STRICT analysis."""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix

from .armature_reader import read_bone_states, resolve_active_armature, resolve_scope_names
from .mesh_resolver import find_associated_meshes
from .models import PreflightResult, ValidationIssue


def _issue(severity, code, message, *, bones=(), objects=()):
    return ValidationIssue(severity, code, code.lower(), message, tuple(bones), tuple(objects))


def _is_identity(matrix, epsilon=1.0e-7):
    identity = Matrix.Identity(4)
    return all(abs(matrix[row][column] - identity[row][column]) <= epsilon for row in range(4) for column in range(4))


def run_preflight(context) -> PreflightResult:
    issues = []
    armature = resolve_active_armature(context)
    if armature is None:
        return PreflightResult(None, None, (), (), (), (_issue("BLOCKER", "UECP_NO_ACTIVE_ARMATURE", "No active Armature"),))

    if armature.library or armature.data.library:
        issues.append(_issue("BLOCKER", "UECP_LINKED_ARMATURE", "Armature is linked and not editable", objects=(armature.name,)))
    if armature.data.users > 1:
        issues.append(_issue("BLOCKER", "UECP_SHARED_ARMATURE_DATA", "Armature data has multiple object users", objects=(armature.name,)))

    determinant = armature.matrix_world.to_3x3().determinant()
    if not math.isfinite(determinant) or abs(determinant) <= 1.0e-12:
        issues.append(_issue("BLOCKER", "UECP_NON_INVERTIBLE_TRANSFORM", "Armature transform is not invertible", objects=(armature.name,)))
    elif determinant < 0.0:
        issues.append(_issue("BLOCKER", "UECP_NEGATIVE_OBJECT_TRANSFORM", "Armature transform has negative determinant", objects=(armature.name,)))
    scales = tuple(abs(float(value)) for value in armature.scale)
    if max(scales) - min(scales) > 1.0e-7:
        issues.append(_issue("WARNING", "UECP_NON_UNIFORM_OBJECT_SCALE", "Armature has non-uniform scale", objects=(armature.name,)))

    settings = getattr(context.scene, "uecp_settings", None)
    scope_mode = settings.scope_mode if settings else "SELECTED_BONES"
    selected = resolve_scope_names(context, armature, scope_mode)
    if not selected:
        issues.append(_issue("BLOCKER", "UECP_EMPTY_SELECTION", "No target bones are selected", objects=(armature.name,)))

    states = ()
    if selected:
        try:
            states = read_bone_states(armature, selected)
        except (KeyError, ValueError, OverflowError) as error:
            issues.append(_issue("BLOCKER", "UECP_UNSUPPORTED_CONTEXT", str(error), objects=(armature.name,)))

    selected_set = set(selected)
    for name in selected:
        bone = armature.data.bones[name]
        if bone.bbone_segments > 1:
            issues.append(_issue("BLOCKER", "UECP_BBONE_UNSUPPORTED", "B-Bone segments are unsupported", bones=(name,)))
        for child in bone.children:
            if child.name not in selected_set and child.use_connect:
                issues.append(_issue("BLOCKER", "UECP_EXTERNAL_CONNECTED_CHILD", "Unselected connected child would be moved", bones=(name, child.name)))
            if child.name in selected_set and (child.head_local - bone.head_local).length <= 1.0e-7:
                issues.append(_issue("BLOCKER", "UECP_COINCIDENT_HELPER", "Parent and child heads coincide", bones=(name, child.name)))
        pose_bone = armature.pose.bones.get(name)
        if pose_bone:
            if pose_bone.constraints:
                issues.append(_issue("BLOCKER", "UECP_RELATED_CONSTRAINT", "Target bone has constraints", bones=(name,)))
            if not _is_identity(pose_bone.matrix_basis):
                issues.append(_issue("BLOCKER", "UECP_NON_IDENTITY_POSE", "Armature pose is not identity", bones=(name,)))

    animation = armature.animation_data
    if animation:
        if animation.action:
            issues.append(_issue("BLOCKER", "UECP_RELATED_ACTION", "Armature has an active Action", objects=(armature.name,)))
        if animation.nla_tracks:
            issues.append(_issue("BLOCKER", "UECP_RELATED_NLA", "Armature has NLA tracks", objects=(armature.name,)))
        if animation.drivers:
            issues.append(_issue("BLOCKER", "UECP_RELATED_DRIVER", "Armature has drivers", objects=(armature.name,)))

    for obj in bpy.data.objects:
        if obj.parent == armature and obj.parent_type == "BONE" and obj.parent_bone in selected_set:
            issues.append(_issue("BLOCKER", "UECP_BONE_PARENTED_OBJECT", "Object is parented to a target bone", bones=(obj.parent_bone,), objects=(obj.name,)))
        for constraint in obj.constraints:
            if getattr(constraint, "target", None) == armature and getattr(constraint, "subtarget", "") in selected_set:
                issues.append(_issue("BLOCKER", "UECP_RELATED_CONSTRAINT", "Object constraint targets a selected bone", objects=(obj.name,)))

    bindings, mesh_issues = find_associated_meshes(armature)
    issues.extend(mesh_issues)
    if not bindings:
        issues.append(_issue("BLOCKER", "UECP_NO_ASSOCIATED_MESH", "No associated Mesh was found", objects=(armature.name,)))
    for binding in bindings:
        mesh = bpy.data.objects[binding.object_name]
        modifier = mesh.modifiers[binding.modifier_name]
        if modifier.use_bone_envelopes:
            issues.append(_issue("BLOCKER", "UECP_ENVELOPE_DEFORMATION", "Armature modifier uses bone envelopes", objects=(mesh.name,)))
        for prior in mesh.modifiers[: mesh.modifiers.find(modifier.name)]:
            if prior.type in {"MIRROR", "ARRAY", "SUBSURF", "REMESH", "NODES", "BOOLEAN", "SKIN"}:
                issues.append(_issue("BLOCKER", "UECP_TOPOLOGY_MODIFIER_BEFORE_ARMATURE", "Topology modifier precedes Armature modifier", objects=(mesh.name,)))
                break

    issues.sort(key=lambda item: ({"BLOCKER": 0, "WARNING": 1, "INFO": 2}.get(item.severity, 3), item.code, item.bone_names, item.object_names))
    return PreflightResult(armature.name, armature.data.name, selected, tuple(binding.object_name for binding in bindings), states, tuple(issues))
