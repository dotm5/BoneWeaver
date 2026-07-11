from __future__ import annotations

import unittest

from tests.test_physics_graph import state
from ue_chain_prep.core.models import TerminalCandidate, TerminalCandidateScore
from ue_chain_prep.core.terminal_candidates import authoritative_solution, generate_candidates, select_candidate
from ue_chain_prep.core.weight_cloud import analyze_weight_cloud


class TerminalCandidateTests(unittest.TestCase):
    def test_auto_six_axis_scoring_selects_supported_positive_axis_deterministically(self) -> None:
        bone = state("Leaf", "Parent", (), (0,0,0), tail=(0,1,0))
        cloud = analyze_weight_cloud("Leaf", (0,0,0), tuple(((float(i), 0, 0), 1.0) for i in range(1, 9)))
        candidates = generate_candidates(bone, cloud, parent_direction=(1,0,0), reference_length=4.0)
        imported = [candidate for candidate in candidates if candidate.kind == "IMPORTED_AXIS"]
        self.assertEqual(len(imported), 6)
        solution = select_candidate("Leaf", tuple(reversed(candidates)), minimum_score=0.5, minimum_margin=0.01)
        self.assertGreater(solution.direction[0], 0.99)
        self.assertFalse(solution.requires_confirmation)
        self.assertEqual(solution, select_candidate("Leaf", candidates, minimum_score=0.5, minimum_margin=0.01))

    def test_equal_candidates_produce_ambiguity_instead_of_silent_choice(self) -> None:
        score = TerminalCandidateScore(0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.5)
        candidates = tuple(
            TerminalCandidate(f"c{index}", "IMPORTED_AXIS", label, direction, 1.0, 1.0, direction, score, (), ())
            for index, (label, direction) in enumerate((("X_POSITIVE", (1.0,0.0,0.0)), ("X_NEGATIVE", (-1.0,0.0,0.0))))
        )
        solution = select_candidate("Leaf", candidates, minimum_score=0.4, minimum_margin=0.08)
        self.assertTrue(solution.requires_confirmation)
        self.assertIn("UECP_TERMINAL_CANDIDATE_AMBIGUOUS", solution.evidence)

    def test_no_weight_cloud_can_fall_back_to_parent_tangent(self) -> None:
        bone = state("Leaf", "Parent", (), (0,0,0), tail=(0,1,0))
        cloud = analyze_weight_cloud("Leaf", (0,0,0), ())
        candidates = generate_candidates(bone, cloud, parent_direction=(0,0,1), reference_length=2.0)
        solution = select_candidate("Leaf", candidates, minimum_score=0.45, minimum_margin=0.01)
        self.assertGreater(solution.direction[2], 0.99)

    def test_unique_direct_child_is_authoritative(self) -> None:
        solution = authoritative_solution(
            "Leaf", (0,0,0), (0,2,0),
            source="UNIQUE_DIRECT_CHILD_HEAD", kind="DIRECT_CHILD",
        )
        self.assertEqual(solution.tail, (0.0, 2.0, 0.0))
        self.assertEqual(solution.confidence, 1.0)
        self.assertFalse(solution.requires_confirmation)
        self.assertEqual(solution.candidates[0].score.total, 1.0)


if __name__ == "__main__":
    unittest.main()
