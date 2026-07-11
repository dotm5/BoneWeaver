from __future__ import annotations

import unittest

from tests.test_physics_graph import state
from ue_chain_prep.core.graph_projection import build_proposals
from ue_chain_prep.core.physics_graph import build_physics_graph, with_virtual_tips
from ue_chain_prep.core.terminal_candidates import generate_candidates, select_candidate
from ue_chain_prep.core.weight_cloud import analyze_weight_cloud


class GraphProjectionTests(unittest.TestCase):
    def test_virtual_tip_is_graph_only_and_projects_leaf_tail(self) -> None:
        bones = (
            state("B0", None, ("B1",), (0,0,0)),
            state("B1", "B0", ("B2",), (0,1,0)),
            state("B2", "B1", (), (0,2,0), tail=(0,2.2,0)),
        )
        base = build_physics_graph(bones)
        cloud = analyze_weight_cloud("B2", (0,2,0), tuple(((0,float(i),0),1.0) for i in range(3,8)))
        solution = select_candidate("B2", generate_candidates(bones[-1], cloud, parent_direction=(0,1,0), reference_length=1.0), minimum_score=0.5, minimum_margin=0.01)
        graph = with_virtual_tips(base, {"B2": solution})
        virtual = [node for node in graph.nodes if node.kind == "VIRTUAL_TIP"]
        self.assertEqual(len(virtual), 1)
        self.assertIsNone(virtual[0].bone_name)
        proposals = build_proposals(graph, bones, "BONEX_ROTATION_CHAIN")
        self.assertEqual([proposal.bone_name for proposal in proposals], ["B0", "B1", "B2"])
        self.assertEqual(proposals[0].proposed_tail, (0.0, 1.0, 0.0))
        self.assertEqual(proposals[-1].proposed_tail, virtual[0].joint_position)
        self.assertEqual([proposal.final_use_connect for proposal in proposals], [False, True, True])

    def test_branch_boundary_is_not_projected_to_either_child(self) -> None:
        bones = (
            state("Root", None, ("Left", "Right"), (0,0,0)),
            state("Left", "Root", (), (-1,1,0)),
            state("Right", "Root", (), (1,1,0)),
        )
        graph = build_physics_graph(bones)
        proposals = build_proposals(graph, bones, "GEOMETRY_ONLY")
        self.assertNotIn("Root", {proposal.bone_name for proposal in proposals})

    def test_stretch_profile_keeps_geometry_but_disconnects(self) -> None:
        bones = (state("B0", None, ("B1",), (0,0,0)), state("B1", "B0", (), (0,1,0)))
        proposals = build_proposals(build_physics_graph(bones), bones, "WIGGLE2_STRETCH_CHAIN")
        self.assertEqual(len(proposals), 1)
        self.assertFalse(proposals[0].final_use_connect)


if __name__ == "__main__":
    unittest.main()
