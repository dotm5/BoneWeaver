from __future__ import annotations

from array import array
import unittest

from ue_chain_prep.core.weight_islands import (
    CompactPerMeshWeightedInput,
    PerMeshWeightedInput,
    resolve_weight_islands,
)


def mesh_input(name, points, edges):
    return PerMeshWeightedInput(
        name,
        tuple((index, tuple(point), float(weight)) for index, (point, weight) in enumerate(points)),
        tuple(tuple(edge) for edge in edges),
    )


class WeightIslandTests(unittest.TestCase):
    def test_single_connected_region_is_used(self) -> None:
        source = mesh_input(
            "Mesh", (((1, 0, 0), 1), ((2, 0, 0), 1), ((3, 0, 0), 1)),
            ((0, 1), (1, 2)),
        )
        result = resolve_weight_islands("Bone", (0, 0, 0), (source,))
        self.assertEqual(len(result.selected_weighted_points), 3)
        self.assertEqual(result.per_mesh_clouds[0].component_count, 1)
        self.assertEqual(result.per_mesh_clouds[0].dominant_weight_ratio, 1.0)
        self.assertEqual(result.warnings, ())

    def test_ninety_percent_dominant_component_is_used_without_midpoint(self) -> None:
        source = mesh_input(
            "Mesh",
            (((1, 0, 0), 4.5), ((2, 0, 0), 4.5), ((100, 0, 0), 1.0)),
            ((0, 1),),
        )
        result = resolve_weight_islands("Bone", (0, 0, 0), (source,))
        self.assertEqual(len(result.selected_weighted_points), 2)
        self.assertAlmostEqual(result.per_mesh_clouds[0].dominant_weight_ratio, 0.9)
        self.assertLess(result.per_mesh_clouds[0].selected_centroid[0], 3.0)

    def test_two_comparable_disconnected_islands_do_not_point_to_blank_midpoint(self) -> None:
        source = mesh_input(
            "Mesh",
            (((-10, 0, 0), 1), ((-9, 0, 0), 1), ((9, 0, 0), 1), ((10, 0, 0), 1)),
            ((0, 1), (2, 3)),
        )
        result = resolve_weight_islands("Bone", (0, 0, 0), (source,))
        self.assertEqual(result.selected_weighted_points, ())
        self.assertIn("UECP_DISCONNECTED_WEIGHT_ISLANDS", result.warnings)
        self.assertIsNone(result.per_mesh_clouds[0].selected_centroid)

    def test_two_meshes_with_compatible_directions_are_combined(self) -> None:
        first = mesh_input("A", (((1, 0, 0), 1), ((2, 0, 0), 1), ((3, 0, 0), 1)), ((0, 1), (1, 2)))
        second = mesh_input("B", (((2, 0.1, 0), 1), ((3, 0.1, 0), 1), ((4, 0.1, 0), 1)), ((0, 1), (1, 2)))
        result = resolve_weight_islands("Bone", (0, 0, 0), (first, second))
        self.assertEqual(len(result.selected_weighted_points), 6)
        self.assertNotIn("UECP_WEIGHT_DIRECTION_CONFLICT", result.warnings)

    def test_two_meshes_with_conflicting_directions_do_not_create_midpoint(self) -> None:
        first = mesh_input("A", (((1, 0, 0), 1), ((2, 0, 0), 1), ((3, 0, 0), 1)), ((0, 1), (1, 2)))
        second = mesh_input("B", (((-1, 0, 0), 1), ((-2, 0, 0), 1), ((-3, 0, 0), 1)), ((0, 1), (1, 2)))
        result = resolve_weight_islands("Bone", (0, 0, 0), (first, second))
        self.assertEqual(result.selected_weighted_points, ())
        self.assertIn("UECP_WEIGHT_DIRECTION_CONFLICT", result.warnings)

    def test_dominant_mesh_can_win_cross_mesh_conflict(self) -> None:
        first = mesh_input("A", (((1, 0, 0), 4), ((2, 0, 0), 4), ((3, 0, 0), 4)), ((0, 1), (1, 2)))
        second = mesh_input("B", (((-1, 0, 0), 1), ((-2, 0, 0), 1), ((-3, 0, 0), 1)), ((0, 1), (1, 2)))
        result = resolve_weight_islands("Bone", (0, 0, 0), (first, second))
        self.assertEqual(len(result.selected_weighted_points), 3)
        self.assertTrue(all(point[0] > 0 for point, _ in result.selected_weighted_points))
        self.assertIn("UECP_WEIGHT_DIRECTION_CONFLICT", result.warnings)

    def test_require_single_component_rejects_every_multi_island_mesh(self) -> None:
        source = mesh_input(
            "Mesh",
            (((1, 0, 0), 1), ((2, 0, 0), 1), ((4, 0, 0), 1), ((5, 0, 0), 1)),
            ((0, 1), (2, 3)),
        )
        result = resolve_weight_islands(
            "Bone", (0, 0, 0), (source,), policy="REQUIRE_SINGLE_COMPONENT",
        )
        self.assertEqual(result.selected_weighted_points, ())
        self.assertIn("UECP_WEIGHT_ISLAND_POLICY_BLOCKED", result.warnings)

    def test_all_compatible_components_merges_only_matching_directions(self) -> None:
        compatible = mesh_input(
            "Mesh",
            (((1, 0, 0), 1), ((2, 0, 0), 1), ((4, 0.1, 0), 1), ((5, 0.1, 0), 1)),
            ((0, 1), (2, 3)),
        )
        merged = resolve_weight_islands(
            "Bone", (0, 0, 0), (compatible,),
            policy="ALL_COMPATIBLE_COMPONENTS",
        )
        self.assertEqual(len(merged.selected_weighted_points), 4)
        self.assertNotIn("UECP_WEIGHT_DIRECTION_CONFLICT", merged.warnings)

        conflicting = mesh_input(
            "Mesh",
            (((1, 0, 0), 1), ((2, 0, 0), 1), ((-1, 0, 0), 1), ((-2, 0, 0), 1)),
            ((0, 1), (2, 3)),
        )
        blocked = resolve_weight_islands(
            "Bone", (0, 0, 0), (conflicting,),
            policy="ALL_COMPATIBLE_COMPONENTS",
        )
        self.assertEqual(blocked.selected_weighted_points, ())
        self.assertIn("UECP_WEIGHT_DIRECTION_CONFLICT", blocked.warnings)
        self.assertIn("UECP_WEIGHT_ISLAND_POLICY_BLOCKED", blocked.warnings)

    def test_dominant_threshold_is_inclusive_and_does_not_round_up(self) -> None:
        exact = mesh_input(
            "Exact",
            (((1, 0, 0), 3.5), ((2, 0, 0), 3.5), ((4, 0, 0), 1.5), ((5, 0, 0), 1.5)),
            ((0, 1), (2, 3)),
        )
        self.assertEqual(
            len(resolve_weight_islands("Bone", (0, 0, 0), (exact,)).selected_weighted_points),
            2,
        )
        below = mesh_input(
            "Below",
            (((1, 0, 0), 3.495), ((2, 0, 0), 3.495), ((4, 0, 0), 1.505), ((5, 0, 0), 1.505)),
            ((0, 1), (2, 3)),
        )
        result = resolve_weight_islands("Bone", (0, 0, 0), (below,))
        self.assertEqual(result.selected_weighted_points, ())
        self.assertIn("UECP_WEIGHT_ISLAND_POLICY_BLOCKED", result.warnings)

    def test_compact_csr_path_does_not_need_complete_edge_buffer(self) -> None:
        source = CompactPerMeshWeightedInput(
            "Mesh",
            array("I", (0, 1, 2)),
            array("d", (1, 0, 0, 2, 0, 0, 3, 0, 0)),
            array("d", (1, 1, 1)),
            array("I"),
            array("I", (0, 1, 3, 4)),
            array("I", (1, 0, 2, 1)),
        )
        result = resolve_weight_islands("Bone", (0, 0, 0), (source,))
        self.assertEqual(len(result.selected_weighted_points), 3)
        self.assertEqual(result.per_mesh_clouds[0].component_count, 1)


if __name__ == "__main__":
    unittest.main()
