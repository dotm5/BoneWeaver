"""Build an immutable joint-head physics graph independent of imported tails."""

from __future__ import annotations

import math

from mathutils import Matrix

from .canonical import sha256
from .models import BoneState, PhysicsChain, PhysicsEdge, PhysicsGraph, PhysicsNode


def _node_id(name: str) -> str:
    return f"real:{name}"


def _edge_id(parent: str, child: str) -> str:
    return f"hierarchy:{parent}->{child}"


def _sub(a, b):
    return tuple(float(a[index] - b[index]) for index in range(3))


def _length(vector):
    return math.sqrt(sum(component * component for component in vector))


def _rotation(state: BoneState):
    matrix = Matrix(tuple(state.matrix_local[index : index + 4] for index in range(0, 16, 4)))
    quaternion = matrix.to_quaternion().normalized()
    return tuple(float(value) for value in quaternion)


def build_physics_graph(bone_states: tuple[BoneState, ...], epsilon: float = 1.0e-7) -> PhysicsGraph:
    by_name = {state.name: state for state in bone_states}
    names = tuple(sorted(by_name))
    children = {
        name: tuple(sorted(child for child in by_name[name].child_names if child in by_name))
        for name in names
    }
    root_names = (
        name
        for name in names
        if by_name[name].parent_name not in by_name
        or len(children[by_name[name].parent_name]) != 1
    )
    def depth(name):
        value = 0
        parent = by_name[name].parent_name
        while parent in by_name:
            value += 1
            parent = by_name[parent].parent_name
        return value

    roots = tuple(sorted(root_names, key=lambda name: (depth(name), name)))
    root_set = set(roots)
    issues = set()
    if any(len(children[name]) > 1 for name in names):
        issues.add("UECP_BRANCH_AMBIGUOUS")

    edges = []
    valid_edge_ids = set()
    for parent_name in names:
        parent = by_name[parent_name]
        for child_name in children[parent_name]:
            child = by_name[child_name]
            vector = _sub(child.head, parent.head)
            length = _length(vector)
            if not math.isfinite(length) or length <= epsilon:
                issues.add("UECP_COINCIDENT_HELPER")
                continue
            edge_id = _edge_id(parent_name, child_name)
            valid_edge_ids.add(edge_id)
            edges.append(
                PhysicsEdge(edge_id, "HIERARCHY_SEGMENT", _node_id(parent_name), _node_id(child_name), vector, length, "JOINT_HEAD_HIERARCHY")
            )

    nodes = tuple(
        PhysicsNode(
            node_id=_node_id(name), kind="REAL_BONE", bone_name=name,
            joint_position=tuple(float(value) for value in by_name[name].head),
            rest_rotation=_rotation(by_name[name]), local_x=by_name[name].local_x,
            local_y=by_name[name].local_y, local_z=by_name[name].local_z,
            parent_node_id=_node_id(by_name[name].parent_name) if by_name[name].parent_name in by_name else None,
            child_node_ids=tuple(_node_id(child) for child in children[name]),
            is_kinematic=name in root_set, source="BONE_HEAD",
        )
        for name in names
    )

    chains = []
    for root in roots:
        chain_names = [root]
        edge_ids = []
        current = root
        while len(children[current]) == 1:
            child = children[current][0]
            edge_id = _edge_id(current, child)
            if edge_id not in valid_edge_ids:
                break
            edge_ids.append(edge_id)
            chain_names.append(child)
            current = child
        parent_name = by_name[root].parent_name
        branch_parent = parent_name if parent_name in by_name and len(children[parent_name]) > 1 else None
        chain_payload = (tuple(chain_names), tuple(edge_ids), branch_parent)
        chains.append(
            PhysicsChain(
                chain_id=sha256(chain_payload), node_ids=tuple(_node_id(name) for name in chain_names),
                edge_ids=tuple(edge_ids), real_bone_names=tuple(chain_names), root_node_id=_node_id(root),
                terminal_node_id=_node_id(chain_names[-1]), has_virtual_tip=False,
                branch_parent_node_id=_node_id(branch_parent) if branch_parent else None,
                resolved=False, issue_codes=("UECP_BRANCH_AMBIGUOUS",) if branch_parent else (),
            )
        )

    edges_tuple = tuple(sorted(edges, key=lambda edge: edge.edge_id))
    chains_tuple = tuple(chains)
    issue_codes = tuple(sorted(issues))
    payload = {"nodes": nodes, "edges": edges_tuple, "chains": chains_tuple, "issues": issue_codes}
    graph_id = sha256(payload)
    return PhysicsGraph(graph_id, tuple(node.node_id for node in nodes), tuple(edge.edge_id for edge in edges_tuple), nodes, edges_tuple, chains_tuple, issue_codes)


def with_virtual_tips(graph: PhysicsGraph, solutions) -> PhysicsGraph:
    nodes = list(graph.nodes)
    edges = list(graph.edges)
    chains = list(graph.chains)
    node_index = {node.node_id: index for index, node in enumerate(nodes)}
    for bone_name, solution in sorted(solutions.items()):
        if solution.requires_confirmation or not solution.selected_candidate_id:
            continue
        real_id = _node_id(bone_name)
        if real_id not in node_index:
            continue
        virtual_id = f"virtual:{bone_name}:{solution.selected_candidate_id}"
        edge_id = f"virtual-tip:{bone_name}:{solution.selected_candidate_id}"
        parent = nodes[node_index[real_id]]
        virtual = PhysicsNode(virtual_id, "VIRTUAL_TIP", None, solution.tail, None, None, None, None, real_id, (), False, solution.source)
        nodes[node_index[real_id]] = PhysicsNode(
            parent.node_id, parent.kind, parent.bone_name, parent.joint_position, parent.rest_rotation,
            parent.local_x, parent.local_y, parent.local_z, parent.parent_node_id,
            tuple(sorted(parent.child_node_ids + (virtual_id,))), parent.is_kinematic, parent.source,
        )
        node_index[virtual_id] = len(nodes)
        nodes.append(virtual)
        vector = _sub(solution.tail, parent.joint_position)
        edges.append(PhysicsEdge(edge_id, "VIRTUAL_TIP_SEGMENT", real_id, virtual_id, vector, _length(vector), solution.source))
        for index, chain in enumerate(chains):
            if chain.terminal_node_id == real_id:
                chains[index] = PhysicsChain(
                    chain.chain_id, chain.node_ids + (virtual_id,), chain.edge_ids + (edge_id,),
                    chain.real_bone_names, chain.root_node_id, virtual_id, True,
                    chain.branch_parent_node_id, True, chain.issue_codes,
                )
                break
    nodes_tuple = tuple(sorted(nodes, key=lambda node: node.node_id))
    edges_tuple = tuple(sorted(edges, key=lambda edge: edge.edge_id))
    chains_tuple = tuple(chains)
    payload = {"nodes": nodes_tuple, "edges": edges_tuple, "chains": chains_tuple, "issues": graph.issue_codes}
    graph_id = sha256(payload)
    return PhysicsGraph(graph_id, tuple(node.node_id for node in nodes_tuple), tuple(edge.edge_id for edge in edges_tuple), nodes_tuple, edges_tuple, chains_tuple, graph.issue_codes)
