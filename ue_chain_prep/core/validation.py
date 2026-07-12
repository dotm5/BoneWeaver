"""Post-apply invariant, digest, projection, and neutral-mesh validation."""

from __future__ import annotations

from dataclasses import dataclass
from array import array

import bpy
from mathutils import Vector

from .fingerprint import base_mesh_digest, modifier_digest, weight_digest
from .canonical import sha256
from .mesh_scan_cache import mesh_digest_pair
from .validation_tolerance import MeshCoordinateCapture, MeshValidationResult, coordinate_delta_metrics, evaluate_mesh_tolerance


@dataclass(frozen=True, slots=True)
class NeutralMeshBaseline:
    capture: MeshCoordinateCapture
    baseline_max_delta: float
    baseline_rms_delta: float


@dataclass(frozen=True, slots=True)
class PostValidationReport:
    success: bool
    issues: tuple[str, ...]
    weight_digest_changes: int
    base_mesh_digest_changes: int
    modifier_digest_changes: int
    non_target_bone_changes: int
    maximum_projection_error: float
    maximum_neutral_mesh_delta: float
    scene_scale: float
    allowed_neutral_mesh_delta: float
    non_target_bone_names: tuple[str, ...]
    mesh_validation_results: tuple[MeshValidationResult, ...]
    numeric_noise_mesh_names: tuple[str, ...]


def _capture_neutral_meshes_once(plan):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    captured = {}
    for state in plan.mesh_states:
        obj = bpy.data.objects[state.object_name]
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            local = array("d")
            world = array("d")
            for vertex in mesh.vertices:
                local.extend(float(value) for value in vertex.co)
                world.extend(float(value) for value in (evaluated.matrix_world @ vertex.co))
            captured[obj.name] = MeshCoordinateCapture(obj.name, local, world)
        finally:
            evaluated.to_mesh_clear()
    return captured


def _capture_delta_metrics(first, second):
    maximum, _mean, rms, _soft_count, _hard_count = coordinate_delta_metrics(
        first.local_coordinates, second.local_coordinates,
    )
    return maximum, rms


def capture_neutral_meshes(plan):
    """Capture twice around a dependency-graph update to measure no-op noise."""
    first = _capture_neutral_meshes_once(plan)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    second = _capture_neutral_meshes_once(plan)
    result = {}
    for name, capture in second.items():
        maximum, rms = _capture_delta_metrics(first[name], capture)
        result[name] = NeutralMeshBaseline(capture, maximum, rms)
    return result


def capture_armature_state(armature):
    return {
        bone.name: {
            "parent": bone.parent.name if bone.parent else None,
            "head": tuple(float(value) for value in bone.head_local),
            "tail": tuple(float(value) for value in bone.tail_local),
            "roll": float(bone.AxisRollFromMatrix(bone.matrix_local.to_3x3())[1]),
            "use_connect": bool(bone.use_connect),
            "use_deform": bool(bone.use_deform),
            "inherit_scale": str(bone.inherit_scale),
            "use_inherit_rotation": bool(bone.use_inherit_rotation),
        }
        for bone in armature.data.bones
    }


def armature_state_digest(armature, epsilon=1.0e-6):
    """Hash whole-armature rest state with reopen-safe float quantization."""

    state = capture_armature_state(armature)
    quantize = lambda value: int(round(float(value) / epsilon))
    payload = tuple(
        (
            name,
            values["parent"],
            tuple(quantize(value) for value in values["head"]),
            tuple(quantize(value) for value in values["tail"]),
            quantize(values["roll"]),
            values["use_connect"],
            values["use_deform"],
            values["inherit_scale"],
            values["use_inherit_rotation"],
        )
        for name, values in sorted(state.items())
    )
    return sha256(payload)


def armature_state_matches(armature, expected_state, epsilon=1.0e-6):
    """Tolerance-aware whole-armature comparison for save/reopen gates."""

    current = capture_armature_state(armature)
    if set(current) != set(expected_state):
        return False
    for name, actual in current.items():
        expected = expected_state[name]
        if any(
            actual[field] != expected.get(field)
            for field in (
                "parent", "use_connect", "use_deform", "inherit_scale",
                "use_inherit_rotation",
            )
        ):
            return False
        for field in ("head", "tail"):
            expected_vector = expected.get(field, ())
            if len(expected_vector) != 3 or any(
                abs(float(a) - float(b)) > epsilon
                for a, b in zip(actual[field], expected_vector)
            ):
                return False
        if abs(float(actual["roll"]) - float(expected.get("roll", actual["roll"]))) > epsilon:
            return False
    return True


def validate_post_apply(context, plan, neutral_baseline, armature_baseline=None):
    issues = []
    weight_changes = base_changes = modifier_changes = 0
    max_projection = 0.0
    nodes = {node.node_id: node for node in plan.physics_graph.nodes}
    edges = {edge.edge_id: edge for edge in plan.physics_graph.edges}
    armature = bpy.data.objects[plan.armature_object_name]
    non_target_changes = 0
    non_target_names = []
    if armature_baseline is not None:
        current_armature = capture_armature_state(armature)
        target_names = {proposal.bone_name for proposal in plan.proposals}
        for name, before in armature_baseline.items():
            after = current_armature.get(name)
            if after is None:
                non_target_changes += 1
                non_target_names.append(name + ":missing")
                continue
            if name not in target_names and after != before:
                non_target_changes += 1
                changed_fields = ",".join(key for key in before if after.get(key) != before[key])
                non_target_names.append(name + ":" + changed_fields)
            if name in target_names:
                for invariant in ("parent", "head", "use_deform", "inherit_scale", "use_inherit_rotation"):
                    if after[invariant] != before[invariant]:
                        non_target_changes += 1
                        break
        if non_target_changes:
            issues.append("UECP_NON_TARGET_BONE_CHANGED")
    for proposal in plan.proposals:
        edge = edges.get(proposal.source_edge_id)
        if edge is None:
            issues.append("UECP_GRAPH_PROJECTION_MISMATCH")
            continue
        graph_tail = tuple(nodes[edge.child_node_id].joint_position)
        if (
            proposal.terminal_source != "MANUAL_OVERRIDE"
            and tuple(proposal.proposed_tail) != graph_tail
        ):
            issues.append("UECP_GRAPH_PROJECTION_MISMATCH")
            continue
        bone = armature.data.bones[proposal.bone_name]
        expected = Vector(proposal.proposed_tail)
        error = (bone.tail_local - expected).length
        max_projection = max(max_projection, error)
        if error > 1.0e-6:
            issues.append("UECP_GRAPH_PROJECTION_MISMATCH")
    for state in plan.mesh_states:
        mesh = bpy.data.objects.get(state.object_name)
        if mesh is None:
            issues.append("UECP_BASE_MESH_CHANGED")
            base_changes += 1
            continue
        current_weight_digest, current_base_mesh_digest = mesh_digest_pair(mesh)
        if current_weight_digest != state.vertex_group_digest:
            weight_changes += 1
            issues.append("UECP_WEIGHT_DIGEST_CHANGED")
        if current_base_mesh_digest != state.base_mesh_digest:
            base_changes += 1
            issues.append("UECP_BASE_MESH_CHANGED")
        if modifier_digest(mesh) != state.modifier_digest:
            modifier_changes += 1
            issues.append("UECP_MODIFIER_DIGEST_CHANGED")
    current = _capture_neutral_meshes_once(plan)
    settings = getattr(context.scene, "uecp_settings", None)
    tolerance_mode = settings.validation_tolerance_mode if settings else "AUTO_PRODUCTION"
    epsilon_factor = settings.position_epsilon_factor if settings else 1.0e-7
    mesh_results = []
    for name, baseline in neutral_baseline.items():
        after = current.get(name)
        if after is None:
            issues.append("UECP_NEUTRAL_MESH_CHANGED")
            continue
        if isinstance(baseline, NeutralMeshBaseline):
            before_capture = baseline.capture
            baseline_max = baseline.baseline_max_delta
            baseline_rms = baseline.baseline_rms_delta
        else:
            # Safe compatibility for callers holding captures from pre-hardening builds.
            before_capture = baseline
            baseline_max = baseline_rms = 0.0
        mesh_results.append(
            evaluate_mesh_tolerance(
                before_capture,
                after,
                mode=tolerance_mode,
                custom_relative_factor=epsilon_factor,
                baseline_max_delta=baseline_max,
                baseline_rms_delta=baseline_rms,
            )
        )
    failed_meshes = tuple(result.mesh_name for result in mesh_results if result.result == "FAIL_AND_ROLLBACK")
    if failed_meshes:
        issues.append("UECP_NEUTRAL_MESH_CHANGED")
    max_neutral = max((result.max_delta for result in mesh_results), default=0.0)
    scene_scale = max((result.mesh_scale for result in mesh_results), default=1.0)
    allowed_neutral = max((result.soft_limit for result in mesh_results), default=1.0e-7)
    noise_meshes = tuple(
        result.mesh_name for result in mesh_results
        if result.result == "PASS_WITH_NUMERIC_NOISE_WARNING"
    )
    unique = tuple(sorted(set(issues)))
    return PostValidationReport(
        not unique, unique, weight_changes, base_changes, modifier_changes,
        non_target_changes, max_projection, max_neutral, scene_scale,
        allowed_neutral, tuple(non_target_names), tuple(mesh_results), noise_meshes,
    )
