from __future__ import annotations

import unittest
import ast
from pathlib import Path

import bpy

import ue_chain_prep
from tests.fixture_builders import clear_scene, make_chain
from ue_chain_prep.controllers.preview import PreviewController
from ue_chain_prep.controllers.selection import SelectionController
from ue_chain_prep.controllers.session import SessionController
from ue_chain_prep.core.runtime_store import has_plan, put_plan
from ue_chain_prep.core.planner import build_plan


class ControllerLifecycleTests(unittest.TestCase):
    def setUp(self):
        ue_chain_prep.unregister()
        clear_scene()
        ue_chain_prep.register()

    def tearDown(self):
        ue_chain_prep.unregister()
        clear_scene()

    def test_preview_controller_is_single_runtime_state_owner(self):
        runtime = bpy.context.window_manager.uecp_runtime
        cache = (((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.2, 0.8, 1.0, 1.0)),)
        PreviewController.enable(bpy.context, cache)
        self.assertTrue(PreviewController.is_enabled())
        self.assertTrue(runtime.preview_enabled)
        PreviewController.disable(bpy.context)
        self.assertFalse(PreviewController.is_enabled())
        self.assertFalse(runtime.preview_enabled)

    def test_clear_analysis_resets_transient_state_but_preserves_snapshot(self):
        runtime = bpy.context.window_manager.uecp_runtime
        runtime.plan_id = "missing-plan"
        runtime.plan_summary = "summary"
        runtime.snapshot_id = "snapshot-1"
        runtime.snapshot_text_name = "UECP_SNAPSHOT::snapshot-1"
        runtime.active_chain_index = 4
        runtime.active_proposal_index = 5
        runtime.active_issue_index = 6
        bpy.context.window_manager.uecp_issue_items.add().message = "issue"
        SessionController.clear_analysis(bpy.context)
        self.assertEqual("", runtime.plan_id)
        self.assertEqual("", runtime.plan_summary)
        self.assertEqual(0, len(bpy.context.window_manager.uecp_issue_items))
        self.assertEqual(0, runtime.active_issue_index)
        self.assertEqual("snapshot-1", runtime.snapshot_id)
        self.assertEqual("UECP_SNAPSHOT::snapshot-1", runtime.snapshot_text_name)

    def test_load_and_undo_invalidate_plan_and_preview_without_deleting_snapshot(self):
        runtime = bpy.context.window_manager.uecp_runtime
        runtime.plan_id = "old-plan"
        runtime.snapshot_text_name = "UECP_SNAPSHOT::1"
        PreviewController.enable(bpy.context, (((0, 0, 0), (0, 1, 0), (1, 1, 1, 1)),))
        SessionController.invalidate_for_scene_change(bpy.context, "undo_redo")
        self.assertEqual("old-plan", runtime.plan_id)
        self.assertEqual("UECP_SNAPSHOT::1", runtime.snapshot_text_name)
        self.assertFalse(PreviewController.is_enabled())
        self.assertEqual("UECP_SCENE_CHANGED_RECHECK", runtime.last_error)

    def test_selection_signature_changes_with_selected_bone_set(self):
        rig = make_chain(count=3)
        first = SelectionController.signature(bpy.context)
        rig.pose.bones[2].select = False
        second = SelectionController.signature(bpy.context)
        self.assertNotEqual(first, second)
        self.assertEqual(first, SelectionController.signature(bpy.context, bone_names=("Bone_0", "Bone_1", "Bone_2")))

    def test_registration_owns_load_undo_redo_handlers(self):
        self.assertIn(SessionController.on_load_pre, bpy.app.handlers.load_pre)
        self.assertIn(SessionController.on_load_post, bpy.app.handlers.load_post)
        self.assertIn(SessionController.on_undo_post, bpy.app.handlers.undo_post)
        self.assertIn(SessionController.on_redo_post, bpy.app.handlers.redo_post)
        ue_chain_prep.unregister()
        self.assertNotIn(SessionController.on_load_pre, bpy.app.handlers.load_pre)
        self.assertNotIn(SessionController.on_undo_post, bpy.app.handlers.undo_post)

    def test_workflow_operators_do_not_assign_runtime_fields(self):
        root = Path(__file__).resolve().parents[1] / "ue_chain_prep" / "operators"
        offenders = []
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                targets = node.targets if isinstance(node, ast.Assign) else ([node.target] if isinstance(node, ast.AnnAssign) else [])
                for target in targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "runtime":
                        offenders.append(f"{path.name}:{target.attr}")
        self.assertEqual([], offenders)

    def test_algorithm_setting_stales_plan_but_preview_setting_does_not(self):
        rig = make_chain(count=3)
        from tests.fixture_builders import make_bound_mesh
        make_bound_mesh(rig)
        self.assertEqual({"FINISHED"}, bpy.ops.uecp.check_and_preview())
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertTrue(PreviewController.is_enabled())
        bpy.context.scene.uecp_settings.preview_axis_scale *= 1.1
        self.assertEqual("ANALYZED", runtime.state)
        self.assertTrue(PreviewController.is_enabled())
        bpy.context.scene.uecp_settings.minimum_weight += 0.01
        self.assertEqual("STALE", runtime.state)
        self.assertFalse(PreviewController.is_enabled())
        self.assertEqual("UECP_SETTINGS_CHANGED_AFTER_ANALYZE", runtime.last_error)


if __name__ == "__main__":
    unittest.main()
