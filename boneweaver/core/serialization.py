"""Schema-shaped JSON serialization and diagnostic report composition."""

from __future__ import annotations

import dataclasses
import json

import bpy
from .runtime_store import get_performance


def to_data(value):
    if dataclasses.is_dataclass(value):
        return {field.name: to_data(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, tuple):
        return [to_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_data(item) for key, item in value.items()}
    return value


def build_tip_helper_records(plan):
    """Serialize helper classification with frozen pre-apply geometry.

    The parent proposal source is persisted because a manual terminal override
    may supersede ``EXISTING_TIP_HELPER_HEAD`` outside Visual Chain Cleanup.
    Classification flags state whether the helper remains reference-only or is
    an explicitly included cleanup mutation target.
    """

    states = {state.name: state for state in plan.bone_states}
    proposals = {proposal.bone_name: proposal for proposal in plan.proposals}
    records = []
    for classification in plan.tip_helpers:
        state = states[classification.bone_name]
        parent_proposal = proposals.get(classification.parent_bone_name)
        record = to_data(classification)
        record.update(
            {
                "head": to_data(state.head),
                "tail": to_data(state.tail),
                "roll": float(state.roll),
                "use_connect": bool(state.use_connect),
                "parent_name": state.parent_name,
                "parent_proposal_id": (
                    parent_proposal.proposal_id if parent_proposal is not None else None
                ),
                "parent_terminal_source": (
                    parent_proposal.terminal_source if parent_proposal is not None else None
                ),
                "parent_expected_tail": (
                    to_data(parent_proposal.proposed_tail)
                    if parent_proposal is not None
                    else None
                ),
            }
        )
        records.append(record)
    return records


def build_diagnostic_report(plan, validation, snapshot_id=None):
    return {
        "kind": "boneweaver.diagnostic_report",
        "schema_version": plan.schema_version,
        "algorithm_version": plan.algorithm_version,
        "addon_version": plan.addon_version,
        "environment": {"blender_version": bpy.app.version_string, "platform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform)},
        "plan_id": plan.plan_id,
        "physics_graph_id": plan.physics_graph.graph_id,
        "profile": plan.profile,
        "tip_helper_usage": plan.tip_helper_usage,
        "physics_nodes": [to_data(node) for node in plan.physics_graph.nodes],
        "snapshot_id": snapshot_id,
        "issues": [to_data(issue) for issue in plan.issues] + [{"code": code} for code in validation.issues],
        "chains": [to_data(chain) for chain in plan.physics_graph.chains],
        "terminal_candidates": [to_data(solution) for solution in plan.terminal_solutions],
        "weight_statistics": [to_data(cloud) for cloud in plan.weight_clouds],
        "tip_helpers": build_tip_helper_records(plan),
        "segment_sampling_hints": [to_data(hint) for hint in plan.segment_sampling_hints],
        "branch_resolutions": [to_data(item) for item in plan.branch_resolutions],
        "topology_ledger": to_data(plan.topology_ledger),
        "validation": to_data(validation),
        "performance": get_performance(plan.plan_id),
        "side_effect_audit": {
            "weight_digest_changes": validation.weight_digest_changes,
            "base_mesh_digest_changes": validation.base_mesh_digest_changes,
            "modifier_digest_changes": validation.modifier_digest_changes,
            "non_target_bone_changes": validation.non_target_bone_changes,
        },
    }


def conversion_plan_to_data(plan):
    return {
        "kind": plan.kind,
        "schema_version": plan.schema_version,
        "algorithm_version": plan.algorithm_version,
        "addon_version": plan.addon_version,
        "plan_id": plan.plan_id,
        "source_fingerprint": plan.source_fingerprint,
        "settings_fingerprint": plan.settings_fingerprint,
        "armature": {"object_name": plan.armature_object_name, "data_name": plan.armature_data_name},
        "profile": plan.profile,
        "tip_helper_usage": plan.tip_helper_usage,
        "scoring_profile": dict(plan.scoring_profile),
        "meshes": [to_data(item) for item in plan.mesh_states],
        "bones": [to_data(item) for item in plan.bone_states],
        "physics_graph": {
            "graph_id": plan.physics_graph.graph_id,
            "nodes": [to_data(item) for item in plan.physics_graph.nodes],
            "edges": [to_data(item) for item in plan.physics_graph.edges],
            "chains": [to_data(item) for item in plan.physics_graph.chains],
            "issues": list(plan.physics_graph.issue_codes),
        },
        "weight_clouds": [to_data(item) for item in plan.weight_clouds],
        "tip_helpers": build_tip_helper_records(plan),
        "terminal_solutions": [to_data(item) for item in plan.terminal_solutions],
        "proposals": [to_data(item) for item in plan.proposals],
        "segment_sampling_hints": [to_data(item) for item in plan.segment_sampling_hints],
        "branch_resolutions": [to_data(item) for item in plan.branch_resolutions],
        "topology_ledger": to_data(plan.topology_ledger),
        "issues": [to_data(item) for item in plan.issues],
    }


def dumps(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
