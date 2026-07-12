from __future__ import annotations

from array import array
import dataclasses
import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.mesh_scan_cache import MeshScanCache
from ue_chain_prep.core.runtime_store import get_performance, get_plan


class MeshScanCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        extra = self.mesh.vertex_groups.new(name="Bone_1")
        extra.add([0, 1, 2], 0.5, "REPLACE")

    def tearDown(self) -> None:
        ue_chain_prep.unregister()
        clear_scene()

    def test_scan_combines_digests_memberships_and_compact_weight_inputs(self) -> None:
        cache = MeshScanCache.scan(
            self.rig,
            (self.mesh,),
            ("Bone_0", "Bone_1"),
            minimum_weight=0.0,
            weight_exponent=2.0,
            use_vertex_area_weight=True,
            exclusivity_mode="CHAIN_NORMALIZED",
        )
        self.assertEqual(cache.vertex_pass_count, 1)
        self.assertEqual(cache.membership_pass_count, 1)
        self.assertEqual(cache.vertex_count, 3)
        self.assertEqual(cache.membership_count, 6)
        mesh_scan = cache.meshes[0]
        self.assertEqual(len(mesh_scan.weight_digest), 64)
        self.assertEqual(len(mesh_scan.base_mesh_digest), 64)
        compact = cache.per_mesh_inputs_by_bone["Bone_0"][0]
        self.assertIsInstance(compact.indices, array)
        self.assertIsInstance(compact.coordinates, array)
        self.assertIsInstance(compact.weights, array)
        self.assertIsInstance(compact.edges, array)
        self.assertIsInstance(compact.adjacency_offsets, array)
        self.assertIsInstance(compact.adjacency_neighbors, array)
        self.assertEqual(compact.indices.typecode, "I")
        self.assertEqual(compact.coordinates.typecode, "d")
        self.assertEqual(compact.weights.typecode, "d")
        self.assertEqual(len(compact.adjacency_offsets), len(self.mesh.data.vertices) + 1)
        self.assertGreater(cache.peak_temporary_memory, 0)

    def test_analyze_uses_one_vertex_and_membership_pass_per_mesh(self) -> None:
        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.uecp_runtime
        metrics = get_performance(runtime.plan_id)
        self.assertEqual(metrics["vertex_pass_count"], 1)
        self.assertEqual(metrics["membership_pass_count"], 1)
        self.assertGreaterEqual(metrics["mesh_scan_time"], 0.0)
        self.assertGreaterEqual(metrics["connectivity_time"], 0.0)
        self.assertGreater(metrics["plan_serialized_size"], 0)

    def test_immutable_plan_contains_statistics_not_raw_point_clouds(self) -> None:
        bpy.ops.uecp.analyze()
        plan = get_plan(bpy.context.window_manager.uecp_runtime.plan_id)
        payload = dataclasses.asdict(plan)
        text = repr(payload)
        self.assertNotIn("points_by_bone", text)
        self.assertNotIn("weighted_vertices", text)
        self.assertNotIn("coordinates", text)


if __name__ == "__main__":
    unittest.main()
