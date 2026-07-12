from __future__ import annotations

import math
import unittest

from boneweaver.contracts import ValidationToleranceMode
from boneweaver.core.validation_tolerance import (
    AUTO_TOLERANCE_DEFAULTS,
    MeshCoordinateCapture,
    evaluate_mesh_tolerance,
    float32_ulp,
)


def capture(name, points, *, world_scale=1.0):
    local = tuple(tuple(float(value) for value in point) for point in points)
    world = tuple(tuple(float(value * world_scale) for value in point) for point in points)
    return MeshCoordinateCapture(name, local, world)


class ValidationToleranceTests(unittest.TestCase):
    def test_float32_ulp_uses_adjacent_representable_values(self) -> None:
        self.assertEqual(float32_ulp(0.0), 2.0 ** -149)
        self.assertEqual(float32_ulp(1.0), 2.0 ** -23)
        self.assertEqual(float32_ulp(1024.0), 2.0 ** -13)
        self.assertEqual(float32_ulp(-1.0), 2.0 ** -24)

    def test_auto_limits_are_per_mesh_and_include_float32_budget(self) -> None:
        small = capture("Small", ((0, 0, 0), (1, 0, 0)))
        large = capture("Large", ((0, 0, 0), (1000, 0, 0)))
        same_small = capture("Small", ((0, 0, 0), (1, 0, 0)))
        same_large = capture("Large", ((0, 0, 0), (1000, 0, 0)))
        small_result = evaluate_mesh_tolerance(small, same_small, mode="AUTO_PRODUCTION")
        large_result = evaluate_mesh_tolerance(large, same_large, mode="AUTO_PRODUCTION")
        self.assertAlmostEqual(small_result.mesh_scale, 1.0)
        self.assertAlmostEqual(large_result.mesh_scale, 1000.0)
        self.assertGreater(large_result.soft_limit, small_result.soft_limit)
        self.assertGreaterEqual(
            small_result.float32_ulp_budget,
            float32_ulp(1.0) * AUTO_TOLERANCE_DEFAULTS.float32_ulp_multiplier,
        )

    def test_strict_rejects_noise_that_auto_accepts(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (1, 0, 0)))
        after = capture("Mesh", ((0, 0, 0), (1.0000003, 0, 0)))
        strict = evaluate_mesh_tolerance(before, after, mode="STRICT_TEST")
        auto = evaluate_mesh_tolerance(before, after, mode="AUTO_PRODUCTION")
        self.assertEqual(strict.result, "FAIL_AND_ROLLBACK")
        self.assertIn(auto.result, {"PASS", "PASS_WITH_NUMERIC_NOISE_WARNING"})

    def test_custom_mode_uses_explicit_relative_factor(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (2, 0, 0)))
        after = capture("Mesh", ((0, 0, 0), (2.000001, 0, 0)))
        result = evaluate_mesh_tolerance(
            before,
            after,
            mode="CUSTOM",
            custom_relative_factor=1.0e-6,
        )
        self.assertGreaterEqual(result.soft_limit, 2.0e-6)
        self.assertEqual(result.result, "PASS")

    def test_single_soft_outlier_can_be_numeric_noise_but_hard_outlier_fails(self) -> None:
        points = tuple((float(index), 0.0, 0.0) for index in range(25))
        before = capture("Mesh", points)
        soft_limit = max(
            AUTO_TOLERANCE_DEFAULTS.absolute_floor,
            24.0 * AUTO_TOLERANCE_DEFAULTS.auto_relative_factor,
            float32_ulp(24.0) * AUTO_TOLERANCE_DEFAULTS.float32_ulp_multiplier,
        )
        noisy = list(points)
        noisy[-1] = (noisy[-1][0] + soft_limit * 1.1, 0.0, 0.0)
        noisy_result = evaluate_mesh_tolerance(before, capture("Mesh", noisy), mode="AUTO_PRODUCTION")
        self.assertEqual(noisy_result.result, "PASS_WITH_NUMERIC_NOISE_WARNING")
        self.assertEqual(noisy_result.soft_outlier_count, 1)

        broken = list(points)
        broken[-1] = (broken[-1][0] + soft_limit * 8.0, 0.0, 0.0)
        broken_result = evaluate_mesh_tolerance(before, capture("Mesh", broken), mode="AUTO_PRODUCTION")
        self.assertEqual(broken_result.result, "FAIL_AND_ROLLBACK")
        self.assertEqual(broken_result.hard_outlier_count, 1)

    def test_noop_baseline_contributes_without_mutating_capture(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (1, 0, 0)))
        after = capture("Mesh", ((0, 0, 0), (1.0000002, 0, 0)))
        result = evaluate_mesh_tolerance(
            before,
            after,
            mode="AUTO_PRODUCTION",
            baseline_max_delta=2.0e-7,
            baseline_rms_delta=1.0e-7,
        )
        self.assertGreaterEqual(result.soft_limit, 8.0e-7)
        self.assertEqual(result.baseline_max_delta, 2.0e-7)
        self.assertEqual(result.baseline_rms_delta, 1.0e-7)
        self.assertEqual(before.local_coordinates[-1], (1.0, 0.0, 0.0))

    def test_nonfinite_baseline_cannot_expand_auto_limit_to_infinity(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (1, 0, 0)))
        after = capture("Mesh", ((0, 0, 0), (1001, 0, 0)))
        result = evaluate_mesh_tolerance(
            before,
            after,
            mode="AUTO_PRODUCTION",
            baseline_max_delta=math.inf,
            baseline_rms_delta=math.inf,
        )
        self.assertTrue(math.isfinite(result.soft_limit))
        self.assertTrue(math.isfinite(result.hard_limit))
        self.assertEqual(result.result, "FAIL_AND_ROLLBACK")

    def test_point_count_mismatch_and_nonfinite_coordinates_fail_closed(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (1, 0, 0)))
        count_mismatch = capture("Mesh", ((0, 0, 0),))
        mismatch_result = evaluate_mesh_tolerance(
            before, count_mismatch, mode="AUTO_PRODUCTION",
        )
        self.assertEqual(mismatch_result.result, "FAIL_AND_ROLLBACK")

        nonfinite = MeshCoordinateCapture(
            "Mesh",
            ((0.0, 0.0, 0.0), (math.nan, 0.0, 0.0)),
            ((0.0, 0.0, 0.0), (math.nan, 0.0, 0.0)),
        )
        nonfinite_result = evaluate_mesh_tolerance(
            before, nonfinite, mode="AUTO_PRODUCTION",
        )
        self.assertEqual(nonfinite_result.result, "FAIL_AND_ROLLBACK")

    def test_world_space_is_diagnostic_and_does_not_change_local_result(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (1, 0, 0)), world_scale=1000.0)
        local_after = ((0, 0, 0), (1.0000002, 0, 0))
        after = capture("Mesh", local_after, world_scale=1000.0)
        result = evaluate_mesh_tolerance(before, after, mode="AUTO_PRODUCTION")
        self.assertEqual(result.coordinate_space, "EVALUATED_MESH_OBJECT_LOCAL")
        self.assertGreater(result.world_max_delta, result.max_delta * 900.0)
        self.assertNotEqual(result.result, "FAIL_AND_ROLLBACK")

    def test_recommendation_is_reported_for_failure(self) -> None:
        before = capture("Mesh", ((0, 0, 0), (2, 0, 0)))
        after = capture("Mesh", ((0, 0, 0), (2.01, 0, 0)))
        result = evaluate_mesh_tolerance(before, after, mode="AUTO_PRODUCTION")
        self.assertEqual(result.result, "FAIL_AND_ROLLBACK")
        self.assertAlmostEqual(result.recommended_absolute_limit, result.max_delta * 1.25)
        self.assertAlmostEqual(
            result.recommended_relative_factor,
            result.recommended_absolute_limit / result.mesh_scale,
        )
        self.assertTrue(math.isfinite(result.recommended_relative_factor))

    def test_enum_values_are_stable(self) -> None:
        self.assertEqual(
            tuple(item.value for item in ValidationToleranceMode),
            ("AUTO_PRODUCTION", "STRICT_TEST", "CUSTOM"),
        )


if __name__ == "__main__":
    unittest.main()
