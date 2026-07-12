from __future__ import annotations

import dataclasses
import unittest

from boneweaver.core.models import BoneState
from boneweaver.core.physics_graph import build_physics_graph


def state(name, parent, children, head, tail=(99.0, 99.0, 99.0)):
    return BoneState(
        name=name, parent_name=parent, child_names=tuple(children), head=tuple(head), tail=tuple(tail),
        roll=0.0, matrix_local=tuple(float(i % 5 == 0) for i in range(16)),
        local_x=(1.0, 0.0, 0.0), local_y=(0.0, 1.0, 0.0), local_z=(0.0, 0.0, 1.0),
        use_connect=False, use_deform=True, inherit_scale="FULL", use_inherit_rotation=True,
        bbone_segments=1, is_socket=False, importer_metadata_flags=(),
    )


class PhysicsGraphTests(unittest.TestCase):
    def test_hierarchy_edges_use_heads_and_ignore_imported_tails(self) -> None:
        bones = (
            state("B0", None, ("B1",), (0, 0, 0), tail=(100, 0, 0)),
            state("B1", "B0", ("B2",), (0, 1, 0), tail=(-100, 0, 0)),
            state("B2", "B1", (), (0, 2, 0), tail=(0, 0, 100)),
        )
        graph = build_physics_graph(bones, epsilon=1.0e-7)
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual([edge.rest_vector for edge in graph.edges], [(0.0, 1.0, 0.0), (0.0, 1.0, 0.0)])
        self.assertEqual([edge.rest_length for edge in graph.edges], [1.0, 1.0])
        self.assertTrue(graph.nodes[0].is_kinematic)
        self.assertFalse(graph.nodes[1].is_kinematic)

    def test_graph_id_is_independent_of_input_and_tail_order_noise(self) -> None:
        bones = (
            state("B0", None, ("B1",), (0, 0, 0)),
            state("B1", "B0", (), (0, 1, 0)),
        )
        first = build_physics_graph(bones)
        noisy = tuple(dataclasses.replace(bone, tail=(7.0, 8.0, 9.0)) for bone in reversed(bones))
        second = build_physics_graph(noisy)
        self.assertEqual(first.graph_id, second.graph_id)
        self.assertEqual(first, second)

    def test_branch_edges_are_preserved_without_averaging(self) -> None:
        bones = (
            state("Root", None, ("Left", "Right"), (0, 0, 0)),
            state("Left", "Root", (), (-1, 1, 0)),
            state("Right", "Root", (), (1, 1, 0)),
        )
        graph = build_physics_graph(bones)
        self.assertEqual(len(graph.edges), 2)
        self.assertEqual({edge.rest_vector for edge in graph.edges}, {(-1.0, 1.0, 0.0), (1.0, 1.0, 0.0)})
        self.assertEqual([chain.real_bone_names for chain in graph.chains], [("Root",), ("Left",), ("Right",)])
        self.assertIn("BONEWEAVER_BRANCH_AMBIGUOUS", graph.issue_codes)
        self.assertTrue(all(chain.node_ids for chain in graph.chains))

    def test_coincident_edge_is_blocked_and_not_emitted(self) -> None:
        bones = (
            state("Root", None, ("Helper",), (0, 0, 0)),
            state("Helper", "Root", (), (0, 0, 0)),
        )
        graph = build_physics_graph(bones)
        self.assertEqual(graph.edges, ())
        self.assertIn("BONEWEAVER_COINCIDENT_HELPER", graph.issue_codes)


if __name__ == "__main__":
    unittest.main()
