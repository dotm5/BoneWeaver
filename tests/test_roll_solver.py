from __future__ import annotations

import math
import unittest

from mathutils import Vector

from ue_chain_prep.core.roll_solver import minimal_twist_reference, parallel_transport_reference, radial_reference
from ue_chain_prep.core.swing_math import swing_rotation


class RollSolverTests(unittest.TestCase):
    def test_minimal_twist_projects_old_z_onto_new_y_plane(self) -> None:
        new_y = (1.0, 1.0, 0.0)
        reference, fallback = minimal_twist_reference(new_y, (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        self.assertFalse(fallback)
        self.assertAlmostEqual(Vector(reference).dot(Vector(new_y).normalized()), 0.0, places=7)
        self.assertGreater(Vector(reference).dot(Vector((0,0,1))), 0.99)

    def test_parallel_transport_is_explicit_and_keeps_parent_hemisphere(self) -> None:
        reference, _ = parallel_transport_reference((0,1,0.2), (0,0,1), (1,0,0), 0.65, 0.35)
        self.assertGreaterEqual(Vector(reference).dot(Vector((0,0,1))), 0.0)

    def test_radial_reference_points_outward(self) -> None:
        reference, _ = radial_reference((0,1,0), (2,0,0), (0,0,0))
        self.assertGreater(Vector(reference).x, 0.99)

    def test_swing_maps_old_segment_to_new_without_extra_twist(self) -> None:
        old = Vector((0,1,0))
        new = Vector((1,0,0))
        swing = swing_rotation(old, new)
        self.assertLess((swing @ old).angle(new), 1.0e-6)
        self.assertAlmostEqual(swing.angle, math.pi / 2.0, places=6)

    def test_mirrored_fallbacks_keep_matching_hemispheres(self) -> None:
        left, left_fallback = minimal_twist_reference((0, 1, 0), (0, 1, 0), (1, 0, 0), (0, 0, 1))
        right, right_fallback = minimal_twist_reference((0, 1, 0), (0, 1, 0), (-1, 0, 0), (0, 0, 1))
        self.assertTrue(left_fallback)
        self.assertTrue(right_fallback)
        self.assertGreaterEqual(Vector(left).dot(Vector((0, 0, 1))), 0.0)
        self.assertGreaterEqual(Vector(right).dot(Vector((0, 0, 1))), 0.0)


if __name__ == "__main__":
    unittest.main()
