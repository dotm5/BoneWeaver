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


def build_diagnostic_report(plan, validation, snapshot_id=None):
    return {
        "kind": "uecp.diagnostic_report",
        "schema_version": plan.schema_version,
        "algorithm_version": plan.algorithm_version,
        "addon_version": plan.addon_version,
        "environment": {"blender_version": bpy.app.version_string, "platform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform)},
        "plan_id": plan.plan_id,
        "physics_graph_id": plan.physics_graph.graph_id,
        "snapshot_id": snapshot_id,
        "issues": [to_data(issue) for issue in plan.issues] + [{"code": code} for code in validation.issues],
        "chains": [to_data(chain) for chain in plan.physics_graph.chains],
        "terminal_candidates": [to_data(solution) for solution in plan.terminal_solutions],
        "weight_statistics": [to_data(cloud) for cloud in plan.weight_clouds],
        "segment_sampling_hints": [to_data(hint) for hint in plan.segment_sampling_hints],
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
        "terminal_solutions": [to_data(item) for item in plan.terminal_solutions],
        "proposals": [to_data(item) for item in plan.proposals],
        "segment_sampling_hints": [to_data(item) for item in plan.segment_sampling_hints],
        "issues": [to_data(item) for item in plan.issues],
    }


def dumps(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
