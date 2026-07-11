from __future__ import annotations

import unittest
from pathlib import Path

import bpy

import ue_chain_prep
from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain


class UIRefactorTests(unittest.TestCase):
    def setUp(self):
        ue_chain_prep.unregister()
        clear_scene()
        ue_chain_prep.register()

    def tearDown(self):
        ue_chain_prep.unregister()
        clear_scene()

    def test_main_panel_source_has_no_engineering_parameters_or_runtime_branching(self):
        path = Path(__file__).resolve().parents[1] / "ue_chain_prep" / "ui" / "panels" / "main.py"
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
            "UECP_PT_main", "UECP_PT_advanced", "UECP_PT_details",
            "UECP_PT_recovery", "UECP_PT_developer",
            "UECP_OT_check_and_preview", "UECP_OT_locate_issue", "UECP_OT_load_details",
        ):
            self.assertTrue(hasattr(bpy.types, name), name)

    def test_developer_diagnostics_default_hidden(self):
        from ue_chain_prep.ui.preferences import UECP_AddonPreferences as prefs_type
        prop = prefs_type.bl_rna.properties["enable_developer_diagnostics"]
        self.assertFalse(prop.default)

    def test_analyze_keeps_rna_lists_lazy_until_requested(self):
        rig = make_chain(count=3)
        make_bound_mesh(rig)
        result = bpy.ops.uecp.analyze()
        self.assertEqual({"FINISHED"}, result)
        wm = bpy.context.window_manager
        self.assertEqual(0, len(wm.uecp_proposal_items))
        self.assertFalse(wm.uecp_runtime.details_loaded)
        from ue_chain_prep.core.runtime_store import get_performance
        metrics = get_performance(wm.uecp_runtime.plan_id)
        self.assertIn("tracemalloc_peak", metrics)
        self.assertIn("preview_build_time", metrics)
        self.assertEqual(0, metrics["ui_item_count"])
        self.assertEqual({"FINISHED"}, bpy.ops.uecp.load_details())
        self.assertTrue(wm.uecp_runtime.details_loaded)
        self.assertGreater(len(wm.uecp_chain_items), 0)
        self.assertLessEqual(len(wm.uecp_proposal_items), 200)

    def test_issue_list_does_not_render_raw_issue_code(self):
        source = (Path(__file__).resolve().parents[1] / "ue_chain_prep" / "ui" / "lists.py").read_text(encoding="utf-8")
        self.assertNotIn("item.code", source)


if __name__ == "__main__":
    unittest.main()
