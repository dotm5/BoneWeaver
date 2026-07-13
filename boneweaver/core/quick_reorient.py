"""Whole-armature UEFormat-parity reorientation and linked-chain planning."""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from ..contracts import ADDON_VERSION, QUICK_REORIENT_ALGORITHM_VERSION, QUICK_REORIENT_SCHEMA_VERSION
from .armature_reader import resolve_active_armature
from .canonical import sha256
from .linked_components import component_lookup, decompose_linear_components
from .mesh_resolver import find_associated_meshes
from .models import ValidationIssue
from .quick_reorient_models import QuickBoneProposal, QuickReorientPlan
from .quick_source_adapter import (
    capture_quick_source,
    detect_source,
    is_external_control,
    is_socket_bone,
    read_allowed_child_map,
)


_EPSILON = 1.0e-7
_MIN_UEFORMAT_LENGTH = 0.01
_VERSION_PROP = "boneweaver_quick_reorient_version"
_FINGERPRINT_PROP = "boneweaver_quick_reorient_source_fingerprint"


def dominant_axis(vector) -> tuple[float, float, float]:
    """Match UEFormat's strict-comparison dominant-axis tie behavior."""
    x, y, z = (float(value) for value in vector)
    result = [0.0, 0.0, 0.0]
    if abs(x) > abs(y):
        index, value = (0, x) if abs(x) > abs(z) else (2, z)
    elif abs(y) > abs(z):
        index, value = 1, y
    else:
        index, value = 2, z
    result[index] = 1.0 if value >= 0.0 else -1.0
    return tuple(result)


def average_offsets(offsets) -> tuple[tuple[float, float, float], float]:
    values = tuple(Vector(offset) for offset in offsets)
    if not values:
        raise ValueError("at least one child offset is required")
    average = sum(values, Vector()) / len(values)
    average_length = sum(value.length for value in values) / len(values)
    return tuple(float(value) for value in average), float(average_length)


def _matrix3(state):
    return Matrix(
        tuple(
            tuple(state.matrix[row * 4 + column] for column in range(3))
            for row in range(3)
        )
    )


def _depth(name, by_name):
    depth = 0
    seen = set()
    parent = by_name[name].parent_name
    while parent in by_name and parent not in seen:
        seen.add(parent)
        depth += 1
        parent = by_name[parent].parent_name
    return depth


def quick_source_fingerprint(armature, states, metadata) -> str:
    world = tuple(
        float(armature.matrix_world[row][column])
        for row in range(4)
        for column in range(4)
    )
    metadata_payload = tuple((name, metadata[name]) for name in sorted(metadata))
    return sha256(
        (
            QUICK_REORIENT_ALGORITHM_VERSION,
            armature.name,
            armature.data.name,
            world,
            states,
            metadata_payload,
        )
    )


def current_quick_source_fingerprint(context, armature) -> str:
    states, metadata = capture_quick_source(context, armature)
    return quick_source_fingerprint(armature, states, metadata)


def _issue(severity, code, message, *, bones=(), objects=()):
    return ValidationIssue(
        severity, code, code.casefold(), message, tuple(bones), tuple(objects)
    )


def _build_proposals(states, metadata, *, source_adapter, already_reoriented,
                     already_normalized, allowed_child_map, connect_linear_chains):
    by_name = {state.bone_name: state for state in states}
    processed = frozenset(
        state.bone_name
        for state in states
        if not is_socket_bone(state.bone_name, metadata[state.bone_name])
    )
    structural = frozenset(
        name for name in processed if not is_external_control(name)
    )
    structural_edges = frozenset(
        (parent.bone_name, child_name)
        for parent in states
        if parent.bone_name in structural
        for child_name in parent.child_names
        if child_name in structural
        and (Vector(by_name[child_name].head) - Vector(parent.head)).length > _EPSILON
    )
    components = decompose_linear_components(states, structural, structural_edges)
    component_ids = component_lookup(components)
    structural_children = {
        name: tuple(
            child
            for child in by_name[name].child_names
            if (name, child) in structural_edges
        )
        for name in structural
    }
    skip_stage_a = already_normalized or already_reoriented
    solved_local: dict[str, tuple[float, float, float]] = {}
    solved_armature: dict[str, Vector] = {}
    stage_a_tails: dict[str, Vector] = {}
    target_local: dict[str, tuple[float, float, float] | None] = {}

    ordered = sorted(by_name, key=lambda name: (_depth(name, by_name), name))
    for name in ordered:
        state = by_name[name]
        head = Vector(state.head)
        old_tail = Vector(state.tail)
        old_rotation = _matrix3(state)
        if name not in processed or skip_stage_a:
            stage_a_tails[name] = old_tail
            target_local[name] = None
            direction = old_tail - head
            if direction.length > _EPSILON:
                solved_armature[name] = direction.normalized()
            continue

        children = tuple(child for child in state.child_names if child in processed)
        allowed = allowed_child_map.get(name)
        if allowed:
            children = tuple(child for child in children if child in allowed)

        local_direction = None
        target_length = state.length
        if children:
            offsets = []
            for child_name in children:
                child_metadata = metadata[child_name]
                if child_metadata.orig_loc is not None:
                    offsets.append(child_metadata.orig_loc)
                else:
                    armature_offset = Vector(by_name[child_name].head) - head
                    offsets.append(tuple(old_rotation.inverted_safe() @ armature_offset))
            average, target_length = average_offsets(offsets)
            local_direction = dominant_axis(average)
        elif state.parent_name in by_name:
            parent_name = state.parent_name
            if metadata[name].orig_quat is not None and parent_name in solved_local:
                inherited = Vector(solved_local[parent_name])
                inherited.rotate(Quaternion(metadata[name].orig_quat).conjugated())
                local_direction = dominant_axis(inherited)
            elif parent_name in solved_armature:
                inherited = old_rotation.inverted_safe() @ solved_armature[parent_name]
                local_direction = dominant_axis(inherited)

        if local_direction is None:
            stage_a_tails[name] = old_tail
            target_local[name] = None
            direction = old_tail - head
            if direction.length > _EPSILON:
                solved_armature[name] = direction.normalized()
            continue
        armature_direction = old_rotation @ Vector(local_direction)
        if armature_direction.length <= _EPSILON:
            stage_a_tails[name] = old_tail
            target_local[name] = None
            continue
        armature_direction.normalize()
        length = max(_MIN_UEFORMAT_LENGTH, float(target_length))
        stage_a_tails[name] = head + armature_direction * length
        target_local[name] = tuple(local_direction)
        solved_local[name] = tuple(local_direction)
        solved_armature[name] = armature_direction

    final_tails = dict(stage_a_tails)
    final_connect = {state.bone_name: state.use_connect for state in states}
    if connect_linear_chains:
        for name in structural:
            children = structural_children[name]
            if len(children) == 1:
                final_tails[name] = Vector(by_name[children[0]].head)
        for name in structural:
            parent = by_name[name].parent_name
            final_connect[name] = bool(
                parent in structural
                and (parent, name) in structural_edges
                and len(structural_children[parent]) == 1
            )

    proposals = []
    for name in sorted(by_name):
        state = by_name[name]
        skipped = name not in processed
        skip_reason = None
        if skipped:
            skip_reason = (
                "SOCKET" if is_socket_bone(name, metadata[name]) else "OUT_OF_SCOPE"
            )
        tail = final_tails.get(name, Vector(state.tail))
        old_rotation = _matrix3(state)
        proposals.append(
            QuickBoneProposal(
                bone_name=name,
                source=source_adapter,
                target_direction_local=target_local.get(name),
                target_tail=tuple(float(value) for value in tail),
                target_roll_reference=tuple(float(value) for value in old_rotation.col[2]),
                target_length=float((tail - Vector(state.head)).length),
                target_use_connect=bool(final_connect[name]),
                component_id=component_ids.get(name),
                branch_boundary=name in structural and len(structural_children[name]) > 1,
                skipped=skipped,
                skip_reason=skip_reason,
            )
        )
    return tuple(proposals), components, structural_edges


def _quick_preflight(context, armature, states, metadata, proposals, structural_edges):
    issues = []
    by_name = {state.bone_name: state for state in states}
    proposal_by_name = {proposal.bone_name: proposal for proposal in proposals}
    targets = {proposal.bone_name for proposal in proposals if not proposal.skipped}
    if armature.library or armature.data.library:
        issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_LINKED_ARMATURE", "Armature is linked and not editable", objects=(armature.name,)))
    if armature.data.users > 1:
        issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_SHARED_ARMATURE_DATA", "Armature data has multiple object users", objects=(armature.name,)))
    determinant = armature.matrix_world.to_3x3().determinant()
    if not math.isfinite(determinant) or abs(determinant) <= 1.0e-12 or determinant < 0.0:
        issues.append(_issue("BLOCKER", "BONEWEAVER_NON_INVERTIBLE_TRANSFORM", "Armature transform is unsafe", objects=(armature.name,)))
    scales = tuple(abs(float(value)) for value in armature.scale)
    if max(scales) - min(scales) > _EPSILON:
        issues.append(_issue("WARNING", "BONEWEAVER_NON_UNIFORM_OBJECT_SCALE", "Armature has non-uniform scale", objects=(armature.name,)))
    for name in sorted(targets):
        bone = armature.data.bones[name]
        if bone.bbone_segments > 1:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_BBONE_UNSUPPORTED", "B-Bone segments are unsupported", bones=(name,)))
        pose_bone = armature.pose.bones.get(name)
        if pose_bone and pose_bone.constraints:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_RELATED_CONSTRAINT", "Target bone has constraints", bones=(name,)))
        if pose_bone:
            identity = Matrix.Identity(4)
            if any(
                abs(pose_bone.matrix_basis[row][column] - identity[row][column]) > _EPSILON
                for row in range(4)
                for column in range(4)
            ):
                issues.append(_issue("BLOCKER", "BONEWEAVER_NON_IDENTITY_POSE", "Armature pose is not identity", bones=(name,)))
        proposal = proposal_by_name[name]
        if (Vector(proposal.target_tail) - Vector(by_name[name].tail)).length > _EPSILON:
            for child_name in by_name[name].child_names:
                if (name, child_name) not in structural_edges and by_name[child_name].use_connect:
                    issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_EXTERNAL_CONNECTED_CHILD", "A non-structural connected child would move", bones=(name, child_name)))
    for child in states:
        parent_name = child.parent_name
        if (
            parent_name in by_name
            and child.bone_name in targets
            and parent_name in targets
            and (parent_name, child.bone_name) not in structural_edges
            and (Vector(by_name[parent_name].head) - Vector(child.head)).length <= _EPSILON
        ):
            issues.append(_issue("WARNING", "BONEWEAVER_QUICK_ZERO_LENGTH", "Coincident joint edge was excluded", bones=(parent_name, child.bone_name)))
    animation = armature.animation_data
    if animation:
        if animation.action:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_RELATED_ACTION", "Armature has an active Action", objects=(armature.name,)))
        if animation.nla_tracks:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_RELATED_NLA", "Armature has NLA tracks", objects=(armature.name,)))
        if animation.drivers:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_RELATED_DRIVER", "Armature has drivers", objects=(armature.name,)))
    for obj in bpy.data.objects:
        if obj.parent == armature and obj.parent_type == "BONE" and obj.parent_bone in targets:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_BONE_PARENTED_OBJECT", "Object is parented to a target bone", bones=(obj.parent_bone,), objects=(obj.name,)))
        for constraint in obj.constraints:
            if getattr(constraint, "target", None) == armature and getattr(constraint, "subtarget", "") in targets:
                issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_RELATED_CONSTRAINT", "Object constraint targets a processed bone", objects=(obj.name,)))
    bindings, mesh_issues = find_associated_meshes(armature)
    issues.extend(mesh_issues)
    for binding in bindings:
        modifier = bpy.data.objects[binding.object_name].modifiers[binding.modifier_name]
        if modifier.use_bone_envelopes:
            issues.append(_issue("BLOCKER", "BONEWEAVER_QUICK_ENVELOPE_DEFORMATION", "Armature modifier uses bone envelopes", objects=(binding.object_name,)))
    rank = {"BLOCKER": 0, "WARNING": 1, "INFO": 2}
    return tuple(sorted(issues, key=lambda item: (rank.get(item.severity, 3), item.code, item.bone_names, item.object_names)))


def build_quick_reorient_plan(
    context, *, connect_linear_chains: bool = True
) -> QuickReorientPlan | None:
    armature = resolve_active_armature(context)
    if armature is None:
        return None
    states, metadata = capture_quick_source(context, armature)
    source_adapter, already_reoriented = detect_source(metadata)
    source_fingerprint = quick_source_fingerprint(armature, states, metadata)
    already_normalized = bool(
        armature.data.get(_VERSION_PROP) == QUICK_REORIENT_ALGORITHM_VERSION
        and armature.data.get(_FINGERPRINT_PROP) == source_fingerprint
    )
    proposals, components, structural_edges = _build_proposals(
        states,
        metadata,
        source_adapter=source_adapter,
        already_reoriented=already_reoriented,
        already_normalized=already_normalized,
        allowed_child_map=read_allowed_child_map(armature),
        connect_linear_chains=connect_linear_chains,
    )
    issues = _quick_preflight(
        context, armature, states, metadata, proposals, structural_edges
    )
    plan_id = sha256(
        (
            "boneweaver.quick_reorient_plan",
            QUICK_REORIENT_SCHEMA_VERSION,
            QUICK_REORIENT_ALGORITHM_VERSION,
            ADDON_VERSION,
            connect_linear_chains,
            source_fingerprint,
            source_adapter,
            states,
            proposals,
            components,
            issues,
        )
    )
    return QuickReorientPlan(
        kind="boneweaver.quick_reorient_plan",
        schema_version=QUICK_REORIENT_SCHEMA_VERSION,
        algorithm_version=QUICK_REORIENT_ALGORITHM_VERSION,
        addon_version=ADDON_VERSION,
        plan_id=plan_id,
        source_fingerprint=source_fingerprint,
        source_adapter=source_adapter,
        armature_object_name=armature.name,
        armature_data_name=armature.data.name,
        already_reoriented=already_reoriented,
        already_normalized=already_normalized,
        connect_linear_chains=connect_linear_chains,
        bone_states=states,
        proposals=proposals,
        linked_components=components,
        issues=issues,
    )
