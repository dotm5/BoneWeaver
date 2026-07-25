"""Atomic Quick Reorient apply, post-validation, rollback, and restore."""

from __future__ import annotations

import datetime as dt
import json
import math

import bpy
from mathutils import Vector

from ..contracts import QUICK_REORIENT_ALGORITHM_VERSION
from .canonical import sha256
from .context_guard import ContextStateGuard
from .fingerprint import base_mesh_digest, modifier_digest, weight_digest
from .mesh_resolver import find_associated_meshes
from .quick_reorient import current_quick_source_fingerprint
from .quick_reorient_models import QuickTransactionResult
from .validation_tolerance import MeshCoordinateCapture, evaluate_mesh_tolerance


_HEAD_EPSILON = 1.0e-7
_TAIL_EPSILON = 1.0e-6
_ROLL_EPSILON = 1.0e-5
_VERSION_PROP = "boneweaver_quick_reorient_version"
_FINGERPRINT_PROP = "boneweaver_quick_reorient_source_fingerprint"
_MODE_PROP = "boneweaver_quick_reorient_mode"


def discover_latest_quick_snapshot() -> str:
    candidates = []
    for text in getattr(bpy.data, "texts", ()):
        if not text.name.startswith("BONEWEAVER_QUICK_SNAPSHOT::"):
            continue
        try:
            payload = json.loads(text.as_string())
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            payload.get("kind") == "boneweaver.quick_reorient_snapshot"
            and payload.get("status") == "APPLIED"
        ):
            candidates.append((str(payload.get("created_at", "")), text.name))
    return max(candidates)[1] if candidates else ""


def _roll_distance(first, second):
    return abs((float(first) - float(second) + math.pi) % (2.0 * math.pi) - math.pi)


def _activate(context, armature):
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    context.view_layer.objects.active = armature
    armature.data.use_mirror_x = False


def _capture_edit_state(armature):
    return {
        bone.name: {
            "parent_name": bone.parent.name if bone.parent else None,
            "head": tuple(float(value) for value in bone.head),
            "tail": tuple(float(value) for value in bone.tail),
            "roll": float(bone.roll),
            "use_connect": bool(bone.use_connect),
            "use_deform": bool(bone.use_deform),
        }
        for bone in armature.data.edit_bones
    }


def _write_edit_state(armature, states):
    for bone in armature.data.edit_bones:
        bone.use_connect = False
    for name, state in states.items():
        bone = armature.data.edit_bones[name]
        bone.tail = state["tail"]
        bone.roll = state["roll"]
    for name, state in states.items():
        armature.data.edit_bones[name].use_connect = state["use_connect"]


def _mesh_digests(armature):
    bindings, issues = find_associated_meshes(armature)
    if issues:
        raise RuntimeError(", ".join(issue.code for issue in issues))
    return {
        binding.object_name: {
            "weight": weight_digest(bpy.data.objects[binding.object_name]),
            "base": base_mesh_digest(bpy.data.objects[binding.object_name]),
            "modifier": modifier_digest(bpy.data.objects[binding.object_name]),
        }
        for binding in bindings
    }


def _capture_neutral(armature):
    bindings, _issues = find_associated_meshes(armature)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    captures = {}
    for binding in bindings:
        obj = bpy.data.objects[binding.object_name]
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            local = tuple(tuple(float(value) for value in vertex.co) for vertex in mesh.vertices)
            world = tuple(
                tuple(float(value) for value in evaluated.matrix_world @ vertex.co)
                for vertex in mesh.vertices
            )
            captures[obj.name] = MeshCoordinateCapture(obj.name, local, world)
        finally:
            evaluated.to_mesh_clear()
    return captures


def _capture_delta(first, second):
    if len(first.local_coordinates) != len(second.local_coordinates):
        return float("inf"), float("inf")
    deltas = tuple(
        (Vector(before) - Vector(after)).length
        for before, after in zip(first.local_coordinates, second.local_coordinates)
    )
    if not deltas:
        return 0.0, 0.0
    return max(deltas), (sum(delta * delta for delta in deltas) / len(deltas)) ** 0.5


def _neutral_baseline(armature):
    first = _capture_neutral(armature)
    bpy.context.evaluated_depsgraph_get().update()
    second = _capture_neutral(armature)
    return {
        name: (capture, *_capture_delta(first[name], capture))
        for name, capture in second.items()
    }


def _metadata_state(armature):
    return {
        _VERSION_PROP: armature.data.get(_VERSION_PROP),
        _FINGERPRINT_PROP: armature.data.get(_FINGERPRINT_PROP),
        _MODE_PROP: armature.data.get(_MODE_PROP),
    }


def _write_metadata_state(armature, state):
    for key, value in state.items():
        if value is None:
            if key in armature.data:
                del armature.data[key]
        else:
            armature.data[key] = value


def _validate(
    context,
    plan,
    armature,
    before,
    after,
    mesh_before,
    neutral_before,
    *,
    mesh_validation_enabled=True,
    neutral_validation_enabled=True,
):
    issues = []
    proposals = {proposal.bone_name: proposal for proposal in plan.proposals}
    if set(after) != set(before):
        issues.append("BONEWEAVER_QUICK_BONE_SET_CHANGED")
    for name, old in before.items():
        current = after.get(name)
        if current is None:
            continue
        if (
            current["parent_name"] != old["parent_name"]
            or current["use_deform"] != old["use_deform"]
            or (Vector(current["head"]) - Vector(old["head"])).length > _HEAD_EPSILON
        ):
            issues.append("BONEWEAVER_QUICK_INVARIANT_CHANGED")
        proposal = proposals[name]
        if proposal.skipped:
            if (
                (Vector(current["tail"]) - Vector(old["tail"])).length > _TAIL_EPSILON
                or _roll_distance(current["roll"], old["roll"]) > _ROLL_EPSILON
                or current["use_connect"] != old["use_connect"]
            ):
                issues.append("BONEWEAVER_QUICK_NON_TARGET_CHANGED")
        else:
            if (Vector(current["tail"]) - Vector(proposal.target_tail)).length > _TAIL_EPSILON:
                issues.append("BONEWEAVER_QUICK_TARGET_TAIL_MISMATCH")
            if current["use_connect"] != proposal.target_use_connect:
                issues.append("BONEWEAVER_QUICK_CONNECT_MISMATCH")

    if plan.connect_linear_chains:
        for component in plan.linked_components:
            for parent_name, child_name in zip(component.bone_names, component.bone_names[1:]):
                parent = after[parent_name]
                child = after[child_name]
                if child["parent_name"] != parent_name:
                    issues.append("BONEWEAVER_QUICK_COMPONENT_PARENT_MISMATCH")
                if (Vector(parent["tail"]) - Vector(child["head"])).length > _TAIL_EPSILON:
                    issues.append("BONEWEAVER_QUICK_COMPONENT_GEOMETRY_MISMATCH")
                if not child["use_connect"]:
                    issues.append("BONEWEAVER_QUICK_COMPONENT_CONNECT_MISMATCH")
            if after[component.root_bone_name]["use_connect"]:
                issues.append("BONEWEAVER_QUICK_COMPONENT_ROOT_CONNECTED")
        state_by_name = {state.bone_name: state for state in plan.bone_states}
        for proposal in plan.proposals:
            if not proposal.branch_boundary:
                continue
            for child_name in state_by_name[proposal.bone_name].child_names:
                child_proposal = proposals[child_name]
                if child_proposal.component_id and after[child_name]["use_connect"]:
                    issues.append("BONEWEAVER_QUICK_BRANCH_CHILD_CONNECTED")

    if mesh_validation_enabled:
        mesh_after = _mesh_digests(armature)
        for name, digests in mesh_before.items():
            if mesh_after.get(name) != digests:
                issues.append("BONEWEAVER_QUICK_MESH_DIGEST_CHANGED")
    if neutral_validation_enabled:
        current_neutral = _capture_neutral(armature)
        settings = context.scene.boneweaver_settings
        for name, (capture, baseline_max, baseline_rms) in neutral_before.items():
            if name not in current_neutral:
                issues.append("BONEWEAVER_QUICK_NEUTRAL_MESH_CHANGED")
                continue
            result = evaluate_mesh_tolerance(
                capture,
                current_neutral[name],
                mode=settings.validation_tolerance_mode,
                custom_relative_factor=settings.position_epsilon_factor,
                baseline_max_delta=baseline_max,
                baseline_rms_delta=baseline_rms,
            )
            if result.result == "FAIL_AND_ROLLBACK":
                issues.append("BONEWEAVER_QUICK_NEUTRAL_MESH_CHANGED")
    return tuple(sorted(set(issues)))


def _mutation_count(before, after, proposals):
    count = 0
    for proposal in proposals:
        old = before[proposal.bone_name]
        new = after[proposal.bone_name]
        if (
            (Vector(old["tail"]) - Vector(new["tail"])).length > _TAIL_EPSILON
            or _roll_distance(old["roll"], new["roll"]) > _ROLL_EPSILON
            or old["use_connect"] != new["use_connect"]
        ):
            count += 1
    return count


def apply_quick_plan(context, plan, *, validator=None, strict_validation=True):
    armature = bpy.data.objects[plan.armature_object_name]
    diagnostic_issues = []
    mesh_validation_enabled = True
    neutral_validation_enabled = True
    try:
        mesh_before = _mesh_digests(armature)
    except Exception:
        if strict_validation:
            raise
        mesh_before = {}
        mesh_validation_enabled = False
        diagnostic_issues.append("BONEWEAVER_QUICK_MESH_DIAGNOSTIC_SKIPPED")
    try:
        neutral_before = _neutral_baseline(armature)
    except Exception:
        if strict_validation:
            raise
        neutral_before = {}
        neutral_validation_enabled = False
        diagnostic_issues.append("BONEWEAVER_QUICK_NEUTRAL_DIAGNOSTIC_SKIPPED")
    metadata_before = _metadata_state(armature)
    snapshot_id = ""
    text_name = ""
    payload = {}
    before = {}
    validation_issues = ()
    with ContextStateGuard(context):
        try:
            _activate(context, armature)
            bpy.ops.object.mode_set(mode="EDIT")
            before = _capture_edit_state(armature)
            bpy.ops.object.mode_set(mode="OBJECT")
            created_at = dt.datetime.now(dt.timezone.utc).isoformat()
            snapshot_id = sha256((plan.plan_id, before, mesh_before, created_at))
            text_name = f"BONEWEAVER_QUICK_SNAPSHOT::{snapshot_id}"
            payload = {
                "kind": "boneweaver.quick_reorient_snapshot",
                "schema_version": plan.schema_version,
                "algorithm_version": plan.algorithm_version,
                "snapshot_id": snapshot_id,
                "plan_id": plan.plan_id,
                "created_at": created_at,
                "armature": {"object_name": armature.name, "data_name": armature.data.name},
                "pre_bones": before,
                "expected_post_bones": {},
                "mesh_digests": mesh_before,
                "mesh_validation_enabled": mesh_validation_enabled,
                "neutral_validation_enabled": neutral_validation_enabled,
                "pre_metadata": metadata_before,
                "expected_post_metadata": {},
                "status": "CREATED",
            }
            text = bpy.data.texts.new(text_name)
            text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))

            bpy.ops.object.mode_set(mode="EDIT")
            for bone in armature.data.edit_bones:
                bone.use_connect = False
            for proposal in plan.proposals:
                if proposal.skipped:
                    continue
                bone = armature.data.edit_bones[proposal.bone_name]
                target_tail = Vector(proposal.target_tail)
                if (bone.tail - target_tail).length > _HEAD_EPSILON:
                    bone.tail = target_tail
                    reference = Vector(proposal.target_roll_reference)
                    if reference.length > _HEAD_EPSILON:
                        bone.align_roll(reference)
            for proposal in plan.proposals:
                armature.data.edit_bones[proposal.bone_name].use_connect = proposal.target_use_connect
            after = _capture_edit_state(armature)
            bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.update()
            try:
                validation_issues = _validate(
                    context,
                    plan,
                    armature,
                    before,
                    after,
                    mesh_before,
                    neutral_before,
                    mesh_validation_enabled=mesh_validation_enabled,
                    neutral_validation_enabled=neutral_validation_enabled,
                )
            except Exception:
                validation_issues = (
                    "BONEWEAVER_QUICK_POST_DIAGNOSTIC_SKIPPED",
                )
            validation_issues = tuple(
                sorted(set(validation_issues + tuple(diagnostic_issues)))
            )
            if validator is not None and not validator(context, plan):
                validation_issues = tuple(
                    sorted(set(validation_issues + ("BONEWEAVER_QUICK_CUSTOM_VALIDATION_FAILED",)))
                )
            if validation_issues and strict_validation:
                raise RuntimeError("post validation failed: " + ", ".join(validation_issues))

            armature.data[_VERSION_PROP] = QUICK_REORIENT_ALGORITHM_VERSION
            armature.data[_MODE_PROP] = plan.mode
            armature.data[_FINGERPRINT_PROP] = current_quick_source_fingerprint(context, armature)
            metadata_after = _metadata_state(armature)
            mutation_count = _mutation_count(before, after, plan.proposals)
            payload["expected_post_bones"] = after
            payload["expected_post_metadata"] = metadata_after
            payload["mutation_count"] = mutation_count
            payload["connected_edge_count"] = sum(
                1 for proposal in plan.proposals if proposal.target_use_connect
            )
            payload["validation_issues"] = validation_issues
            payload["status"] = "APPLIED"
            text.clear()
            text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
            return QuickTransactionResult(
                True, False, snapshot_id, text_name, mutation_count,
                payload["connected_edge_count"], validation_issues, None,
            )
        except Exception as error:
            try:
                _activate(context, armature)
                bpy.ops.object.mode_set(mode="EDIT")
                if before:
                    _write_edit_state(armature, before)
                bpy.ops.object.mode_set(mode="OBJECT")
                _write_metadata_state(armature, metadata_before)
                context.view_layer.update()
                if text_name and text_name in bpy.data.texts:
                    payload["status"] = "ROLLED_BACK"
                    payload["validation_issues"] = validation_issues
                    text = bpy.data.texts[text_name]
                    text.clear()
                    text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
                return QuickTransactionResult(
                    False, True, snapshot_id, text_name, 0, 0,
                    validation_issues, str(error),
                )
            except Exception as rollback_error:
                return QuickTransactionResult(
                    False, False, snapshot_id, text_name, 0, 0,
                    validation_issues, f"{error}; rollback failed: {rollback_error}",
                )


def restore_quick_snapshot(context, text_name):
    text = bpy.data.texts.get(text_name)
    if text is None:
        return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
    payload = json.loads(text.as_string())
    if payload.get("kind") != "boneweaver.quick_reorient_snapshot" or payload.get("status") != "APPLIED":
        return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
    info = payload["armature"]
    armature = bpy.data.objects.get(info["object_name"])
    if armature is None or armature.data.name != info["data_name"]:
        return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
    if payload.get("mesh_validation_enabled", True):
        try:
            if _mesh_digests(armature) != payload.get("mesh_digests", {}):
                return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
        except RuntimeError:
            return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
    current_metadata = _metadata_state(armature)
    expected_metadata = payload.get("expected_post_metadata", {})
    if _MODE_PROP not in expected_metadata:
        current_metadata.pop(_MODE_PROP, None)
    if current_metadata != expected_metadata:
        return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
    with ContextStateGuard(context):
        _activate(context, armature)
        bpy.ops.object.mode_set(mode="EDIT")
        current = _capture_edit_state(armature)
        expected = payload["expected_post_bones"]
        conflict = set(current) != set(expected)
        if not conflict:
            for name, state in expected.items():
                bone = current[name]
                if (
                    bone["parent_name"] != state["parent_name"]
                    or (Vector(bone["head"]) - Vector(state["head"])).length > _HEAD_EPSILON
                    or (Vector(bone["tail"]) - Vector(state["tail"])).length > _TAIL_EPSILON
                    or _roll_distance(bone["roll"], state["roll"]) > _ROLL_EPSILON
                    or bone["use_connect"] != state["use_connect"]
                    or bone["use_deform"] != state["use_deform"]
                ):
                    conflict = True
                    break
        if conflict:
            bpy.ops.object.mode_set(mode="OBJECT")
            return False, "BONEWEAVER_QUICK_RESTORE_CONFLICT"
        _write_edit_state(armature, payload["pre_bones"])
        bpy.ops.object.mode_set(mode="OBJECT")
        _write_metadata_state(armature, payload.get("pre_metadata", {}))
        context.view_layer.update()
    payload["status"] = "RESTORED"
    text.clear()
    text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return True, None
