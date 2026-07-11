"""Post-apply invariant, digest, projection, and neutral-mesh validation."""

from __future__ import annotations

from dataclasses import dataclass

import bpy
from mathutils import Vector

from .fingerprint import base_mesh_digest, modifier_digest, weight_digest


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


def capture_neutral_meshes(plan):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    captured = {}
    for state in plan.mesh_states:
        obj = bpy.data.objects[state.object_name]
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            captured[obj.name] = tuple(tuple(float(value) for value in (evaluated.matrix_world @ vertex.co)) for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    return captured


def capture_armature_state(armature):
    return {
        bone.name: {
            "parent": bone.parent.name if bone.parent else None,
            "head": tuple(float(value) for value in bone.head_local),
            "tail": tuple(float(value) for value in bone.tail_local),
            "use_connect": bool(bone.use_connect),
            "use_deform": bool(bone.use_deform),
            "inherit_scale": str(bone.inherit_scale),
            "use_inherit_rotation": bool(bone.use_inherit_rotation),
        }
        for bone in armature.data.bones
    }


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
        if edge is None or tuple(proposal.proposed_tail) != tuple(nodes[edge.child_node_id].joint_position):
            issues.append("UECP_GRAPH_PROJECTION_MISMATCH")
            continue
        bone = armature.data.bones[proposal.bone_name]
        expected = Vector(nodes[edge.child_node_id].joint_position)
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
        if weight_digest(mesh) != state.vertex_group_digest:
            weight_changes += 1
            issues.append("UECP_WEIGHT_DIGEST_CHANGED")
        if base_mesh_digest(mesh) != state.base_mesh_digest:
            base_changes += 1
            issues.append("UECP_BASE_MESH_CHANGED")
        if modifier_digest(mesh) != state.modifier_digest:
            modifier_changes += 1
            issues.append("UECP_MODIFIER_DIGEST_CHANGED")
    current = capture_neutral_meshes(plan)
    max_neutral = 0.0
    for name, before in neutral_baseline.items():
        after = current.get(name, ())
        if len(before) != len(after):
            issues.append("UECP_NEUTRAL_MESH_CHANGED")
            max_neutral = float("inf")
            continue
        for first, second in zip(before, after):
            max_neutral = max(max_neutral, (Vector(first) - Vector(second)).length)
    scene_scale = max(
        1.0,
        float(armature.dimensions.length),
        *(float(bpy.data.objects[state.object_name].dimensions.length) for state in plan.mesh_states),
    )
    settings = getattr(context.scene, "uecp_settings", None)
    epsilon_factor = settings.position_epsilon_factor if settings else 1.0e-7
    allowed_neutral = max(1.0e-7, scene_scale * epsilon_factor)
    if max_neutral > allowed_neutral:
        issues.append("UECP_NEUTRAL_MESH_CHANGED")
    unique = tuple(sorted(set(issues)))
    return PostValidationReport(not unique, unique, weight_changes, base_changes, modifier_changes, non_target_changes, max_projection, max_neutral, scene_scale, allowed_neutral, tuple(non_target_names))
