"""Build a frozen ConversionPlan from preflight, evidence, graph, and settings."""

from __future__ import annotations

import dataclasses
import math
import time

import bpy
from mathutils import Vector

from ..contracts import ADDON_VERSION, ALGORITHM_VERSION, CANDIDATE_SCORING_PROFILE, SCHEMA_VERSION
from .canonical import sha256
from .fingerprint import base_mesh_digest, modifier_digest, settings_fingerprint, source_fingerprint_from_states, weight_digest
from .graph_projection import build_proposals
from .models import ConversionPlan, MeshBindingState, ValidationIssue
from .physics_graph import build_physics_graph, with_virtual_tips
from .preflight import run_preflight
from .segment_sampling import build_sampling_hints
from .terminal_candidates import authoritative_solution, generate_candidates, select_candidate
from .weight_cloud import analyze_weight_cloud, collect_weight_evidence
from .roll_solver import minimal_twist_reference, parallel_transport_reference, radial_reference


_LAST_BUILD_METRICS = {}


def last_build_metrics():
    return dict(_LAST_BUILD_METRICS)


def _matrix_tuple(matrix):
    return tuple(float(matrix[row][column]) for row in range(4) for column in range(4))


def _manual_solution(settings, state, armature):
    override = next((item for item in settings.terminal_overrides if item.enabled and item.bone_name == state.name and item.mode != "NONE"), None)
    if override is None:
        return None
    tail = None
    if override.mode == "EXPLICIT_DIRECTION_LENGTH" and override.length > 0.0:
        direction = Vector(override.direction)
        if direction.length > 1.0e-9:
            tail = Vector(state.head) + direction.normalized() * override.length
    elif override.mode == "CURSOR_POSITION":
        tail = armature.matrix_world.inverted_safe() @ bpy.context.scene.cursor.location
    elif override.mode == "REFERENCE_OBJECT" and override.reference_object:
        tail = armature.matrix_world.inverted_safe() @ override.reference_object.matrix_world.translation
    elif override.mode == "MESH_VERTEX":
        mesh = bpy.data.objects.get(override.mesh_object_name)
        if mesh and mesh.type == "MESH" and 0 <= override.vertex_index < len(mesh.data.vertices):
            tail = armature.matrix_world.inverted_safe() @ mesh.matrix_world @ mesh.data.vertices[override.vertex_index].co
    if tail is None:
        return authoritative_solution(state.name, state.head, state.head, source="MANUAL_OVERRIDE", kind="MANUAL")
    return authoritative_solution(state.name, state.head, tuple(float(value) for value in tail), source="MANUAL_OVERRIDE", kind="MANUAL")


def _roll_proposals(proposals, graph, bone_states, settings, armature):
    states = {state.name: state for state in bone_states}
    by_name = {proposal.bone_name: proposal for proposal in proposals}
    updated = {}
    if settings.radial_reference_mode == "CURSOR":
        radial_point = tuple(armature.matrix_world.inverted_safe() @ bpy.context.scene.cursor.location)
    elif settings.radial_reference_mode == "OBJECT" and settings.radial_reference_object:
        radial_point = tuple(armature.matrix_world.inverted_safe() @ settings.radial_reference_object.matrix_world.translation)
    elif settings.radial_reference_mode == "BONE_HEAD" and settings.radial_reference_bone in armature.data.bones:
        radial_point = tuple(armature.data.bones[settings.radial_reference_bone].head_local)
    else:
        radial_point = (0.0, 0.0, 0.0)
    for chain in graph.chains:
        parent_z = None
        for name in chain.real_bone_names:
            proposal = by_name.get(name)
            if proposal is None:
                continue
            state = states[name]
            new_y = tuple(proposal.proposed_tail[index] - proposal.original_head[index] for index in range(3))
            if settings.roll_mode == "PARALLEL_TRANSPORT" and parent_z is not None:
                reference, fallback = parallel_transport_reference(new_y, parent_z, state.local_z, settings.parallel_transport_weight, settings.old_axis_weight)
            elif settings.roll_mode == "RADIAL_REFERENCE":
                reference, fallback = radial_reference(new_y, state.head, radial_point)
            elif settings.roll_mode == "KEEP_NUMERIC_ROLL":
                reference, fallback = state.local_z, False
            else:
                reference, fallback = minimal_twist_reference(new_y, state.local_z, state.local_x, parent_z)
            codes = proposal.issue_codes + (("UECP_ROLL_FALLBACK_USED",) if fallback else ())
            if settings.roll_mode == "KEEP_NUMERIC_ROLL":
                codes += ("UECP_KEEP_NUMERIC_ROLL",)
            updated[name] = dataclasses.replace(proposal, proposed_roll_reference_z=tuple(reference), issue_codes=codes)
            parent_z = tuple(reference)
    return tuple(updated.get(proposal.bone_name, proposal) for proposal in proposals)


def build_plan(context):
    global _LAST_BUILD_METRICS
    started = time.perf_counter()
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
    weight_started = time.perf_counter()
    evidence = collect_weight_evidence(
        armature, mesh_objects, preflight.selected_bone_names,
        minimum_weight=settings.minimum_weight, weight_exponent=settings.weight_exponent,
        use_vertex_area_weight=settings.use_vertex_area_weight,
        exclusivity_mode=settings.exclusivity_mode,
    ) if mesh_objects else None
    weight_finished = time.perf_counter()
    clouds = tuple(
        analyze_weight_cloud(
            state.name, state.head,
            evidence.points_by_bone.get(state.name, ()) if evidence else (),
            preflight.mesh_names, settings.terminal_percentile,
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
        manual = _manual_solution(settings, state, armature)
        if manual is not None:
            solutions[leaf_name] = manual
            if manual.requires_confirmation:
                issues.append(ValidationIssue("BLOCKER", "UECP_VIRTUAL_TIP_INVALID", "uecp_virtual_tip_invalid", "Invalid manual terminal override", bone_names=(leaf_name,)))
            continue
        external_children = tuple(name for name in state.child_names if name not in preflight.selected_bone_names)
        if len(external_children) == 1:
            child = armature.data.bones.get(external_children[0])
            if child is not None and not bool(child.get("is_socket", False)):
                solution = authoritative_solution(
                    leaf_name, state.head, tuple(float(value) for value in child.head_local),
                    source="UNIQUE_DIRECT_CHILD_HEAD", kind="DIRECT_CHILD",
                )
                solutions[leaf_name] = solution
                if solution.requires_confirmation:
                    for code in solution.evidence:
                        issues.append(ValidationIssue("BLOCKER", code, code.lower(), code, bone_names=(leaf_name,)))
                continue
        parent_edge = next((edge for edge in reversed(graph.edges) if edge.child_node_id == leaf_node.node_id), None)
        parent_direction = None
        reference_length = math.dist(state.head, state.tail)
        if parent_edge:
            parent_direction = tuple(value / parent_edge.rest_length for value in parent_edge.rest_vector)
            reference_length = parent_edge.rest_length
        length_override = None
        if settings.tip_length_mode == "ABSOLUTE":
            length_override = settings.absolute_tip_length
        elif settings.tip_length_mode in {"PREVIOUS_SEGMENT", "CHAIN_MEDIAN"}:
            length_override = reference_length
        candidates = generate_candidates(
            state, cloud_by_name[leaf_name], parent_direction=parent_direction,
            reference_length=reference_length, length_override=length_override,
            minimum_length_ratio=settings.minimum_length_ratio,
            maximum_length_ratio=settings.maximum_length_ratio,
            maximum_auto_bend_degrees=settings.maximum_auto_bend_degrees,
            explicit_axis_label=settings.bone_forward_axis if settings.bone_forward_axis != "AUTO" else None,
        )
        mode_kinds = {
            "IMPORTED_FORWARD_AXIS_ONLY": {"IMPORTED_AXIS"},
            "WEIGHT_CLOUD_ONLY": {"WEIGHT_PRINCIPAL_AXIS", "WEIGHT_CENTROID", "WEIGHT_PLANAR_BLEND"},
            "PARENT_EXTRAPOLATION_ONLY": {"PARENT_TANGENT"},
            "ORIGINAL_AXIS_ONLY": {"ORIGINAL_DISPLAY_AXIS"},
            "UNIQUE_CHILD_ONLY": set(),
            "MANUAL_ONLY": set(),
        }
        if settings.terminal_mode in mode_kinds:
            candidates = tuple(candidate for candidate in candidates if candidate.kind in mode_kinds[settings.terminal_mode])
        if settings.terminal_mode == "IMPORTED_FORWARD_AXIS_ONLY" and settings.bone_forward_axis != "AUTO":
            candidates = tuple(candidate for candidate in candidates if candidate.axis_label == settings.bone_forward_axis)
        solution = select_candidate(
            leaf_name, candidates, minimum_score=settings.minimum_candidate_score,
            minimum_margin=settings.candidate_minimum_margin,
            minimum_confidence=settings.minimum_confidence,
        )
        solutions[leaf_name] = solution
        for code in solution.evidence:
            issues.append(ValidationIssue("BLOCKER", code, code.lower(), code, bone_names=(leaf_name,)))
    graph = with_virtual_tips(graph, solutions)
    proposals = _roll_proposals(
        build_proposals(graph, preflight.bone_states, settings.physics_profile),
        graph, preflight.bone_states, settings, armature,
    )
    if settings.create_role_collections:
        proposals = tuple(
            dataclasses.replace(proposal, issue_codes=proposal.issue_codes + ("UECP_CREATE_ROLE_COLLECTIONS",))
            for proposal in proposals
        )
    hints = build_sampling_hints(
        graph, ratio_warning=settings.long_segment_ratio_warning,
        subdivision_max=settings.virtual_preview_subdivision_max,
    ) if settings.enable_segment_sampling_hints else ()
    fingerprint_started = time.perf_counter()
    source = source_fingerprint_from_states(armature, preflight.bone_states, mesh_states)
    settings_hash = settings_fingerprint(settings)
    fingerprint_finished = time.perf_counter()
    issues_tuple = tuple(sorted(issues, key=lambda issue: (issue.severity, issue.code, issue.bone_names, issue.object_names)))
    plan = ConversionPlan(
        "uecp.conversion_plan", SCHEMA_VERSION, ALGORITHM_VERSION, ADDON_VERSION, "",
        source, settings_hash, armature.name, armature.data.name, settings.physics_profile,
        CANDIDATE_SCORING_PROFILE, mesh_states, preflight.bone_states, graph, clouds,
        tuple(solutions[name] for name in sorted(solutions)), proposals, hints, issues_tuple,
    )
    payload = dataclasses.asdict(plan)
    payload.pop("plan_id")
    result = dataclasses.replace(plan, plan_id=sha256(payload))
    finished = time.perf_counter()
    _LAST_BUILD_METRICS = {
        "bone_count": len(preflight.bone_states),
        "mesh_count": len(mesh_states),
        "vertex_count": evidence.vertex_count if evidence else 0,
        "membership_count": evidence.membership_count if evidence else 0,
        "analyze_time": finished - started,
        "fingerprint_time": fingerprint_finished - fingerprint_started,
        "weight_cloud_time": weight_finished - weight_started,
        "peak_temporary_point_count": evidence.peak_point_count if evidence else 0,
    }
    return result
