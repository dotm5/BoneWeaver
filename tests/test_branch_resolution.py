from __future__ import annotations

import dataclasses
import unittest

from tests.test_physics_graph import state
from ue_chain_prep.contracts import BranchResolutionMode
from ue_chain_prep.core.branch_resolution import resolve_branch


def bag_fixture():
    return (
        state("bag_r_02", None, ("bag_r_03",), (0, 0, 0)),
        state("bag_r_03", "bag_r_02", ("bag_r_04", "bag_r_03a_01"), (0, 1, 0)),
        state("bag_r_04", "bag_r_03", ("bag_r_05",), (0, 2, 0)),
        state("bag_r_05", "bag_r_04", ("bag_r_06",), (0, 3, 0)),
        state("bag_r_06", "bag_r_05", (), (0, 4, 0)),
        state("bag_r_03a_01", "bag_r_03", ("bag_r_03a_02",), (0.5, 1.7, 0)),
        state("bag_r_03a_02", "bag_r_03a_01", (), (1.0, 2.4, 0)),
    )


class BranchResolutionTests(unittest.TestCase):
    def test_bag_fixture_selects_longest_main_continuation(self) -> None:
        resolution = resolve_branch("bag_r_03", bag_fixture())
        self.assertEqual(resolution.selected_child_name, "bag_r_04")
        self.assertIn(resolution.result, {"HIGH", "MEDIUM"})
        self.assertGreaterEqual(resolution.score, 0.55)
        self.assertGreaterEqual(resolution.margin, 0.08)
        self.assertEqual(resolution.side_child_names, ("bag_r_03a_01",))
        self.assertGreater(
            resolution.candidates[0].longest_downstream_path_length,
            resolution.candidates[1].longest_downstream_path_length,
        )

    def test_short_immediate_edge_can_win_with_longer_downstream_path(self) -> None:
        bones = (
            state("hair_branch", None, ("hair_a", "hair_b"), (0, 0, 0)),
            state("hair_a", "hair_branch", ("hair_a2",), (0, 0.2, 0)),
            state("hair_a2", "hair_a", ("hair_a3",), (0, 2.2, 0)),
            state("hair_a3", "hair_a2", (), (0, 4.2, 0)),
            state("hair_b", "hair_branch", (), (2, 0, 0)),
        )
        resolution = resolve_branch("hair_branch", bones)
        self.assertEqual(resolution.selected_child_name, "hair_a")

    def test_weighted_short_branch_can_beat_unweighted_decorative_branch(self) -> None:
        bones = (
            state("hair_branch", None, ("hair_long", "hair_weighted"), (0, 0, 0)),
            state("hair_long", "hair_branch", ("hair_long2",), (0, 1.4, 0)),
            state("hair_long2", "hair_long", (), (0, 2.8, 0)),
            state("hair_weighted", "hair_branch", (), (1.0, 0.7, 0)),
        )
        resolution = resolve_branch(
            "hair_branch", bones, deform_weight_mass={"hair_weighted": 10.0},
        )
        self.assertEqual(resolution.selected_child_name, "hair_weighted")

    def test_symmetric_equal_branch_remains_ambiguous(self) -> None:
        bones = (
            state("Skirt", None, ("Left", "Right"), (0, 0, 0)),
            state("Left", "Skirt", (), (-1, 1, 0)),
            state("Right", "Skirt", (), (1, 1, 0)),
        )
        resolution = resolve_branch("Skirt", bones)
        self.assertEqual(resolution.result, "AMBIGUOUS")
        self.assertIsNone(resolution.selected_child_name)
        self.assertIn("UECP_BRANCH_AMBIGUOUS", resolution.issue_codes)

    def test_three_way_branch_is_deterministic(self) -> None:
        bones = (
            state("hair_branch", None, ("hair_a", "hair_b", "hair_c"), (0, 0, 0)),
            state("hair_a", "hair_branch", (), (-1, 1, 0)),
            state("hair_b", "hair_branch", ("hair_b2",), (0, 1, 0)),
            state("hair_b2", "hair_b", ("hair_b3",), (0, 2, 0)),
            state("hair_b3", "hair_b2", (), (0, 3, 0)),
            state("hair_c", "hair_branch", (), (1, 1, 0)),
        )
        first = resolve_branch("hair_branch", bones)
        second = resolve_branch("hair_branch", tuple(reversed(bones)))
        self.assertEqual(first, second)
        self.assertEqual(first.selected_child_name, "hair_b")

    def test_main_skeleton_branch_is_never_auto_selected(self) -> None:
        bones = (
            state("spine_01", None, ("spine_02", "clavicle_l"), (0, 0, 0)),
            state("spine_02", "spine_01", (), (0, 2, 0)),
            state("clavicle_l", "spine_01", (), (1, 1, 0)),
        )
        resolution = resolve_branch("spine_01", bones)
        self.assertIsNone(resolution.selected_child_name)
        self.assertEqual(resolution.result, "BLOCKED")
        self.assertIn("UECP_BRANCH_AUTO_MAIN_SKELETON_FORBIDDEN", resolution.issue_codes)

    def test_socket_branch_is_penalized(self) -> None:
        bones = list(bag_fixture())
        socket_index = next(index for index, bone in enumerate(bones) if bone.name == "bag_r_04")
        bones[socket_index] = dataclasses.replace(bones[socket_index], is_socket=True)
        resolution = resolve_branch("bag_r_03", tuple(bones))
        self.assertNotEqual(resolution.selected_child_name, "bag_r_04")

    def test_manual_selection_is_authoritative(self) -> None:
        resolution = resolve_branch(
            "bag_r_03", bag_fixture(), mode="MANUAL_ONLY", manual_selected_child="bag_r_03a_01"
        )
        self.assertEqual(resolution.selected_child_name, "bag_r_03a_01")
        self.assertEqual(resolution.result, "MANUAL")
        self.assertEqual(resolution.score, 1.0)

    def test_naming_continuity_cannot_override_opposite_geometry(self) -> None:
        bones = (
            state("chain_03", "Incoming", ("chain_04", "side"), (0, 1, 0)),
            state("Incoming", None, ("chain_03",), (0, 0, 0)),
            state("chain_04", "chain_03", (), (0, -1, 0)),
            state("side", "chain_03", ("side2",), (0, 2, 0)),
            state("side2", "side", (), (0, 3, 0)),
        )
        resolution = resolve_branch("chain_03", bones)
        self.assertNotEqual(resolution.selected_child_name, "chain_04")

    def test_enum_values_are_stable(self) -> None:
        self.assertEqual(
            tuple(item.value for item in BranchResolutionMode),
            ("AUTO_MAIN_PATH", "LONGEST_PATH_ONLY", "DIRECTION_CONTINUITY", "MANUAL_ONLY", "KEEP_ORIGINAL"),
        )


if __name__ == "__main__":
    unittest.main()
