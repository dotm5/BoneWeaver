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


def validate_post_apply(context, plan, neutral_baseline):
    issues = []
    weight_changes = base_changes = modifier_changes = 0
    max_projection = 0.0
    nodes = {node.node_id: node for node in plan.physics_graph.nodes}
    edges = {edge.edge_id: edge for edge in plan.physics_graph.edges}
    armature = bpy.data.objects[plan.armature_object_name]
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
    if max_neutral > 1.0e-7:
        issues.append("UECP_NEUTRAL_MESH_CHANGED")
    unique = tuple(sorted(set(issues)))
    return PostValidationReport(not unique, unique, weight_changes, base_changes, modifier_changes, 0, max_projection, max_neutral)
