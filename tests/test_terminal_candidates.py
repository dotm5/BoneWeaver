from __future__ import annotations

import unittest
import math
import dataclasses

from tests.test_physics_graph import state
from boneweaver.core.models import TerminalCandidate, TerminalCandidateScore
from boneweaver.core.terminal_candidates import authoritative_solution, generate_candidates, select_candidate
from boneweaver.core.weight_cloud import analyze_weight_cloud


class TerminalCandidateTests(unittest.TestCase):
    @staticmethod
    def candidate(candidate_id, kind, degrees, total):
        radians = math.radians(degrees)
        direction = (math.cos(radians), math.sin(radians), 0.0)
        score = TerminalCandidateScore(0.5, 0.5, 0.5, 0.0, 0.5, 0.0, total)
        return TerminalCandidate(
            candidate_id, kind, None, direction, 1.0, 1.0, direction,
            score, (kind,), (),
        )

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
        self.assertIn("BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS", solution.evidence)

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

    def test_near_parallel_evidence_clusters_before_margin(self) -> None:
        candidates = (
            self.candidate("pca", "WEIGHT_PRINCIPAL_AXIS", 0.0, 0.70),
            self.candidate("axis", "IMPORTED_AXIS", 2.0, 0.69),
            self.candidate("opposite", "ORIGINAL_DISPLAY_AXIS", 180.0, 0.65),
        )
        solution = select_candidate(
            "Leaf", candidates, minimum_score=0.60, minimum_margin=0.08,
            candidate_direction_merge_angle_degrees=7.5,
        )
        self.assertEqual(len(solution.candidate_clusters), 2)
        self.assertFalse(solution.requires_confirmation)
        self.assertGreater(solution.score_margin, 0.08)
        winning = solution.candidate_clusters[0]
        self.assertEqual(set(winning.member_candidate_ids), {"pca", "axis"})
        self.assertGreater(winning.direction[0], 0.999)

    def test_three_supporting_candidates_have_bounded_bonus(self) -> None:
        candidates = (
            self.candidate("pca", "WEIGHT_PRINCIPAL_AXIS", -1.0, 0.70),
            self.candidate("axis", "IMPORTED_AXIS", 0.0, 0.69),
            self.candidate("parent", "PARENT_TANGENT", 1.0, 0.68),
            self.candidate("opposite", "ORIGINAL_DISPLAY_AXIS", 180.0, 0.65),
        )
        solution = select_candidate(
            "Leaf", candidates, minimum_score=0.60, minimum_margin=0.08,
            candidate_direction_merge_angle_degrees=7.5,
        )
        self.assertEqual(len(solution.candidate_clusters), 2)
        self.assertLessEqual(solution.candidate_clusters[0].support_bonus, 0.12)
        self.assertEqual(len(solution.candidate_clusters[0].evidence_kinds), 3)

    def test_genuinely_different_directions_remain_independent(self) -> None:
        candidates = (
            self.candidate("first", "WEIGHT_PRINCIPAL_AXIS", 0.0, 0.70),
            self.candidate("second", "PARENT_TANGENT", 30.0, 0.69),
        )
        solution = select_candidate(
            "Leaf", candidates, minimum_score=0.60, minimum_margin=0.08,
            candidate_direction_merge_angle_degrees=7.5,
        )
        self.assertEqual(len(solution.candidate_clusters), 2)
        self.assertTrue(solution.requires_confirmation)
        self.assertIn("BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS", solution.evidence)

    def test_cluster_order_is_deterministic(self) -> None:
        candidates = (
            self.candidate("pca", "WEIGHT_PRINCIPAL_AXIS", 0.0, 0.70),
            self.candidate("axis", "IMPORTED_AXIS", 2.0, 0.69),
            self.candidate("other", "PARENT_TANGENT", 90.0, 0.40),
        )
        first = select_candidate("Leaf", candidates, candidate_direction_merge_angle_degrees=7.5)
        second = select_candidate("Leaf", tuple(reversed(candidates)), candidate_direction_merge_angle_degrees=7.5)
        self.assertEqual(first, second)

    def test_imported_axis_prior_requires_reliable_importer_metadata(self) -> None:
        plain = state("Leaf", "Parent", (), (0, 0, 0), tail=(0, 1, 0))
        tagged = dataclasses.replace(plain, importer_metadata_flags=("orig_quat", "post_quat"))
        cloud = analyze_weight_cloud("Leaf", (0, 0, 0), ())
        plain_axis = next(c for c in generate_candidates(plain, cloud, parent_direction=(0, 1, 0), reference_length=1.0)
                          if c.kind == "IMPORTED_AXIS" and c.axis_label == "Y_POSITIVE")
        tagged_axis = next(c for c in generate_candidates(tagged, cloud, parent_direction=(0, 1, 0), reference_length=1.0)
                           if c.kind == "IMPORTED_AXIS" and c.axis_label == "Y_POSITIVE")
        self.assertLess(plain_axis.score.imported_axis_prior, tagged_axis.score.imported_axis_prior)
        self.assertLess(plain_axis.score.total, tagged_axis.score.total)


if __name__ == "__main__":
    unittest.main()
