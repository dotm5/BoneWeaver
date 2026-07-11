"""Project unique PhysicsGraph edges into immutable Blender Bone proposals."""

from __future__ import annotations

import dataclasses

from .canonical import sha256
from .models import BoneProposal


def build_proposals(graph, bone_states, profile, *, branch_resolutions=()):
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
    resolved_by_branch = {
        resolution.branch_bone_name: resolution
        for resolution in branch_resolutions
        if resolution.selected_child_name
    }
    main_children = {resolution.selected_child_name for resolution in resolved_by_branch.values()}
    side_children = {
        child_name
        for resolution in resolved_by_branch.values()
        for child_name in resolution.side_child_names
    }
    proposals = []
    for edge in graph.edges:
        parent = nodes[edge.parent_node_id]
        child = nodes[edge.child_node_id]
        if parent.kind != "REAL_BONE":
            continue
        resolution = resolved_by_branch.get(parent.bone_name)
        if hierarchy_counts.get(parent.node_id, 0) > 1:
            if resolution is None or child.bone_name != resolution.selected_child_name:
                continue
        state = states[parent.bone_name]
        chain = chain_for_bone[parent.bone_name]
        if profile in {"BONEX_ROTATION_CHAIN", "WIGGLE2_ROTATION_CHAIN"}:
            connect = parent.bone_name not in root_bones or parent.bone_name in main_children
        elif profile in {"BONEX_TRANSLATION_ALLOWED", "WIGGLE2_STRETCH_CHAIN"}:
            connect = False
        else:
            connect = state.use_connect
        if resolution is not None:
            role = "BRANCH_CONTINUATION"
        elif parent.bone_name in side_children:
            role = "BRANCH_SIDE_ROOT"
            connect = False
        else:
            role = "LEAF" if edge.kind == "VIRTUAL_TIP_SEGMENT" else ("ANCHOR" if parent.bone_name in root_bones else "DYNAMIC")
        proposals.append(
            BoneProposal(
                parent.bone_name, chain.chain_id, edge.edge_id, role, state.head, state.tail,
                state.roll, child.joint_position, state.local_z, connect,
                child.source if edge.kind == "VIRTUAL_TIP_SEGMENT" else "UNIQUE_DIRECT_CHILD_HEAD",
                resolution.score if resolution is not None else 1.0, (),
            )
        )
    proposals = [
        dataclasses.replace(
            proposal,
            proposal_id=sha256(
                (
                    proposal.bone_name, proposal.chain_id, proposal.source_edge_id,
                    proposal.role, proposal.proposed_tail,
                    proposal.proposed_roll_reference_z, proposal.final_use_connect,
                    proposal.terminal_source,
                )
            ),
        )
        for proposal in proposals
    ]
    chain_order = {name: index for chain in graph.chains for index, name in enumerate(chain.real_bone_names)}
    return tuple(sorted(proposals, key=lambda proposal: (chain_order.get(proposal.bone_name, 0), proposal.bone_name)))
