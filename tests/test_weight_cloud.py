from __future__ import annotations

import unittest

from boneweaver.core.weight_cloud import analyze_weight_cloud, weighted_percentile


class WeightCloudTests(unittest.TestCase):
    def test_linear_cloud_recovers_principal_direction(self) -> None:
        points = tuple(((float(index), 0.02 * (-1) ** index, 0.0), 1.0) for index in range(1, 11))
        stats = analyze_weight_cloud("Leaf", (0.0, 0.0, 0.0), points)
        self.assertEqual(stats.cloud_class, "LINEAR")
        self.assertGreater(stats.principal_axis[0], 0.99)
        self.assertGreaterEqual(stats.confidence, 0.7)

    def test_planar_and_isotropic_clouds_are_not_claimed_linear(self) -> None:
        planar = tuple(((x, y, 0.0), 1.0) for x in (-2.0, -1.0, 1.0, 2.0) for y in (-2.0, -1.0, 1.0, 2.0))
        sphere = tuple(((x, y, z), 1.0) for x, y, z in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))
        self.assertEqual(analyze_weight_cloud("Skirt", (0,0,0), planar).cloud_class, "PLANAR")
        self.assertEqual(analyze_weight_cloud("Ball", (0,0,0), sphere).cloud_class, "ISOTROPIC")

    def test_insufficient_cloud_and_weighted_percentile(self) -> None:
        stats = analyze_weight_cloud("Empty", (0,0,0), ())
        self.assertEqual(stats.cloud_class, "INSUFFICIENT")
        self.assertIsNone(stats.principal_axis)
        self.assertAlmostEqual(weighted_percentile(((1.0, 1.0), (2.0, 1.0), (10.0, 8.0)), 0.5), 10.0)


if __name__ == "__main__":
    unittest.main()
