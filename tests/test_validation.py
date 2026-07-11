from __future__ import annotations

import unittest
import json
from pathlib import Path

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.runtime_store import get_plan
from ue_chain_prep.core.validation import capture_neutral_meshes, validate_post_apply


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        for name in ("Bone_1", "Bone_2"):
            group = self.mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40

    def tearDown(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.62
        settings.candidate_minimum_margin = 0.08
        settings.minimum_confidence = 0.70
        ue_chain_prep.unregister()
        for text in tuple(bpy.data.texts):
            if text.name.startswith("UECP_SNAPSHOT::"):
                bpy.data.texts.remove(text)
        clear_scene()

    def test_post_validation_checks_graph_digests_and_neutral_mesh(self) -> None:
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        plan = get_plan(runtime.plan_id)
        neutral = capture_neutral_meshes(plan)
        bpy.ops.uecp.apply(plan_id=runtime.plan_id)
        report = validate_post_apply(bpy.context, plan, neutral)
        self.assertTrue(report.success, report.issues)
        self.assertEqual(report.non_target_bone_changes, 0)
        self.assertEqual(report.weight_digest_changes, 0)
        self.assertLessEqual(report.maximum_neutral_mesh_delta, 1.0e-7)
        self.assertEqual(len(report.mesh_validation_results), 1)
        mesh_result = report.mesh_validation_results[0]
        self.assertEqual(mesh_result.mesh_name, self.mesh.name)
        self.assertEqual(mesh_result.coordinate_space, "EVALUATED_MESH_OBJECT_LOCAL")
        self.assertEqual(mesh_result.tolerance_mode, "AUTO_PRODUCTION")
        self.assertEqual(mesh_result.result, "PASS")
        self.assertGreaterEqual(mesh_result.hard_limit, mesh_result.soft_limit)
        self.assertGreaterEqual(mesh_result.baseline_max_delta, 0.0)
        self.assertGreaterEqual(mesh_result.float32_ulp_budget, 0.0)

    def test_validate_and_export_diagnostic_json(self) -> None:
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        bpy.ops.uecp.apply(plan_id=runtime.plan_id)
        self.assertNotIn("validation_scope", bpy.types.UECP_OT_validate.bl_rna.properties)
        self.assertEqual(bpy.ops.uecp.validate(), {"FINISHED"})
        output = Path(__file__).resolve().parents[1] / "test-output" / "diagnostic-report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertEqual(bpy.ops.uecp.export_report(filepath=str(output)), {"FINISHED"})
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "uecp.diagnostic_report")
        self.assertEqual(payload["plan_id"], runtime.plan_id)
        self.assertIn("physics_graph_id", payload)
        self.assertIn("side_effect_audit", payload)
        self.assertGreater(payload["performance"]["bone_count"], 0)
        self.assertIn("analyze_time", payload["performance"])
        mesh_validation = payload["validation"]["mesh_validation_results"][0]
        self.assertEqual(mesh_validation["coordinate_space"], "EVALUATED_MESH_OBJECT_LOCAL")
        self.assertIn("recommended_relative_factor", mesh_validation)


if __name__ == "__main__":
    unittest.main()
