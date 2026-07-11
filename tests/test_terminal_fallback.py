from __future__ import annotations

import dataclasses
import unittest

from tests.test_physics_graph import state
from ue_chain_prep.contracts import TerminalResolutionClass
from ue_chain_prep.core.terminal_candidates import safe_parent_chain_fallback


class TerminalFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bones = (
            state("B0", None, ("B1",), (0, 0, 0)),
            state("B1", "B0", ("B2",), (0, 1, 0)),
            state("B2", "B1", ("Leaf",), (0, 3, 0)),
            state("Leaf", "B2", (), (0, 6, 0)),
        )

    def test_uses_parent_direction_and_median_of_nearest_three_segments(self) -> None:
        solution = safe_parent_chain_fallback(self.bones[-1], self.bones)
        self.assertEqual(solution.source, "PARENT_CHAIN_EXTRAPOLATION")
        self.assertEqual(solution.resolution_class, "AUTO_SAFE_FALLBACK")
        self.assertAlmostEqual(solution.length, 2.0)
        self.assertEqual(solution.tail, (0.0, 8.0, 0.0))
        self.assertTrue(solution.requires_confirmation)
        self.assertNotEqual(solution.source, "MANUAL_OVERRIDE")
        self.assertNotEqual(solution.candidates[0].kind, "MANUAL")

    def test_no_weight_evidence_is_not_required(self) -> None:
        solution = safe_parent_chain_fallback(self.bones[-1], self.bones)
        self.assertIsNotNone(solution.selected_candidate_id)
        self.assertEqual(solution.resolution_class, "AUTO_SAFE_FALLBACK")

    def test_zero_length_incoming_segment_is_unresolved(self) -> None:
        coincident = dataclasses.replace(self.bones[-1], head=self.bones[-2].head)
        solution = safe_parent_chain_fallback(coincident, self.bones[:-1] + (coincident,))
        self.assertEqual(solution.resolution_class, "UNRESOLVED")
        self.assertIn("UECP_COINCIDENT_HELPER", solution.evidence)

    def test_missing_parent_is_unresolved(self) -> None:
        orphan = dataclasses.replace(self.bones[-1], parent_name=None)
        solution = safe_parent_chain_fallback(orphan, self.bones[:-1] + (orphan,))
        self.assertEqual(solution.resolution_class, "UNRESOLVED")
        self.assertIn("UECP_TERMINAL_PARENT_UNAVAILABLE", solution.evidence)

    def test_unresolved_branch_is_not_silently_crossed(self) -> None:
        solution = safe_parent_chain_fallback(self.bones[-1], self.bones, unresolved_branch=True)
        self.assertEqual(solution.resolution_class, "UNRESOLVED")
        self.assertIn("UECP_BRANCH_AMBIGUOUS", solution.evidence)

    def test_socket_control_or_helper_is_not_eligible(self) -> None:
        socket = dataclasses.replace(self.bones[-1], is_socket=True)
        solution = safe_parent_chain_fallback(socket, self.bones[:-1] + (socket,))
        self.assertEqual(solution.resolution_class, "UNRESOLVED")
        control = dataclasses.replace(self.bones[-1], importer_metadata_flags=("CONTROL",))
        solution = safe_parent_chain_fallback(control, self.bones[:-1] + (control,))
        self.assertEqual(solution.resolution_class, "UNRESOLVED")

    def test_reliable_reverse_weight_direction_blocks_fallback(self) -> None:
        solution = safe_parent_chain_fallback(
            self.bones[-1],
            self.bones,
            reliable_weight_direction=(0.0, -1.0, 0.0),
            reliable_weight_confidence=0.9,
            reliable_confidence_threshold=0.7,
        )
        self.assertEqual(solution.resolution_class, "UNRESOLVED")
        self.assertIn("UECP_WEIGHT_DIRECTION_CONFLICT", solution.evidence)

    def test_enum_values_are_stable(self) -> None:
        self.assertEqual(
            tuple(item.value for item in TerminalResolutionClass),
            ("AUTO_CONFIDENT", "AUTO_SAFE_FALLBACK", "MANUAL", "UNRESOLVED"),
        )


if __name__ == "__main__":
    unittest.main()
