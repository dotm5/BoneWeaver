from __future__ import annotations

import unittest
from pathlib import Path

import bpy

import boneweaver
from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain


class UIRefactorTests(unittest.TestCase):
    def setUp(self):
        boneweaver.unregister()
        clear_scene()
        boneweaver.register()

    def tearDown(self):
        boneweaver.unregister()
        clear_scene()

    def test_main_panel_source_has_no_engineering_parameters_or_runtime_branching(self):
        path = Path(__file__).resolve().parents[1] / "boneweaver" / "ui" / "panels" / "main.py"
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "minimum_weight", "weight_exponent", "minimum_confidence",
            "candidate_minimum_margin", "position_epsilon_factor", "runtime.state",
            "issue.code", "plan_id", "fingerprint",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("panel_view_state_from_context", source)

    def test_panel_layers_and_primary_operators_are_registered(self):
        for name in (
            "BONEWEAVER_PT_main", "BONEWEAVER_PT_advanced", "BONEWEAVER_PT_details",
            "BONEWEAVER_PT_recovery", "BONEWEAVER_PT_developer",
            "BONEWEAVER_OT_check_and_preview", "BONEWEAVER_OT_locate_issue", "BONEWEAVER_OT_load_details",
        ):
            self.assertTrue(hasattr(bpy.types, name), name)

    def test_unimplemented_export_flags_are_not_public(self):
        properties = bpy.types.BONEWEAVER_OT_export_report.bl_rna.properties
        for name in ("include_plan", "include_weight_stats", "include_snapshot_summary"):
            self.assertNotIn(name, properties)

    def test_panel_business_branching_lives_in_view_models(self):
        root = Path(__file__).resolve().parents[1] / "boneweaver" / "ui" / "panels"
        for name in ("advanced.py", "details.py", "recovery.py", "developer.py"):
            source = (root / name).read_text(encoding="utf-8")
            self.assertNotIn("runtime =", source, name)

    def test_developer_diagnostics_default_hidden(self):
        from boneweaver.ui.preferences import BONEWEAVER_AddonPreferences as prefs_type
        prop = prefs_type.bl_rna.properties["enable_developer_diagnostics"]
        self.assertFalse(prop.default)

    def test_analyze_keeps_rna_lists_lazy_until_requested(self):
        rig = make_chain(count=3)
        make_bound_mesh(rig)
        result = bpy.ops.boneweaver.analyze()
        self.assertEqual({"FINISHED"}, result)
        wm = bpy.context.window_manager
        self.assertEqual(0, len(wm.boneweaver_proposal_items))
        self.assertFalse(wm.boneweaver_runtime.details_loaded)
        from boneweaver.core.runtime_store import get_performance
        metrics = get_performance(wm.boneweaver_runtime.plan_id)
        self.assertIn("tracemalloc_peak", metrics)
        self.assertIn("preview_build_time", metrics)
        self.assertEqual(0, metrics["ui_item_count"])
        self.assertEqual({"FINISHED"}, bpy.ops.boneweaver.load_details())
        self.assertTrue(wm.boneweaver_runtime.details_loaded)
        self.assertGreater(len(wm.boneweaver_chain_items), 0)
        self.assertLessEqual(len(wm.boneweaver_proposal_items), 200)

    def test_issue_list_shows_affected_bone_and_readable_summary(self):
        from boneweaver.ui.lists import BONEWEAVER_UL_issues

        class FakeLayout:
            def __init__(self):
                self.labels = []

            def label(self, *, text, icon):
                self.labels.append((text, icon))

        class FakeItem:
            bone_name = "hair_ribbon_l_06"
            code = "BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS"
            message = "BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS"
            severity = "BLOCKER"

        layout = FakeLayout()
        BONEWEAVER_UL_issues.draw_item(None, None, layout, None, FakeItem(), None, None, None, 0)

        self.assertEqual([("hair_ribbon_l_06 · 末端方向存在歧义", "ERROR")], layout.labels)

    def test_details_locate_operator_shows_selected_bone(self):
        source = (Path(__file__).resolve().parents[1] / "boneweaver" / "ui" / "panels" / "details.py").read_text(encoding="utf-8")
        self.assertIn('text=f"定位：{view.selected_issue_bone}"', source)


if __name__ == "__main__":
    unittest.main()
