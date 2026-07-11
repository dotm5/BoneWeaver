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
    snapshot_conflict_check_ran: bool


def _empty_report(*issues):
    return ReopenValidationReport(
        False, tuple(sorted(set(issues))), 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, False,
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
    manifest_records = tuple(manifest.get("mutation_records", ()))
    snapshot_records = tuple(snapshot.get("mutation_records", ()))
    if manifest_records != snapshot_records:
        issues.add("UECP_REOPEN_MUTATION_LEDGER_MISMATCH")
    armature_info = manifest.get("armature") or {}
    armature = bpy.data.objects.get(armature_info.get("object_name", ""))
    if armature is None or armature.type != "ARMATURE" or armature.data.name != armature_info.get("data_name"):
        return _empty_report("UECP_REOPEN_ARMATURE_MISSING")
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
        not issues,
        tuple(sorted(issues)),
        len(snapshot_records),
        len(manifest_records),
        len(current),
        checked_linear_edges,
        len(selected_by_branch),
        weight_changes,
        base_changes,
        modifier_changes,
        packed_count,
        expected_packed,
        True,
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
