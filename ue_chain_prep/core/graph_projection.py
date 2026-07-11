"""Project unique PhysicsGraph edges into immutable Blender Bone proposals."""

from __future__ import annotations

from .models import BoneProposal


def build_proposals(graph, bone_states, profile):
    states = {state.name: state for state in bone_states}
    nodes = {node.node_id: node for node in graph.nodes}
    chain_for_bone = {}
    root_bones = set()
    for chain in graph.chains:
        root_bones.add(chain.real_bone_names[0])
        for name in chain.real_bone_names:
            chain_for_bone[name] = chain
    hierarchy_counts = {}
    for edge in graph.edges:
        if edge.kind == "HIERARCHY_SEGMENT":
            hierarchy_counts[edge.parent_node_id] = hierarchy_counts.get(edge.parent_node_id, 0) + 1
    proposals = []
    for edge in graph.edges:
        parent = nodes[edge.parent_node_id]
        child = nodes[edge.child_node_id]
        if parent.kind != "REAL_BONE" or hierarchy_counts.get(parent.node_id, 0) > 1:
            continue
        state = states[parent.bone_name]
        chain = chain_for_bone[parent.bone_name]
        if profile in {"BONEX_ROTATION_CHAIN", "WIGGLE2_ROTATION_CHAIN"}:
            connect = parent.bone_name not in root_bones
        elif profile in {"BONEX_TRANSLATION_ALLOWED", "WIGGLE2_STRETCH_CHAIN"}:
            connect = False
        else:
            connect = state.use_connect
        role = "LEAF" if edge.kind == "VIRTUAL_TIP_SEGMENT" else ("ANCHOR" if parent.bone_name in root_bones else "DYNAMIC")
        proposals.append(
            BoneProposal(
                parent.bone_name, chain.chain_id, edge.edge_id, role, state.head, state.tail,
                state.roll, child.joint_position, state.local_z, connect,
                child.source if edge.kind == "VIRTUAL_TIP_SEGMENT" else "UNIQUE_DIRECT_CHILD_HEAD",
                1.0, (),
            )
        )
    chain_order = {name: index for chain in graph.chains for index, name in enumerate(chain.real_bone_names)}
    return tuple(sorted(proposals, key=lambda proposal: (chain_order.get(proposal.bone_name, 0), proposal.bone_name)))
