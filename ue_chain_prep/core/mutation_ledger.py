"""Field-level mutation and selected-topology accounting."""

from __future__ import annotations

import dataclasses

from .models import BoneMutationRecord, TopologyProjectionLedger


def _tuple3(value):
    return tuple(float(component) for component in value)


def _changed(first, second, epsilon=1.0e-12):
    if isinstance(first, (tuple, list)):
        return any(abs(float(a) - float(b)) > epsilon for a, b in zip(first, second))
    if isinstance(first, bool):
        return bool(first) != bool(second)
    return abs(float(first) - float(second)) > epsilon


def build_mutation_records(plan, before_states, after_states):
    records = []
    for proposal in sorted(plan.proposals, key=lambda item: item.bone_name):
        before = before_states.get(proposal.bone_name)
        after = after_states.get(proposal.bone_name)
        if before is None or after is None:
            continue
        tail_changed = _changed(before["tail"], after["tail"])
        roll_changed = _changed(before["roll"], after["roll"])
        connect_changed = _changed(before["use_connect"], after["use_connect"])
        if not (tail_changed or roll_changed or connect_changed):
            continue
        reasons = []
        if tail_changed:
            reasons.append("TAIL_PROJECTED")
        if roll_changed:
            reasons.append("ROLL_ALIGNED")
        if connect_changed:
            reasons.append("CONNECT_PROFILE_CHANGED")
        if proposal.role == "BRANCH_CONTINUATION":
            reasons.append("BRANCH_CONTINUATION")
        if proposal.role == "BRANCH_SIDE_ROOT":
            reasons.append("BRANCH_SIDE_ROOT")
        records.append(
            BoneMutationRecord(
                proposal.bone_name,
                proposal.proposal_id,
                proposal.chain_id,
                proposal.role,
                tail_changed,
                roll_changed,
                connect_changed,
                _tuple3(before["tail"]),
                _tuple3(after["tail"]),
                float(before["roll"]),
                float(after["roll"]),
                bool(before["use_connect"]),
                bool(after["use_connect"]),
                tuple(reasons),
            )
        )
    return tuple(records)


def validate_mutation_records(plan, before_states, after_states, records):
    issues = set()
    proposals = {proposal.proposal_id: proposal for proposal in plan.proposals}
    for record in records:
        proposal = proposals.get(record.proposal_id)
        if proposal is None or proposal.bone_name != record.bone_name:
            issues.add("UECP_MUTATION_WITHOUT_PROPOSAL")
    expected = build_mutation_records(plan, before_states, after_states)
    if tuple(records) != expected:
        issues.add("UECP_UNRECORDED_BONE_MUTATION")
    return tuple(sorted(issues))


def build_topology_projection_ledger(
    bone_states,
    graph,
    proposals,
    branch_resolutions,
    *,
    mutation_record_count,
):
    selected_names = {state.name for state in bone_states}
    hierarchy_edges = tuple(edge for edge in graph.edges if edge.kind == "HIERARCHY_SEGMENT")
    counts = {}
    for edge in hierarchy_edges:
        counts[edge.parent_node_id] = counts.get(edge.parent_node_id, 0) + 1
    branch_nodes = {node_id for node_id, count in counts.items() if count > 1}
    branch_edges = sum(counts[node_id] for node_id in branch_nodes)
    linear_edges = len(hierarchy_edges) - branch_edges
    resolved = sum(resolution.selected_child_name is not None for resolution in branch_resolutions)
    unresolved = sum(resolution.selected_child_name is None and resolution.result != "KEEP_ORIGINAL" for resolution in branch_resolutions)
    external_edges = sum(
        child_name not in selected_names
        for state in bone_states
        for child_name in state.child_names
    )
    proposed_names = {proposal.bone_name for proposal in proposals}
    return TopologyProjectionLedger(
        selected_bone_count=len(selected_names),
        selected_hierarchy_edge_count=len(hierarchy_edges),
        linear_edge_count=linear_edges,
        branch_node_count=len(branch_nodes),
        branch_edge_count=branch_edges,
        resolved_branch_count=resolved,
        unresolved_branch_count=unresolved,
        external_child_edge_count=external_edges,
        virtual_tip_count=sum(node.kind == "VIRTUAL_TIP" for node in graph.nodes),
        proposal_count=len(proposals),
        mutation_record_count=int(mutation_record_count),
        skipped_by_design_count=len(selected_names - proposed_names),
    )


def with_mutation_count(ledger, count):
    return dataclasses.replace(ledger, mutation_record_count=int(count))
