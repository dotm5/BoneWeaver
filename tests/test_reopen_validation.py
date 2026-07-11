from __future__ import annotations

import json
from pathlib import Path
import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.reopen_validation import validate_reopened_file


class ReopenValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        for text in tuple(bpy.data.texts):
            if text.name == "UECP_EXPORT_MANIFEST" or text.name.startswith("UECP_SNAPSHOT::"):
                bpy.data.texts.remove(text)
        ue_chain_prep.register()

    def tearDown(self) -> None:
        ue_chain_prep.unregister()
        clear_scene()

    def test_missing_manifest_and_snapshot_fail_closed(self) -> None:
        report = validate_reopened_file()
        self.assertFalse(report.success)
        self.assertIn("UECP_REOPEN_MANIFEST_MISSING", report.issues)

    def test_export_pipeline_runs_independent_reopen_validation(self) -> None:
        rig = make_chain()
        mesh, _ = make_bound_mesh(rig)
        for name in ("Bone_1", "Bone_2"):
            group = mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40
        output_dir = Path(__file__).resolve().parents[1] / "test-output" / "reopen-validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        source = output_dir / "source.blend"
        converted = output_dir / "converted.blend"
        report_path = output_dir / "reopen-validation.json"
        for path in (source, converted, report_path, output_dir / "conversion-audit.json"):
            if path.exists():
                path.unlink()
        bpy.ops.wm.save_as_mainfile(filepath=str(source))
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertEqual(bpy.ops.uecp.apply(plan_id=runtime.plan_id), {"FINISHED"})
        self.assertEqual(bpy.ops.uecp.export_conversion(filepath=str(converted)), {"FINISHED"})
        self.assertTrue(report_path.exists())
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["success"], payload["issues"])
        self.assertTrue(payload["snapshot_conflict_check_ran"])
        self.assertEqual(payload["mutation_record_count"], payload["manifest_mutation_record_count"])
        audit = json.loads((output_dir / "conversion-audit.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["reopen_validation"]["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
