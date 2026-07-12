"""Build a frozen ConversionPlan from preflight, evidence, graph, and settings."""

from __future__ import annotations

import dataclasses
import math
import time

import bpy
from mathutils import Vector

from ..contracts import (
    ADDON_VERSION,
    ALGORITHM_VERSION,
    CANDIDATE_SCORING_PROFILE,
    PhysicsProfile,
    SCHEMA_VERSION,
    TipHelperUsage,
)
from .canonical import sha256
from .branch_resolution import resolve_branch
from .fingerprint import settings_fingerprint, source_fingerprint_from_states
from .graph_projection import build_proposals
from .mesh_scan_cache import MeshScanCache
from .models import ConversionPlan, MeshBindingState, ValidationIssue
from .mutation_ledger import build_topology_projection_ledger
from .physics_graph import build_physics_graph, with_skipped_mutation_targets, with_virtual_tips
from .overrides import (
    armature_structural_fingerprint,
    find_branch_override,
    find_terminal_override,
)
from .preflight import run_preflight
from .segment_sampling import build_sampling_hints
from .terminal_candidates import (
    authoritative_solution,
    generate_candidates,
    safe_parent_chain_fallback,
    select_candidate,
)
from .tip_helpers import classify_tip_helpers
from .weight_cloud import analyze_weight_cloud
from .weight_islands import resolve_weight_islands
from .roll_solver import minimal_twist_reference, parallel_transport_reference, radial_reference


_LAST_BUILD_METRICS = {}
_BRANCH_BLOCK_MESSAGES = {
    "BONEWEAVER_BRANCH_AMBIGUOUS": "Branch continuation evidence is ambiguous",
    "BONEWEAVER_BRANCH_AUTO_MAIN_SKELETON_FORBIDDEN": "Automatic branch selection is forbidden on main-skeleton semantics",
    "BONEWEAVER_BRANCH_AUTO_CONTROL_FORBIDDEN": "Automatic branch selection is forbidden on control or IK semantics",
    "BONEWEAVER_BRANCH_AUTO_SOCKET_FORBIDDEN": "Automatic branch selection is forbidden on socket semantics",
    "BONEWEAVER_BRANCH_AUTO_TWIST_FORBIDDEN": "Automatic branch selection is forbidden on twist semantics",
    "BONEWEAVER_BRANCH_AUTO_SECONDARY_SEMANTICS_REQUIRED": "Automatic branch selection requires explicit secondary-physics semantics",
}


def last_build_metrics():
    return dict(_LAST_BUILD_METRICS)


def _matrix_tuple(matrix):
    return tuple(float(matrix[row][column]) for row in range(4) for column in range(4))


def _manual_solution(settings, state, armature, *, chain_id, structural_fingerprint):
    override, legacy = find_terminal_override(
        settings.terminal_overrides,
        armature_data_name=armature.data.name,
        armature_structural_fingerprint=structural_fingerprint,
        bone_name=state.name,
        chain_id=chain_id,
    )
    if override is None:
        return None, legacy
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
        return authoritative_solution(state.name, state.head, state.head, source="MANUAL_OVERRIDE", kind="MANUAL"), legacy
    return authoritative_solution(state.name, state.head, tuple(float(value) for value in tail), source="MANUAL_OVERRIDE", kind="MANUAL"), legacy


def _roll_proposals(proposals, graph, bone_states, settings, armature):
    states = {state.name: state for state in bone_states}
    by_name = {proposal.bone_name: proposal for proposal in proposals}
    updated = {}
    roll_mode = (
        "MINIMAL_TWIST"
        if settings.physics_profile == PhysicsProfile.VISUAL_CHAIN_CLEANUP.value
        else settings.roll_mode
    )
    if roll_mode == "RADIAL_REFERENCE" and settings.radial_reference_mode == "CURSOR":
        radial_point = tuple(armature.matrix_world.inverted_safe() @ bpy.context.scene.cursor.location)
    elif roll_mode == "RADIAL_REFERENCE" and settings.radial_reference_mode == "OBJECT" and settings.radial_reference_object:
        radial_point = tuple(armature.matrix_world.inverted_safe() @ settings.radial_reference_object.matrix_world.translation)
    elif roll_mode == "RADIAL_REFERENCE" and settings.radial_reference_mode == "BONE_HEAD" and settings.radial_reference_bone in armature.data.bones:
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
            if roll_mode == "PARALLEL_TRANSPORT" and parent_z is not None:
                reference, fallback = parallel_transport_reference(new_y, parent_z, state.local_z, settings.parallel_transport_weight, settings.old_axis_weight)
            elif roll_mode == "RADIAL_REFERENCE":
                reference, fallback = radial_reference(new_y, state.head, radial_point)
            elif roll_mode == "KEEP_NUMERIC_ROLL":
                reference, fallback = state.local_z, False
            else:
                reference, fallback = minimal_twist_reference(new_y, state.local_z, state.local_x, parent_z)
            codes = proposal.issue_codes + (("BONEWEAVER_ROLL_FALLBACK_USED",) if fallback else ())
            if roll_mode == "KEEP_NUMERIC_ROLL":
                codes += ("BONEWEAVER_KEEP_NUMERIC_ROLL",)
            updated[name] = dataclasses.replace(proposal, proposed_roll_reference_z=tuple(reference), issue_codes=codes)
            parent_z = tuple(reference)
    return tuple(updated.get(proposal.bone_name, proposal) for proposal in proposals)


def build_plan(
    context,
    *,
    scope_names: tuple[str, ...] | None = None,
    scoped_branch_continuations: tuple[tuple[str, str], ...] = (),
    required_reference_tip_helper_names: tuple[str, ...] = (),
):
    global _LAST_BUILD_METRICS
    started = time.perf_counter()
    preflight = run_preflight(context, scope_names=scope_names)
    if preflight.armature_object_name is None:
        return None
    armature = bpy.data.objects[preflight.armature_object_name]
    settings = context.scene.boneweaver_settings
    visual_cleanup = (
        settings.physics_profile == PhysicsProfile.VISUAL_CHAIN_CLEANUP.value
    )
    tip_helper_usage = getattr(
        settings,
        "tip_helper_usage",
        TipHelperUsage.REFERENCE_ONLY.value,
    )
    structural_fingerprint = armature_structural_fingerprint(armature)
    mesh_objects = tuple(bpy.data.objects[name] for name in preflight.mesh_names)
    scan_cache = MeshScanCache.scan(
        armature, mesh_objects, preflight.selected_bone_names,
        minimum_weight=settings.minimum_weight,
        weight_exponent=settings.weight_exponent,
        use_vertex_area_weight=settings.use_vertex_area_weight,
        exclusivity_mode=settings.exclusivity_mode,
    )
    scans_by_name = {scan.object_name: scan for scan in scan_cache.meshes}
    mesh_states = []
    for mesh in mesh_objects:
        scan = scans_by_name[mesh.name]
        modifiers = tuple(modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE" and modifier.object == armature)
        transform = armature.matrix_world.inverted_safe() @ mesh.matrix_world
        mesh_states.append(
            MeshBindingState(
                mesh.name, mesh.data.name, len(mesh.data.vertices), len(mesh.data.polygons),
                tuple(modifier.name for modifier in modifiers), modifiers[0].name if len(modifiers) == 1 else "",
                _matrix_tuple(mesh.matrix_world), _matrix_tuple(transform),
                scan.vertex_group_names, scan.weight_digest,
                scan.modifier_digest, scan.base_mesh_digest,
            )
        )
    mesh_states = tuple(mesh_states)
    weight_started = time.perf_counter()
    clouds_list = []
    weight_issues = []
    for state in preflight.bone_states:
        island_resolution = resolve_weight_islands(
            state.name,
            state.head,
            scan_cache.per_mesh_inputs_by_bone.get(state.name, ()),
            policy=settings.weight_island_policy,
        )
        cloud = analyze_weight_cloud(
            state.name, state.head, island_resolution.selected_weighted_points,
            tuple(item.mesh_name for item in island_resolution.per_mesh_clouds),
            settings.terminal_percentile,
        )
        cloud = dataclasses.replace(
            cloud,
            warnings=tuple(sorted(set(cloud.warnings + island_resolution.warnings))),
            per_mesh_clouds=island_resolution.per_mesh_clouds,
            component_strategy=settings.weight_island_policy,
        )
        clouds_list.append(cloud)
        for code in island_resolution.warnings:
            weight_issues.append(
                ValidationIssue(
                    "WARNING", code, code.lower(), code, bone_names=(state.name,),
                )
            )
    clouds = tuple(clouds_list)
    weight_finished = time.perf_counter()
    cloud_by_name = {cloud.bone_name: cloud for cloud in clouds}
    tip_helpers = classify_tip_helpers(
        preflight.bone_states,
        clouds,
        preflight.issues,
        minimum_length_ratio=settings.minimum_length_ratio,
        maximum_length_ratio=settings.maximum_length_ratio,
    )
    required_reference_helper_names = {
        str(name) for name in required_reference_tip_helper_names
    }
    classified_helper_names = {item.bone_name for item in tip_helpers}
    missing_required_helper_names = tuple(sorted(
        required_reference_helper_names - classified_helper_names
    ))
    tip_usage_issues = [
        ValidationIssue(
            "BLOCKER", "BONEWEAVER_HIERARCHY_TIP_HELPER_IDENTITY_CHANGED",
            "boneweaver_hierarchy_tip_helper_identity_changed",
            "Frozen reference-only Tip Helper no longer satisfies classification",
            bone_names=(name,),
        )
        for name in missing_required_helper_names
    ]
    if tip_helper_usage == TipHelperUsage.INCLUDE_AS_PHYSICS_TERMINAL.value:
        if not visual_cleanup:
            tip_usage_issues.append(
                ValidationIssue(
                    "BLOCKER", "BONEWEAVER_TIP_HELPER_INCLUDE_PROFILE_REQUIRED",
                    "boneweaver_tip_helper_include_profile_required",
                    "Including Tip Helpers as mutation targets is restricted to Visual Chain Cleanup",
                    bone_names=tuple(item.bone_name for item in tip_helpers),
                )
            )
        else:
            included_helpers = []
            for classification in tip_helpers:
                if classification.excluded_child_names:
                    tip_usage_issues.append(
                        ValidationIssue(
                            "BLOCKER", "BONEWEAVER_TIP_HELPER_INCLUDE_UNSAFE",
                            "boneweaver_tip_helper_include_unsafe",
                            "Tip Helper has excluded children and must remain reference-only",
                            bone_names=(
                                classification.bone_name,
                                *classification.excluded_child_names,
                            ),
                        )
                    )
                    included_helpers.append(classification)
                else:
                    included_helpers.append(dataclasses.replace(
                        classification,
                        reference_only=False,
                        mutation_target=True,
                        requires_own_tail=True,
                    ))
            tip_helpers = tuple(included_helpers)
    allowed_external_helper_edges = {
        (classification.bone_name, child_name)
        for classification in tip_helpers
        for child_name in classification.excluded_child_names
    }
    effective_preflight_issues = tuple(
        issue
        for issue in preflight.issues
        if not (
            issue.code == "BONEWEAVER_EXTERNAL_CONNECTED_CHILD"
            and len(issue.bone_names) >= 2
            and (issue.bone_names[0], issue.bone_names[1])
            in allowed_external_helper_edges
        )
    )
    helper_names = {
        classification.bone_name for classification in tip_helpers
    }.union(missing_required_helper_names)
    reference_only_helper_names = {
        classification.bone_name
        for classification in tip_helpers
        if classification.reference_only
    }
    reference_only_helper_names.update(missing_required_helper_names)
    helper_parent_names = {classification.parent_bone_name for classification in tip_helpers}
    excluded_helper_child_names = {
        child_name
        for classification in tip_helpers
        for child_name in classification.excluded_child_names
    }
    graph = build_physics_graph(
        preflight.bone_states,
        tip_helpers=tip_helpers,
        helper_names=missing_required_helper_names,
    )
    branch_resolutions_list = []
    override_issues = []
    selected_bone_names = frozenset(preflight.selected_bone_names)
    deform_weight_mass = {
        cloud.bone_name: cloud.total_statistical_weight for cloud in clouds
    }
    weighted_vertex_count = {
        cloud.bone_name: cloud.sample_count for cloud in clouds
    }
    scoped_continuation_by_branch = dict(scoped_branch_continuations)
    for state in sorted(preflight.bone_states, key=lambda item: item.name):
        if sum(child in selected_bone_names for child in state.child_names) <= 1:
            continue
        branch_override, legacy = find_branch_override(
            settings.branch_overrides,
            armature_data_name=armature.data.name,
            armature_structural_fingerprint=structural_fingerprint,
            branch_bone_name=state.name,
        )
        if legacy:
            override_issues.append(
                ValidationIssue(
                    "WARNING", "BONEWEAVER_LEGACY_OVERRIDE_UNSCOPED",
                    "boneweaver_legacy_override_unscoped",
                    "Legacy branch override is unscoped and was not applied",
                    bone_names=(state.name,),
                )
            )
        selected_child_name = (
            branch_override.selected_child_name
            if branch_override
            else scoped_continuation_by_branch.get(state.name)
        )
        branch_resolutions_list.append(
            resolve_branch(
                state.name,
                preflight.bone_states,
                deform_weight_mass=deform_weight_mass,
                weighted_vertex_count=weighted_vertex_count,
                mode=(
                    "MANUAL_ONLY"
                    if visual_cleanup or selected_child_name is not None
                    else settings.branch_resolution_mode
                ),
                manual_selected_child=selected_child_name,
            )
        )
    branch_resolutions = tuple(branch_resolutions_list)
    graph = with_skipped_mutation_targets(
        graph,
        (
            resolution.branch_bone_name
            for resolution in branch_resolutions
            if resolution.result == "KEEP_ORIGINAL"
        ),
    )
    branch_by_name = {resolution.branch_bone_name: resolution for resolution in branch_resolutions}
    node_by_id = {node.node_id: node for node in graph.nodes}
    solutions = {}
    state_by_name = {state.name: state for state in preflight.bone_states}
    chain_id_by_bone = {
        bone_name: chain.chain_id
        for chain in graph.chains
        for bone_name in chain.real_bone_names
    }
    for classification in tip_helpers:
        parent = state_by_name[classification.parent_bone_name]
        helper = state_by_name[classification.bone_name]
        manual, legacy_terminal_override = (None, False) if visual_cleanup else _manual_solution(
            settings,
            parent,
            armature,
            chain_id=chain_id_by_bone.get(parent.name, ""),
            structural_fingerprint=structural_fingerprint,
        )
        if legacy_terminal_override:
            override_issues.append(
                ValidationIssue(
                    "WARNING", "BONEWEAVER_LEGACY_OVERRIDE_UNSCOPED",
                    "boneweaver_legacy_override_unscoped",
                    "Legacy terminal override is unscoped and was not applied",
                    bone_names=(parent.name,),
                )
            )
        solutions[parent.name] = manual or authoritative_solution(
            parent.name,
            parent.head,
            helper.head,
            source="EXISTING_TIP_HELPER_HEAD",
            kind="DIRECT_CHILD",
        )
        if manual is not None and manual.requires_confirmation:
            override_issues.append(
                ValidationIssue(
                    "BLOCKER", "BONEWEAVER_VIRTUAL_TIP_INVALID",
                    "boneweaver_virtual_tip_invalid",
                    "Invalid manual terminal override",
                    bone_names=(parent.name,),
                )
            )
        if (
            manual is not None
            and helper.use_connect
            and math.dist(tuple(manual.tail), tuple(helper.head)) > 1.0e-7
        ):
            override_issues.append(
                ValidationIssue(
                    "BLOCKER", "BONEWEAVER_MANUAL_OVERRIDE_CONNECTED_TIP_HELPER",
                    "boneweaver_manual_override_connected_tip_helper",
                    "Manual terminal override would move a connected reference-only Tip Helper",
                    bone_names=(parent.name, helper.name),
                )
            )
    issues = list(effective_preflight_issues) + weight_issues + override_issues + tip_usage_issues
    for resolution in branch_resolutions:
        if resolution.issue_codes:
            for code in resolution.issue_codes:
                issues.append(
                    ValidationIssue(
                        "BLOCKER", code, code.lower(),
                        _BRANCH_BLOCK_MESSAGES.get(code, code),
                        bone_names=(resolution.branch_bone_name,),
                        details=(("winner_score", str(resolution.score)), ("margin", str(resolution.margin))),
                    )
                )
        elif resolution.result == "MEDIUM":
            issues.append(
                ValidationIssue(
                    "WARNING", "BONEWEAVER_BRANCH_MEDIUM_CONFIDENCE", "boneweaver_branch_medium_confidence",
                    "Branch continuation selected with medium confidence",
                    bone_names=(resolution.branch_bone_name,),
                    details=(("selected_child", resolution.selected_child_name or ""), ("winner_score", str(resolution.score)), ("margin", str(resolution.margin))),
                )
            )
    for chain in graph.chains:
        leaf_name = chain.real_bone_names[-1]
        if leaf_name in reference_only_helper_names or leaf_name in excluded_helper_child_names:
            continue
        leaf_node = node_by_id[f"real:{leaf_name}"]
        if any(node_by_id[child].kind == "REAL_BONE" for child in leaf_node.child_node_ids):
            continue
        state = state_by_name[leaf_name]
        unresolved_branch = bool(
            chain.branch_parent_node_id
            and branch_by_name.get(
                chain.branch_parent_node_id.removeprefix("real:"), None,
            )
            and branch_by_name[
                chain.branch_parent_node_id.removeprefix("real:")
            ].selected_child_name is None
        )
        if visual_cleanup:
            cloud = cloud_by_name[leaf_name]
            fallback = safe_parent_chain_fallback(
                state,
                preflight.bone_states,
                unresolved_branch=unresolved_branch,
                reliable_weight_direction=cloud.principal_axis,
                reliable_weight_confidence=cloud.confidence,
                reliable_confidence_threshold=settings.minimum_confidence,
            )
            if fallback.resolution_class == "AUTO_SAFE_FALLBACK":
                solutions[leaf_name] = fallback
                issues.append(
                    ValidationIssue(
                        "WARNING", "BONEWEAVER_TERMINAL_SAFE_FALLBACK_USED",
                        "boneweaver_terminal_safe_fallback_used",
                        "Visual cleanup leaf resolved by safe parent-chain extrapolation",
                        bone_names=(leaf_name,),
                    )
                )
                continue
            manual, legacy_terminal_override = _manual_solution(
                settings, state, armature,
                chain_id=chain.chain_id,
                structural_fingerprint=structural_fingerprint,
            )
            if legacy_terminal_override:
                issues.append(
                    ValidationIssue(
                        "WARNING", "BONEWEAVER_LEGACY_OVERRIDE_UNSCOPED",
                        "boneweaver_legacy_override_unscoped",
                        "Legacy terminal override is unscoped and was not applied",
                        bone_names=(leaf_name,),
                    )
                )
            if manual is not None:
                solutions[leaf_name] = manual
                if manual.requires_confirmation:
                    issues.append(ValidationIssue(
                        "BLOCKER", "BONEWEAVER_VIRTUAL_TIP_INVALID",
                        "boneweaver_virtual_tip_invalid",
                        "Invalid manual terminal override",
                        bone_names=(leaf_name,),
                    ))
                continue
            solutions[leaf_name] = fallback
            for code in fallback.evidence:
                issues.append(ValidationIssue(
                    "BLOCKER", code, code.lower(), code,
                    bone_names=(leaf_name,),
                ))
            continue
        manual, legacy_terminal_override = _manual_solution(
            settings, state, armature,
            chain_id=chain.chain_id,
            structural_fingerprint=structural_fingerprint,
        )
        if legacy_terminal_override:
            issues.append(
                ValidationIssue(
                    "WARNING", "BONEWEAVER_LEGACY_OVERRIDE_UNSCOPED",
                    "boneweaver_legacy_override_unscoped",
                    "Legacy terminal override is unscoped and was not applied",
                    bone_names=(leaf_name,),
                )
            )
        if manual is not None:
            solutions[leaf_name] = manual
            if manual.requires_confirmation:
                issues.append(ValidationIssue("BLOCKER", "BONEWEAVER_VIRTUAL_TIP_INVALID", "boneweaver_virtual_tip_invalid", "Invalid manual terminal override", bone_names=(leaf_name,)))
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
            candidate_direction_merge_angle_degrees=settings.candidate_direction_merge_angle_degrees,
        )
        if solution.requires_confirmation and settings.terminal_mode in {
            "AUTO_HYBRID", "PARENT_EXTRAPOLATION_ONLY"
        }:
            cloud = cloud_by_name[leaf_name]
            fallback = safe_parent_chain_fallback(
                state,
                preflight.bone_states,
                unresolved_branch=bool(
                    unresolved_branch
                ),
                reliable_weight_direction=cloud.principal_axis,
                reliable_weight_confidence=cloud.confidence,
                reliable_confidence_threshold=settings.minimum_confidence,
            )
            if fallback.resolution_class == "AUTO_SAFE_FALLBACK":
                solution = fallback
                issues.append(
                    ValidationIssue(
                        "WARNING", "BONEWEAVER_TERMINAL_SAFE_FALLBACK_USED",
                        "boneweaver_terminal_safe_fallback_used",
                        "Low-confidence terminal resolved by safe parent-chain extrapolation",
                        bone_names=(leaf_name,),
                    )
                )
        solutions[leaf_name] = solution
        if solution.resolution_class == "UNRESOLVED":
            for code in solution.evidence:
                issues.append(ValidationIssue("BLOCKER", code, code.lower(), code, bone_names=(leaf_name,)))
    graph = with_virtual_tips(
        graph,
        {
            bone_name: solution
            for bone_name, solution in solutions.items()
            if bone_name not in helper_parent_names
        },
    )
    proposals = _roll_proposals(
        build_proposals(
            graph, preflight.bone_states, settings.physics_profile,
            branch_resolutions=branch_resolutions,
            terminal_solutions=tuple(solutions.values()),
        ),
        graph, preflight.bone_states, settings, armature,
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
    topology_ledger = build_topology_projection_ledger(
        preflight.bone_states, graph, proposals, branch_resolutions,
        mutation_record_count=0,
    )
    plan = ConversionPlan(
        "boneweaver.conversion_plan", SCHEMA_VERSION, ALGORITHM_VERSION, ADDON_VERSION, "",
        source, settings_hash, armature.name, armature.data.name, settings.physics_profile,
        CANDIDATE_SCORING_PROFILE, mesh_states, preflight.bone_states, graph, clouds,
        tuple(solutions[name] for name in sorted(solutions)), proposals, hints,
        issues_tuple, branch_resolutions, topology_ledger,
        tip_helpers=tip_helpers,
        tip_helper_usage=tip_helper_usage,
    )
    payload = dataclasses.asdict(plan)
    payload.pop("plan_id")
    result = dataclasses.replace(plan, plan_id=sha256(payload))
    finished = time.perf_counter()
    plan_serialized_size = len(repr(dataclasses.asdict(result)).encode("utf-8"))
    _LAST_BUILD_METRICS = {
        "bone_count": len(preflight.bone_states),
        "mesh_count": len(mesh_states),
        "vertex_count": scan_cache.vertex_count,
        "membership_count": scan_cache.membership_count,
        "vertex_pass_count": scan_cache.vertex_pass_count,
        "membership_pass_count": scan_cache.membership_pass_count,
        "mesh_scan_time": scan_cache.mesh_scan_time,
        "connectivity_time": weight_finished - weight_started,
        "analyze_time": finished - started,
        "fingerprint_time": fingerprint_finished - fingerprint_started,
        "weight_cloud_time": weight_finished - weight_started,
        "peak_temporary_point_count": max(
            (len(item.indices) for inputs in scan_cache.per_mesh_inputs_by_bone.values() for item in inputs),
            default=0,
        ),
        "peak_temporary_memory": scan_cache.peak_temporary_memory,
        "plan_serialized_size": plan_serialized_size,
        "validation_time": 0.0,
    }
    return result
