from __future__ import annotations

import unittest

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from boneweaver.core.weight_cloud import collect_weight_evidence


class WeightCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()

    def tearDown(self) -> None:
        clear_scene()

    def test_scans_each_vertex_and_membership_once_with_chain_exclusivity(self) -> None:
        rig = make_chain()
        mesh, _ = make_bound_mesh(rig)
        second = mesh.vertex_groups.new(name="Bone_1")
        second.add([0, 1, 2], 0.5, "REPLACE")
        first = mesh.vertex_groups["Bone_0"]
        first.add([0, 1, 2], 0.5, "REPLACE")
        result = collect_weight_evidence(
            rig, (mesh,), ("Bone_0", "Bone_1"), minimum_weight=0.0,
            weight_exponent=2.0, use_vertex_area_weight=True,
            exclusivity_mode="CHAIN_NORMALIZED",
        )
        self.assertEqual(result.vertex_count, 3)
        self.assertEqual(result.membership_count, 6)
        self.assertEqual(len(result.points_by_bone["Bone_0"]), 3)
        self.assertEqual(len(result.points_by_bone["Bone_1"]), 3)
        self.assertAlmostEqual(result.points_by_bone["Bone_0"][0][1], (0.1 / 3.0) * 0.25 * 0.5)
        self.assertEqual(len(result.per_mesh_inputs_by_bone["Bone_0"]), 1)
        compact_input = result.per_mesh_inputs_by_bone["Bone_0"][0]
        self.assertEqual(compact_input.mesh_name, mesh.name)
        self.assertEqual(len(compact_input.weighted_vertices), 3)
        self.assertEqual(compact_input.edges, ((0, 1), (0, 2), (1, 2)))


if __name__ == "__main__":
    unittest.main()
