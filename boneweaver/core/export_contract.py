"""Hard export gate and conversion audit manifest composition."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import bpy

from .serialization import build_tip_helper_records
from .fingerprint import modifier_digest, settings_fingerprint
from .mesh_scan_cache import mesh_digest_pair
from .validation import armature_state_matches
from .context_guard import ContextStateGuard


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
        return ExportReadinessReport(False, ("BONEWEAVER_EXPORT_PLAN_MISSING",), 0, 0)
    if plan_stale:
        reasons.add("BONEWEAVER_EXPORT_PLAN_STALE")
    if runtime_state != "RESTORABLE":
        reasons.add("BONEWEAVER_EXPORT_APPLY_NOT_SUCCESSFUL")
    if not snapshot_present or not snapshot_payload:
        reasons.add("BONEWEAVER_EXPORT_SNAPSHOT_MISSING")
        return ExportReadinessReport(False, tuple(sorted(reasons)), 0, 0)
    if snapshot_payload.get("plan_id") != plan.plan_id:
        reasons.add("BONEWEAVER_EXPORT_SNAPSHOT_PLAN_MISMATCH")
    if snapshot_payload.get("status") != "APPLIED":
        reasons.add("BONEWEAVER_EXPORT_APPLY_NOT_SUCCESSFUL")
    if (
        snapshot_payload.get("profile") != plan.profile
        or snapshot_payload.get("tip_helper_usage") != plan.tip_helper_usage
    ):
        reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")
    records = tuple(snapshot_payload.get("mutation_records", ()))
    mutation_targets = tuple(proposal.bone_name for proposal in plan.proposals)
    reference_only_helpers = tuple(
        item.bone_name for item in plan.tip_helpers if item.reference_only
    )
    if tuple(snapshot_payload.get("mutation_targets", ())) != mutation_targets:
        reasons.add("BONEWEAVER_EXPORT_MUTATION_LEDGER_MISMATCH")
    if tuple(snapshot_payload.get("reference_only_tip_helpers", ())) != reference_only_helpers:
        reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")
    if tuple(snapshot_payload.get("tip_helpers", ())) != tuple(build_tip_helper_records(plan)):
        reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")
    if any(record.get("bone_name") in reference_only_helpers for record in records):
        reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")
    changed_bones = {
        record.get("bone_name") for record in records
        if record.get("tail_changed") or record.get("roll_changed") or record.get("use_connect_changed")
    }
    if not records or not changed_bones:
        reasons.add("BONEWEAVER_EXPORT_NO_ACTUAL_MUTATION")
    validation = snapshot_payload.get("post_validation") or {}
    if not validation.get("success"):
        reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")
    for key, code in (
        ("weight_digest_changes", "BONEWEAVER_WEIGHT_DIGEST_CHANGED"),
        ("base_mesh_digest_changes", "BONEWEAVER_BASE_MESH_CHANGED"),
        ("modifier_digest_changes", "BONEWEAVER_MODIFIER_DIGEST_CHANGED"),
        ("non_target_bone_changes", "BONEWEAVER_NON_TARGET_BONE_CHANGED"),
    ):
        if validation.get(key, 0):
            reasons.add(code)
    mesh_results = tuple(validation.get("mesh_validation_results", ()))
    if not mesh_results or any(result.get("result") == "FAIL_AND_ROLLBACK" for result in mesh_results):
        reasons.add("BONEWEAVER_NEUTRAL_MESH_CHANGED")
    topology = snapshot_payload.get("topology_ledger") or {}
    if not topology:
        reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_MISSING")
    else:
        if topology.get("unresolved_branch_count", 0):
            reasons.add("BONEWEAVER_BRANCH_AMBIGUOUS")
        if topology.get("selected_hierarchy_edge_count", 0) != (
            topology.get("linear_edge_count", 0) + topology.get("branch_edge_count", 0)
        ):
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if topology.get("proposal_count") != len(plan.proposals):
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if topology.get("mutation_record_count") != len(records):
            reasons.add("BONEWEAVER_EXPORT_MUTATION_LEDGER_MISMATCH")
        selected_count = topology.get("selected_bone_count", 0)
        mutation_target_count = topology.get("mutation_target_count", 0)
        reference_only_count = topology.get("reference_only_tip_helper_count", 0)
        skipped_count = topology.get("skipped_by_design_count", 0)
        if selected_count != mutation_target_count + reference_only_count + skipped_count:
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if topology.get("proposal_count", 0) != mutation_target_count:
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if mutation_target_count != len(mutation_targets):
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
        if reference_only_count != len(reference_only_helpers):
            reasons.add("BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE")
    if any(getattr(issue, "severity", None) == "BLOCKER" for issue in plan.issues):
        reasons.add("BONEWEAVER_EXPORT_UNRESOLVED_BLOCKER")
    if any(
        resolution.selected_child_name is None and resolution.result != "KEEP_ORIGINAL"
        for resolution in plan.branch_resolutions
    ):
        reasons.add("BONEWEAVER_BRANCH_AMBIGUOUS")
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


def _vector_close(first, second, epsilon=1.0e-6):
    return len(first) == len(second) and all(
        abs(float(a) - float(b)) <= epsilon for a, b in zip(first, second)
    )


def _bone_roll(bone):
    _axis, roll = bone.AxisRollFromMatrix(bone.matrix_local.to_3x3())
    return float(roll)


def _matrix_is_identity(matrix, epsilon=1.0e-6):
    return all(
        abs(float(matrix[row][column]) - (1.0 if row == column else 0.0)) <= epsilon
        for row in range(4)
        for column in range(4)
    )


def _current_export_state_reasons(context, plan, snapshot_payload):
    """Revalidate mutable scene state immediately before Pack/Save."""

    reasons = set()
    settings = getattr(context.scene, "boneweaver_settings", None)
    if settings is None or settings_fingerprint(settings) != plan.settings_fingerprint:
        reasons.add("BONEWEAVER_SETTINGS_CHANGED_AFTER_ANALYZE")
    armature = context.scene.objects.get(plan.armature_object_name)
    if (
        armature is None
        or armature.type != "ARMATURE"
        or armature.data.name != plan.armature_data_name
    ):
        reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")
        return reasons
    if not armature_state_matches(
        armature,
        snapshot_payload.get("whole_armature_post_state") or {},
    ):
        reasons.add("BONEWEAVER_NON_TARGET_BONE_CHANGED")
    armature_matrix = tuple(
        float(armature.matrix_world[row][column])
        for row in range(4)
        for column in range(4)
    )
    if not _vector_close(
        armature_matrix,
        (snapshot_payload.get("armature") or {}).get("matrix_world", ()),
    ):
        reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")
    pose_bones = (
        armature.pose.bones
        if settings is not None and settings.strict_whole_armature_pose
        else tuple(armature.pose.bones.get(state.name) for state in plan.bone_states)
    )
    if any(
        bone is not None and not _matrix_is_identity(bone.matrix_basis)
        for bone in pose_bones
    ):
        reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")

    for name, expected in (snapshot_payload.get("expected_post_bones") or {}).items():
        bone = armature.data.bones.get(name)
        if bone is None:
            reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")
            continue
        if (
            not _vector_close(tuple(bone.head_local), expected.get("head", ()))
            or (bone.parent.name if bone.parent else None) != expected.get("parent_name")
            or not _vector_close(tuple(bone.tail_local), expected.get("tail", ()))
            or not math.isclose(
                _bone_roll(bone),
                float(expected.get("roll", _bone_roll(bone))),
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
            or bool(bone.use_connect) != bool(expected.get("use_connect"))
        ):
            reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")

    for helper in snapshot_payload.get("tip_helpers", ()):
        bone = armature.data.bones.get(helper.get("bone_name", ""))
        if bone is None:
            reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")
            continue
        parent_name = bone.parent.name if bone.parent else None
        mismatch = (
            parent_name != helper.get("parent_name")
            or not _vector_close(tuple(bone.head_local), helper.get("head", ()))
        )
        if helper.get("reference_only") is True:
            mismatch = mismatch or (
                not _vector_close(tuple(bone.tail_local), helper.get("tail", ()))
                or not math.isclose(
                    _bone_roll(bone),
                    float(helper.get("roll", _bone_roll(bone))),
                    rel_tol=0.0,
                    abs_tol=1.0e-6,
                )
                or bool(bone.use_connect) != bool(helper.get("use_connect"))
            )
        if mismatch:
            reasons.add("BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH")

    for expected in plan.mesh_states:
        mesh = context.scene.objects.get(expected.object_name)
        if mesh is None or mesh.type != "MESH":
            reasons.update(
                {
                    "BONEWEAVER_WEIGHT_DIGEST_CHANGED",
                    "BONEWEAVER_BASE_MESH_CHANGED",
                    "BONEWEAVER_MODIFIER_DIGEST_CHANGED",
                }
            )
            continue
        mesh_matrix = tuple(
            float(mesh.matrix_world[row][column])
            for row in range(4)
            for column in range(4)
        )
        if not _vector_close(mesh_matrix, expected.object_matrix_world):
            reasons.add("BONEWEAVER_EXPORT_POST_VALIDATION_FAILED")
        current_weight, current_base = mesh_digest_pair(mesh)
        if current_weight != expected.vertex_group_digest:
            reasons.add("BONEWEAVER_WEIGHT_DIGEST_CHANGED")
        if current_base != expected.base_mesh_digest:
            reasons.add("BONEWEAVER_BASE_MESH_CHANGED")
        if modifier_digest(mesh) != expected.modifier_digest:
            reasons.add("BONEWEAVER_MODIFIER_DIGEST_CHANGED")
    return reasons


def assert_export_ready(context, plan, runtime):
    payload = load_snapshot_payload(runtime.snapshot_text_name)
    report = evaluate_export_readiness(
        plan,
        runtime_state=runtime.state,
        snapshot_payload=payload,
        snapshot_present=payload is not None,
        plan_stale=runtime.plan_id != plan.plan_id,
    )
    current_reasons = set()
    if payload:
        with ContextStateGuard(context):
            if context.object is not None and context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.update()
            current_reasons = _current_export_state_reasons(context, plan, payload)
    if current_reasons:
        reasons = tuple(sorted(set(report.reasons).union(current_reasons)))
        report = ExportReadinessReport(
            False,
            reasons,
            report.mutation_record_count,
            report.changed_bone_count,
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
    mutation_targets = [proposal.bone_name for proposal in plan.proposals]
    reference_only_tip_helpers = [
        item.bone_name for item in plan.tip_helpers if item.reference_only
    ]
    return {
        "kind": "boneweaver.export_manifest",
        "schema_version": plan.schema_version,
        "algorithm_version": plan.algorithm_version,
        "addon_version": plan.addon_version,
        "source_file_sha256": source_sha,
        "source_file_timestamp": source_timestamp,
        "plan_id": plan.plan_id,
        "graph_id": plan.physics_graph.graph_id,
        "profile": plan.profile,
        "tip_helper_usage": plan.tip_helper_usage,
        "armature": {
            "object_name": plan.armature_object_name,
            "data_name": plan.armature_data_name,
            "matrix_world": (snapshot_payload.get("armature") or {}).get(
                "matrix_world", []
            ),
        },
        "mesh_object_matrices": {
            state.object_name: list(state.object_matrix_world)
            for state in plan.mesh_states
        },
        "bone_parents": {
            state.name: state.parent_name for state in plan.bone_states
        },
        "physics_edges": [
            _asdict(edge) for edge in plan.physics_graph.edges
        ],
        "physics_nodes": [
            _asdict(node) for node in plan.physics_graph.nodes
        ],
        "snapshot_id": snapshot_payload.get("snapshot_id"),
        "whole_armature_post_digest": snapshot_payload.get(
            "whole_armature_post_digest"
        ),
        "whole_armature_post_state": snapshot_payload.get(
            "whole_armature_post_state", {}
        ),
        "tolerance_mode": tolerance_mode,
        "per_mesh_tolerance": validation.get("mesh_validation_results", []),
        "maximum_delta": validation.get("maximum_neutral_mesh_delta", 0.0),
        "rms_delta": max((item.get("rms_delta", 0.0) for item in validation.get("mesh_validation_results", [])), default=0.0),
        "selected_bones": [state.name for state in plan.bone_states],
        "target_bones": mutation_targets,
        "mutation_targets": mutation_targets,
        "reference_only_tip_helpers": reference_only_tip_helpers,
        "tip_helpers": build_tip_helper_records(plan),
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
