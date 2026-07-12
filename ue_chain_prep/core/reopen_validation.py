"""Independent-process validation for a saved conversion copy."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import bpy

from .fingerprint import modifier_digest
from .mesh_scan_cache import mesh_digest_pair
from .validation import armature_state_matches


@dataclass(frozen=True, slots=True)
class ReopenValidationReport:
    success: bool
    issues: tuple[str, ...]
    mutation_record_count: int
    manifest_mutation_record_count: int
    checked_bone_count: int
    checked_linear_edge_count: int
    checked_branch_count: int
    weight_digest_changes: int
    base_mesh_digest_changes: int
    modifier_digest_changes: int
    packed_image_count: int
    expected_packed_image_count: int
    checked_tip_helper_count: int
    mutation_target_count: int
    reference_only_tip_helper_count: int
    topology_ledger_conserved: bool
    snapshot_conflict_check_ran: bool


def _empty_report(*issues):
    return ReopenValidationReport(
        success=False,
        issues=tuple(sorted(set(issues))),
        mutation_record_count=0,
        manifest_mutation_record_count=0,
        checked_bone_count=0,
        checked_linear_edge_count=0,
        checked_branch_count=0,
        weight_digest_changes=0,
        base_mesh_digest_changes=0,
        modifier_digest_changes=0,
        packed_image_count=0,
        expected_packed_image_count=0,
        checked_tip_helper_count=0,
        mutation_target_count=0,
        reference_only_tip_helper_count=0,
        topology_ledger_conserved=False,
        snapshot_conflict_check_ran=False,
    )


def _json_text(name):
    text = bpy.data.texts.get(name)
    if text is None:
        return None
    try:
        return json.loads(text.as_string())
    except (TypeError, ValueError):
        return None


def _vector_close(first, second, epsilon=1.0e-6):
    return len(first) == len(second) and all(
        abs(float(a) - float(b)) <= epsilon for a, b in zip(first, second)
    )


def _capture_edit_states(armature, names):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        return {
            name: {
                "head": tuple(float(value) for value in armature.data.edit_bones[name].head),
                "tail": tuple(float(value) for value in armature.data.edit_bones[name].tail),
                "roll": float(armature.data.edit_bones[name].roll),
                "use_connect": bool(armature.data.edit_bones[name].use_connect),
                "parent_name": armature.data.edit_bones[name].parent.name if armature.data.edit_bones[name].parent else None,
            }
            for name in names
            if name in armature.data.edit_bones
        }
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def _topology_ledger_is_conserved(ledger, mutation_targets, reference_only_helpers):
    if not isinstance(ledger, dict):
        return False
    selected_count = int(ledger.get("selected_bone_count", -1))
    mutation_target_count = int(ledger.get("mutation_target_count", -1))
    reference_only_count = int(ledger.get("reference_only_tip_helper_count", -1))
    skipped_count = int(ledger.get("skipped_by_design_count", -1))
    return (
        selected_count == mutation_target_count + reference_only_count + skipped_count
        and mutation_target_count == len(mutation_targets)
        and reference_only_count == len(reference_only_helpers)
        and int(ledger.get("proposal_count", -1)) == mutation_target_count
    )


def validate_reopened_file():
    manifest = _json_text("UECP_EXPORT_MANIFEST")
    if manifest is None:
        return _empty_report("UECP_REOPEN_MANIFEST_MISSING")
    snapshot_id = manifest.get("snapshot_id")
    snapshot = _json_text(f"UECP_SNAPSHOT::{snapshot_id}") if snapshot_id else None
    if snapshot is None:
        return _empty_report("UECP_REOPEN_SNAPSHOT_MISSING")
    issues = set()
    if snapshot.get("status") != "APPLIED":
        issues.add("UECP_REOPEN_SNAPSHOT_NOT_APPLIED")
    profile = manifest.get("profile")
    tip_helper_usage = manifest.get("tip_helper_usage")
    if (
        profile != snapshot.get("profile")
        or tip_helper_usage != snapshot.get("tip_helper_usage")
        or tip_helper_usage not in {
            "REFERENCE_ONLY", "INCLUDE_AS_PHYSICS_TERMINAL",
        }
        or (
            tip_helper_usage == "INCLUDE_AS_PHYSICS_TERMINAL"
            and profile != "VISUAL_CHAIN_CLEANUP"
        )
    ):
        issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    manifest_records = tuple(manifest.get("mutation_records", ()))
    snapshot_records = tuple(snapshot.get("mutation_records", ()))
    if manifest_records != snapshot_records:
        issues.add("UECP_REOPEN_MUTATION_LEDGER_MISMATCH")
    manifest_helpers = tuple(manifest.get("tip_helpers", ()))
    snapshot_helpers = tuple(snapshot.get("tip_helpers", ()))
    if manifest_helpers != snapshot_helpers:
        issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    mutation_targets = tuple(manifest.get("mutation_targets", ()))
    reference_only_helpers = tuple(manifest.get("reference_only_tip_helpers", ()))
    if mutation_targets != tuple(snapshot.get("mutation_targets", ())):
        issues.add("UECP_REOPEN_TOPOLOGY_LEDGER_MISMATCH")
    if reference_only_helpers != tuple(snapshot.get("reference_only_tip_helpers", ())):
        issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    helper_names = tuple(item.get("bone_name") for item in manifest_helpers)
    expected_reference_helpers = tuple(
        item.get("bone_name")
        for item in manifest_helpers
        if item.get("reference_only") is True
    )
    included_helper_names = tuple(
        item.get("bone_name")
        for item in manifest_helpers
        if item.get("mutation_target") is True
    )
    if (
        expected_reference_helpers != reference_only_helpers
        or len(set(helper_names)) != len(helper_names)
        or not set(included_helper_names).issubset(mutation_targets)
    ):
        issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    helper_name_set = set(helper_names)
    reference_only_helper_set = set(reference_only_helpers)
    manual_tip_edges = {
        (helper.get("parent_bone_name"), helper.get("bone_name"))
        for helper in manifest_helpers
        if helper.get("parent_terminal_source") == "MANUAL_OVERRIDE"
    }
    if reference_only_helper_set.intersection(mutation_targets) or any(
        record.get("bone_name") in reference_only_helper_set for record in manifest_records
    ):
        issues.add("UECP_REOPEN_TIP_HELPER_MUTATION_DETECTED")
    for helper in manifest_helpers:
        reference_only = helper.get("reference_only") is True
        included = (
            helper.get("mutation_target") is True
            and helper.get("requires_own_tail") is True
            and not reference_only
        )
        if helper.get("role") != "EXISTING_TIP_HELPER" or not (
            (reference_only and helper.get("mutation_target") is False
             and helper.get("requires_own_tail") is False)
            or (included and tip_helper_usage == "INCLUDE_AS_PHYSICS_TERMINAL")
        ):
            issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    manifest_nodes = tuple(manifest.get("physics_nodes", ()))
    manifest_nodes_by_id = {
        node.get("node_id"): node for node in manifest_nodes if node.get("node_id")
    }
    if manifest_nodes != tuple(snapshot.get("physics_nodes", ())):
        issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    helper_nodes = {
        node.get("bone_name"): node
        for node in manifest_nodes
        if node.get("bone_name") in helper_name_set
    }
    for name in helper_names:
        node = helper_nodes.get(name)
        helper = next(item for item in manifest_helpers if item.get("bone_name") == name)
        if not node or (
            node.get("semantic_role") != "EXISTING_TIP_HELPER"
            or node.get("reference_only") is not helper.get("reference_only")
            or node.get("mutation_target") is not helper.get("mutation_target")
            or node.get("requires_own_tail") is not helper.get("requires_own_tail")
        ):
            issues.add("UECP_REOPEN_TIP_HELPER_CLASSIFICATION_MISMATCH")
    manifest_ledger = manifest.get("topology_ledger") or {}
    snapshot_ledger = snapshot.get("topology_ledger") or {}
    topology_conserved = (
        manifest_ledger == snapshot_ledger
        and _topology_ledger_is_conserved(
            manifest_ledger, mutation_targets, reference_only_helpers
        )
    )
    if not topology_conserved:
        issues.add("UECP_REOPEN_TOPOLOGY_LEDGER_MISMATCH")
    armature_info = manifest.get("armature") or {}
    armature = bpy.data.objects.get(armature_info.get("object_name", ""))
    if armature is None or armature.type != "ARMATURE" or armature.data.name != armature_info.get("data_name"):
        return _empty_report("UECP_REOPEN_ARMATURE_MISSING")
    armature_matrix = tuple(
        float(armature.matrix_world[row][column])
        for row in range(4)
        for column in range(4)
    )
    if not _vector_close(armature_matrix, armature_info.get("matrix_world", ())):
        issues.add("UECP_REOPEN_REST_GEOMETRY_MISMATCH")
    if not armature_state_matches(
        armature,
        manifest.get("whole_armature_post_state") or {},
    ):
        issues.add("UECP_REOPEN_REST_GEOMETRY_MISMATCH")
    expected_post = snapshot.get("expected_post_bones") or {}
    current = _capture_edit_states(armature, tuple(expected_post))
    for name, expected in expected_post.items():
        actual = current.get(name)
        if actual is None:
            issues.add("UECP_REOPEN_BONE_MISSING")
            continue
        if not _vector_close(actual["tail"], expected.get("tail", ())):
            issues.add("UECP_REOPEN_REST_GEOMETRY_MISMATCH")
        if abs(actual["roll"] - float(expected.get("roll", actual["roll"]))) > 1.0e-6:
            issues.add("UECP_REOPEN_REST_GEOMETRY_MISMATCH")
        if actual["use_connect"] != bool(expected.get("use_connect")):
            issues.add("UECP_REOPEN_CONNECT_MISMATCH")
    current_helpers = _capture_edit_states(armature, helper_names)
    for helper in manifest_helpers:
        name = helper.get("bone_name")
        actual = current_helpers.get(name)
        if actual is None:
            issues.add("UECP_REOPEN_BONE_MISSING")
            continue
        geometry_mismatch = (
            actual.get("parent_name") != helper.get("parent_name")
            or not _vector_close(actual.get("head", ()), helper.get("head", ()))
        )
        if helper.get("reference_only") is True:
            geometry_mismatch = geometry_mismatch or (
                not _vector_close(actual.get("tail", ()), helper.get("tail", ()))
                or abs(float(actual.get("roll", 0.0)) - float(helper.get("roll", 0.0))) > 1.0e-6
                or bool(actual.get("use_connect")) != bool(helper.get("use_connect"))
            )
        if geometry_mismatch:
            issues.add("UECP_REOPEN_TIP_HELPER_GEOMETRY_MISMATCH")
        if helper.get("parent_terminal_source") == "EXISTING_TIP_HELPER_HEAD":
            parent_name = helper.get("parent_bone_name")
            parent = current.get(parent_name)
            if parent is None:
                parent = _capture_edit_states(armature, (parent_name,)).get(parent_name)
            if parent is None or not _vector_close(parent.get("tail", ()), actual.get("head", ())):
                issues.add("UECP_REOPEN_TIP_HELPER_GEOMETRY_MISMATCH")
    branch_resolutions = tuple(manifest.get("branch_resolutions", ()))
    selected_by_branch = {
        item.get("branch_bone_name"): item.get("selected_child_name")
        for item in branch_resolutions
        if item.get("selected_child_name")
    }
    for branch, selected_child in selected_by_branch.items():
        branch_state = current.get(branch) or _capture_edit_states(armature, (branch, selected_child)).get(branch)
        child_state = current.get(selected_child) or _capture_edit_states(armature, (branch, selected_child)).get(selected_child)
        if not branch_state or not child_state or not _vector_close(branch_state["tail"], child_state["head"]):
            issues.add("UECP_REOPEN_BRANCH_MAIN_PATH_MISMATCH")
        resolution = next(item for item in branch_resolutions if item.get("branch_bone_name") == branch)
        side_states = _capture_edit_states(armature, tuple(resolution.get("side_child_names", ())))
        if any(item["use_connect"] for item in side_states.values()):
            issues.add("UECP_REOPEN_BRANCH_SIDE_CONNECT_MISMATCH")
    checked_linear_edges = 0
    node_to_bone = lambda node_id: node_id.removeprefix("real:")
    for edge in manifest.get("physics_edges", ()):
        if edge.get("kind") != "HIERARCHY_SEGMENT":
            continue
        parent = node_to_bone(edge["parent_node_id"])
        child = node_to_bone(edge["child_node_id"])
        parent_node = manifest_nodes_by_id.get(edge.get("parent_node_id"))
        if parent_node is not None and not parent_node.get("mutation_target", True):
            continue
        if (parent, child) in manual_tip_edges:
            continue
        if parent in selected_by_branch and selected_by_branch[parent] != child:
            continue
        states = _capture_edit_states(armature, (parent, child))
        if parent in states and child in states:
            checked_linear_edges += 1
            if not _vector_close(states[parent]["tail"], states[child]["head"]):
                issues.add("UECP_REOPEN_LINEAR_CONTINUITY_MISMATCH")
    weight_changes = base_changes = modifier_changes = 0
    for name, expected_weight in manifest.get("weight_digests", {}).items():
        mesh = bpy.data.objects.get(name)
        if mesh is None:
            weight_changes += 1
            base_changes += 1
            modifier_changes += 1
            continue
        mesh_matrix = tuple(
            float(mesh.matrix_world[row][column])
            for row in range(4)
            for column in range(4)
        )
        if not _vector_close(
            mesh_matrix,
            manifest.get("mesh_object_matrices", {}).get(name, ()),
        ):
            issues.add("UECP_REOPEN_REST_GEOMETRY_MISMATCH")
        current_weight, current_base = mesh_digest_pair(mesh)
        if current_weight != expected_weight:
            weight_changes += 1
        if current_base != manifest.get("base_mesh_digests", {}).get(name):
            base_changes += 1
        if modifier_digest(mesh) != manifest.get("modifier_digests", {}).get(name):
            modifier_changes += 1
    if weight_changes:
        issues.add("UECP_WEIGHT_DIGEST_CHANGED")
    if base_changes:
        issues.add("UECP_BASE_MESH_CHANGED")
    if modifier_changes:
        issues.add("UECP_MODIFIER_DIGEST_CHANGED")
    packed_count = sum(bool(image.packed_file) for image in bpy.data.images)
    expected_packed = int(manifest.get("packed_image_count", 0))
    if packed_count != expected_packed:
        issues.add("UECP_REOPEN_PACKED_IMAGE_COUNT_MISMATCH")
    return ReopenValidationReport(
        success=not issues,
        issues=tuple(sorted(issues)),
        mutation_record_count=len(snapshot_records),
        manifest_mutation_record_count=len(manifest_records),
        checked_bone_count=len(current),
        checked_linear_edge_count=checked_linear_edges,
        checked_branch_count=len(selected_by_branch),
        weight_digest_changes=weight_changes,
        base_mesh_digest_changes=base_changes,
        modifier_digest_changes=modifier_changes,
        packed_image_count=packed_count,
        expected_packed_image_count=expected_packed,
        checked_tip_helper_count=len(current_helpers),
        mutation_target_count=len(mutation_targets),
        reference_only_tip_helper_count=len(reference_only_helpers),
        topology_ledger_conserved=topology_conserved,
        snapshot_conflict_check_ran=True,
    )


def launch_reopen_validation(blender_executable, blend_path, report_path, project_root):
    script = Path(project_root) / "tools" / "reopen_validate.py"
    completed = subprocess.run(
        [
            str(blender_executable), "--background", str(blend_path),
            "--python", str(script), "--", "--report", str(report_path),
            "--project-root", str(project_root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    payload = None
    if Path(report_path).is_file():
        payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    return completed.returncode, payload, completed.stdout, completed.stderr
