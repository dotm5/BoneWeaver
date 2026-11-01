from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
        self.assertIn('"boneweaver.auto_cleanup"', source)
        self.assertIn('"boneweaver.restore_auto_cleanup"', source)
        for mode, label in (
            ("AUTO", "全自动整理"), ("REORIENT", "仅父子重定向"),
            ("CONNECT", "仅连接骨链"), ("CLEANUP", "仅清理辅助骨"),
        ):
            self.assertIn(f'"{mode}"', source)
            self.assertIn(label, source)
        self.assertNotIn('OPERATOR_IDS["quick_reorient_auto"]', source)
        legacy = (path.parent / "legacy.py").read_text(encoding="utf-8")
        for mode in ("quick_reorient_auto", "quick_reorient_links_only", "quick_reorient_hybrid_auto"):
            self.assertIn(f'OPERATOR_IDS["{mode}"]', legacy)

    def test_main_panel_buttons_dispatch_modes(self):
        from boneweaver.ui.panels.main import BONEWEAVER_PT_main

        class FakeLayout:
            def __init__(self):
                self.buttons = []

            def box(self):
                return self

            def row(self):
                return self

            def label(self, **kwargs):
                pass

            def operator(self, operator_id, **kwargs):
                properties = SimpleNamespace()
                self.buttons.append((operator_id, kwargs["text"], properties))
                return properties

        layout = FakeLayout()
        view = SimpleNamespace(target=SimpleNamespace(armature_name="Rig", source_kind=""))
        context = SimpleNamespace(window_manager=SimpleNamespace(
            boneweaver_runtime=SimpleNamespace(quick_summary="")))
        with patch("boneweaver.ui.panels.main.panel_view_state_from_context", return_value=view), \
             patch("boneweaver.ui.panels.main.AutoCleanupController.can_run", return_value=True), \
             patch("boneweaver.ui.panels.main.AutoCleanupController.can_restore", return_value=False):
            BONEWEAVER_PT_main.draw(SimpleNamespace(layout=layout), context)
        self.assertEqual([
            ("boneweaver.auto_cleanup", "全自动整理", "AUTO"),
            ("boneweaver.auto_cleanup", "仅父子重定向", "REORIENT"),
            ("boneweaver.auto_cleanup", "仅连接骨链", "CONNECT"),
            ("boneweaver.auto_cleanup", "仅清理辅助骨", "CLEANUP"),
        ], [(op, label, props.mode) for op, label, props in layout.buttons])

    def test_auto_cleanup_operator_modes_and_dispatch(self):
        from boneweaver.operators.auto_cleanup import BONEWEAVER_OT_auto_cleanup
        prop = bpy.ops.boneweaver.auto_cleanup.get_rna_type().properties["mode"]
        self.assertEqual("AUTO", prop.default)
        self.assertEqual({"AUTO", "REORIENT", "CONNECT", "CLEANUP"},
                         {item.identifier for item in prop.enum_items})
        context = SimpleNamespace(window_manager=SimpleNamespace(
            boneweaver_runtime=SimpleNamespace(quick_summary="done")))
        for mode in ("AUTO", "REORIENT", "CONNECT", "CLEANUP"):
            operator = SimpleNamespace(mode=mode, report=lambda *args: None)
            with patch("boneweaver.operators.auto_cleanup.AutoCleanupController.run", return_value=True) as run:
                self.assertEqual({"FINISHED"}, BONEWEAVER_OT_auto_cleanup.execute(operator, context))
                run.assert_called_once_with(context, mode=mode)
        description = BONEWEAVER_OT_auto_cleanup.description(None, SimpleNamespace(mode="CONNECT"))
        self.assertIn("已对齐", description)
        self.assertIn("不重定向或删除", description)

    def test_advanced_panel_hierarchy_and_registration_order(self):
        from boneweaver.ui.panels import PANEL_CLASSES
        from boneweaver.ui.preferences import ADDON_ID
        names = [cls.bl_idname for cls in PANEL_CLASSES]
        self.assertEqual("BONEWEAVER_PT_main", names[0])
        self.assertLess(names.index("BONEWEAVER_PT_main"), names.index("BONEWEAVER_PT_advanced"))
        for cls in PANEL_CLASSES:
            if cls.bl_idname not in {"BONEWEAVER_PT_main", "BONEWEAVER_PT_advanced"}:
                self.assertEqual("BONEWEAVER_PT_advanced", cls.bl_parent_id)
                self.assertLess(names.index("BONEWEAVER_PT_advanced"), names.index(cls.bl_idname))
        advanced = PANEL_CLASSES[names.index("BONEWEAVER_PT_advanced")]
        self.assertEqual("BONEWEAVER_PT_main", advanced.bl_parent_id)
        self.assertIn("DEFAULT_CLOSED", advanced.bl_options)
        self.assertEqual(boneweaver.__package__, ADDON_ID)
        source = (Path(__file__).resolve().parents[1] / "boneweaver" / "ui" / "panels" / "advanced.py").read_text(encoding="utf-8")
        self.assertIn('"enable_developer_diagnostics"', source)

    def test_quick_reorient_is_a_true_single_click_action(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "boneweaver"
            / "operators"
            / "quick_reorient.py"
        )
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("invoke_confirm", source)
        self.assertEqual(source.count("return self.execute(context)"), 3)

    def test_panel_layers_and_primary_operators_are_registered(self):
        for name in (
            "BONEWEAVER_PT_main", "BONEWEAVER_PT_advanced", "BONEWEAVER_PT_legacy", "BONEWEAVER_PT_details",
            "BONEWEAVER_PT_recovery", "BONEWEAVER_PT_developer",
            "BONEWEAVER_OT_check_and_preview", "BONEWEAVER_OT_locate_issue", "BONEWEAVER_OT_load_details",
            "BONEWEAVER_OT_auto_cleanup", "BONEWEAVER_OT_restore_auto_cleanup",
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
