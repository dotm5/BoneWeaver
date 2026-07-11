"""Build a frozen ConversionPlan from preflight, evidence, graph, and settings."""

from __future__ import annotations

import dataclasses
import math

import bpy

from ..contracts import ADDON_VERSION, ALGORITHM_VERSION, CANDIDATE_SCORING_PROFILE, SCHEMA_VERSION
from .canonical import sha256
from .fingerprint import base_mesh_digest, modifier_digest, settings_fingerprint, source_fingerprint_from_states, weight_digest
from .graph_projection import build_proposals
from .models import ConversionPlan, MeshBindingState, ValidationIssue
from .physics_graph import build_physics_graph, with_virtual_tips
from .preflight import run_preflight
from .segment_sampling import build_sampling_hints
from .terminal_candidates import generate_candidates, select_candidate
from .weight_cloud import analyze_weight_cloud, collect_weight_evidence


def _matrix_tuple(matrix):
    return tuple(float(matrix[row][column]) for row in range(4) for column in range(4))


def build_plan(context):
    preflight = run_preflight(context)
    if preflight.armature_object_name is None:
        return None
    armature = bpy.data.objects[preflight.armature_object_name]
    settings = context.scene.uecp_settings
    mesh_objects = tuple(bpy.data.objects[name] for name in preflight.mesh_names)
    mesh_states = []
    for mesh in mesh_objects:
        modifiers = tuple(modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE" and modifier.object == armature)
        transform = armature.matrix_world.inverted_safe() @ mesh.matrix_world
        mesh_states.append(
            MeshBindingState(
                mesh.name, mesh.data.name, len(mesh.data.vertices), len(mesh.data.polygons),
                tuple(modifier.name for modifier in modifiers), modifiers[0].name if len(modifiers) == 1 else "",
                _matrix_tuple(mesh.matrix_world), _matrix_tuple(transform),
                tuple(group.name for group in mesh.vertex_groups), weight_digest(mesh),
                modifier_digest(mesh), base_mesh_digest(mesh),
            )
        )
    mesh_states = tuple(mesh_states)
    evidence = collect_weight_evidence(
        armature, mesh_objects, preflight.selected_bone_names,
        minimum_weight=settings.minimum_weight, weight_exponent=settings.weight_exponent,
        use_vertex_area_weight=settings.use_vertex_area_weight,
        exclusivity_mode=settings.exclusivity_mode,
    ) if mesh_objects else None
    clouds = tuple(
        analyze_weight_cloud(
            state.name, state.head,
            evidence.points_by_bone.get(state.name, ()) if evidence else (),
            preflight.mesh_names,
        )
        for state in preflight.bone_states
    )
    cloud_by_name = {cloud.bone_name: cloud for cloud in clouds}
    graph = build_physics_graph(preflight.bone_states)
    node_by_id = {node.node_id: node for node in graph.nodes}
    solutions = {}
    issues = list(preflight.issues)
    for chain in graph.chains:
        leaf_name = chain.real_bone_names[-1]
        leaf_node = node_by_id[f"real:{leaf_name}"]
        if any(node_by_id[child].kind == "REAL_BONE" for child in leaf_node.child_node_ids):
            continue
        state = next(item for item in preflight.bone_states if item.name == leaf_name)
        parent_edge = next((edge for edge in reversed(graph.edges) if edge.child_node_id == leaf_node.node_id), None)
        parent_direction = None
        reference_length = math.dist(state.head, state.tail)
        if parent_edge:
            parent_direction = tuple(value / parent_edge.rest_length for value in parent_edge.rest_vector)
            reference_length = parent_edge.rest_length
        candidates = generate_candidates(state, cloud_by_name[leaf_name], parent_direction=parent_direction, reference_length=reference_length)
        solution = select_candidate(
            leaf_name, candidates, minimum_score=settings.minimum_candidate_score,
            minimum_margin=settings.candidate_minimum_margin,
            minimum_confidence=settings.minimum_confidence,
        )
        solutions[leaf_name] = solution
        for code in solution.evidence:
            issues.append(ValidationIssue("BLOCKER", code, code.lower(), code, bone_names=(leaf_name,)))
    graph = with_virtual_tips(graph, solutions)
    proposals = build_proposals(graph, preflight.bone_states, settings.physics_profile)
    hints = build_sampling_hints(
        graph, ratio_warning=settings.long_segment_ratio_warning,
        subdivision_max=settings.virtual_preview_subdivision_max,
    ) if settings.enable_segment_sampling_hints else ()
    source = source_fingerprint_from_states(armature, preflight.bone_states, mesh_states)
    settings_hash = settings_fingerprint(settings)
    issues_tuple = tuple(sorted(issues, key=lambda issue: (issue.severity, issue.code, issue.bone_names, issue.object_names)))
    plan = ConversionPlan(
        "uecp.conversion_plan", SCHEMA_VERSION, ALGORITHM_VERSION, ADDON_VERSION, "",
        source, settings_hash, armature.name, armature.data.name, settings.physics_profile,
        CANDIDATE_SCORING_PROFILE, mesh_states, preflight.bone_states, graph, clouds,
        tuple(solutions[name] for name in sorted(solutions)), proposals, hints, issues_tuple,
    )
    payload = dataclasses.asdict(plan)
    payload.pop("plan_id")
    return dataclasses.replace(plan, plan_id=sha256(payload))
