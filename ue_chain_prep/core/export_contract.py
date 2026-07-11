"""Hard export gate and conversion audit manifest composition."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import bpy


@dataclass(frozen=True, slots=True)
class ExportReadinessReport:
    ready: bool
    reasons: tuple[str, ...]
    mutation_record_count: int
    changed_bone_count: int


class ExportReadinessError(RuntimeError):
    def __init__(self, report):
        super().__init__(", ".join(report.reasons))
        self.report = report


def evaluate_export_readiness(
    plan,
    *,
    runtime_state,
    snapshot_payload,
    snapshot_present,
    plan_stale,
):
    reasons = set()
    if plan is None:
        return ExportReadinessReport(False, ("UECP_EXPORT_PLAN_MISSING",), 0, 0)
    if plan_stale:
        reasons.add("UECP_EXPORT_PLAN_STALE")
    if runtime_state != "RESTORABLE":
        reasons.add("UECP_EXPORT_APPLY_NOT_SUCCESSFUL")
    if not snapshot_present or not snapshot_payload:
        reasons.add("UECP_EXPORT_SNAPSHOT_MISSING")
        return ExportReadinessReport(False, tuple(sorted(reasons)), 0, 0)
    if snapshot_payload.get("plan_id") != plan.plan_id:
        reasons.add("UECP_EXPORT_SNAPSHOT_PLAN_MISMATCH")
    if snapshot_payload.get("status") != "APPLIED":
        reasons.add("UECP_EXPORT_APPLY_NOT_SUCCESSFUL")
    records = tuple(snapshot_payload.get("mutation_records", ()))
    changed_bones = {
        record.get("bone_name") for record in records
        if record.get("tail_changed") or record.get("roll_changed") or record.get("use_connect_changed")
    }
    if not records or not changed_bones:
        reasons.add("UECP_EXPORT_NO_ACTUAL_MUTATION")
    validation = snapshot_payload.get("post_validation") or {}
    if not validation.get("success"):
        reasons.add("UECP_EXPORT_POST_VALIDATION_FAILED")
    for key, code in (
        ("weight_digest_changes", "UECP_WEIGHT_DIGEST_CHANGED"),
        ("base_mesh_digest_changes", "UECP_BASE_MESH_CHANGED"),
        ("modifier_digest_changes", "UECP_MODIFIER_DIGEST_CHANGED"),
        ("non_target_bone_changes", "UECP_NON_TARGET_BONE_CHANGED"),
    ):
        if validation.get(key, 0):
            reasons.add(code)
    mesh_results = tuple(validation.get("mesh_validation_results", ()))
    if not mesh_results or any(result.get("result") == "FAIL_AND_ROLLBACK" for result in mesh_results):
        reasons.add("UECP_NEUTRAL_MESH_CHANGED")
    topology = snapshot_payload.get("topology_ledger") or {}
    if not topology:
        reasons.add("UECP_EXPORT_TOPOLOGY_LEDGER_MISSING")
    else:
        if topology.get("unresolved_branch_count", 0):
            reasons.add("UECP_BRANCH_AMBIGUOUS")
        if topology.get("selected_hierarchy_edge_count", 0) != (
            topology.get("linear_edge_count", 0) + topology.get("branch_edge_count", 0)
        ):
            reasons.add("UECP_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if topology.get("proposal_count") != len(plan.proposals):
            reasons.add("UECP_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if topology.get("mutation_record_count") != len(records):
            reasons.add("UECP_EXPORT_MUTATION_LEDGER_MISMATCH")
    if any(getattr(issue, "severity", None) == "BLOCKER" for issue in plan.issues):
        reasons.add("UECP_EXPORT_UNRESOLVED_BLOCKER")
    if any(
        resolution.selected_child_name is None and resolution.result != "KEEP_ORIGINAL"
        for resolution in plan.branch_resolutions
    ):
        reasons.add("UECP_BRANCH_AMBIGUOUS")
    return ExportReadinessReport(
        not reasons, tuple(sorted(reasons)), len(records), len(changed_bones),
    )


def load_snapshot_payload(text_name):
    text = bpy.data.texts.get(text_name) if text_name else None
    if text is None:
        return None
    try:
        return json.loads(text.as_string())
    except (TypeError, ValueError):
        return None


def assert_export_ready(context, plan, runtime):
    payload = load_snapshot_payload(runtime.snapshot_text_name)
    report = evaluate_export_readiness(
        plan,
        runtime_state=runtime.state,
        snapshot_payload=payload,
        snapshot_present=payload is not None,
        plan_stale=runtime.plan_id != plan.plan_id,
    )
    if not report.ready:
        raise ExportReadinessError(report)
    return report, payload


def file_signature(path):
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    stat = source.stat()
    return digest.hexdigest(), stat.st_mtime_ns


def _asdict(value):
    return dataclasses.asdict(value) if dataclasses.is_dataclass(value) else value


def build_export_manifest(
    source_path,
    plan,
    snapshot_payload,
    *,
    tolerance_mode,
    packed_image_count,
    export_time=None,
):
    source_sha, source_timestamp = file_signature(source_path)
    validation = snapshot_payload["post_validation"]
    terminal_classes = [solution.resolution_class for solution in plan.terminal_solutions]
    return {
        "kind": "uecp.export_manifest",
        "schema_version": plan.schema_version,
        "algorithm_version": plan.algorithm_version,
        "addon_version": plan.addon_version,
        "source_file_sha256": source_sha,
        "source_file_timestamp": source_timestamp,
        "plan_id": plan.plan_id,
        "graph_id": plan.physics_graph.graph_id,
        "armature": {
            "object_name": plan.armature_object_name,
            "data_name": plan.armature_data_name,
        },
        "bone_parents": {
            state.name: state.parent_name for state in plan.bone_states
        },
        "physics_edges": [
            _asdict(edge) for edge in plan.physics_graph.edges
        ],
        "snapshot_id": snapshot_payload.get("snapshot_id"),
        "tolerance_mode": tolerance_mode,
        "per_mesh_tolerance": validation.get("mesh_validation_results", []),
        "maximum_delta": validation.get("maximum_neutral_mesh_delta", 0.0),
        "rms_delta": max((item.get("rms_delta", 0.0) for item in validation.get("mesh_validation_results", [])), default=0.0),
        "target_bones": [state.name for state in plan.bone_states],
        "mutation_records": snapshot_payload.get("mutation_records", []),
        "branch_resolutions": [_asdict(item) for item in plan.branch_resolutions],
        "automatic_terminal_count": terminal_classes.count("AUTO_CONFIDENT"),
        "safe_fallback_terminal_count": terminal_classes.count("AUTO_SAFE_FALLBACK"),
        "manual_terminal_count": terminal_classes.count("MANUAL"),
        "topology_ledger": snapshot_payload.get("topology_ledger"),
        "weight_digests": {state.object_name: state.vertex_group_digest for state in plan.mesh_states},
        "base_mesh_digests": {state.object_name: state.base_mesh_digest for state in plan.mesh_states},
        "modifier_digests": {state.object_name: state.modifier_digest for state in plan.mesh_states},
        "packed_image_count": int(packed_image_count),
        "export_time": export_time or dt.datetime.now(dt.timezone.utc).isoformat(),
    }
