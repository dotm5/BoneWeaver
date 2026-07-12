from __future__ import annotations

import unittest

from boneweaver.contracts import PlanAvailability, PlanState, WorkflowStage
from boneweaver.ui.view_model import (
    BlenderContextSummary,
    RuntimeSummary,
    SnapshotSummary,
    derive_panel_view_state,
)


class PanelViewModelTests(unittest.TestCase):
    def _derive(self, *, context=None, runtime=None, availability=PlanAvailability.NONE,
                selection="sel-a", settings="settings-a", snapshot=None):
        return derive_panel_view_state(
            context or BlenderContextSummary("Rig", 6, 1, "BoneX · 稳定旋转链", "ARMATURE", selection),
            runtime or RuntimeSummary(state=PlanState.IDLE.value),
            availability,
            selection,
            settings,
            snapshot or SnapshotSummary(),
        )

    def test_no_context_has_no_primary_action(self):
        view = self._derive(context=BlenderContextSummary(None, 0, None, "BoneX · 稳定旋转链", "NONE", ""))
        self.assertEqual(WorkflowStage.NO_CONTEXT.value, view.workflow_stage)
        self.assertIsNone(view.primary_action)
        self.assertIn("未找到", view.notice_lines[0])

    def test_idle_context_is_ready_to_analyze(self):
        view = self._derive()
        self.assertEqual(WorkflowStage.READY_TO_ANALYZE.value, view.workflow_stage)
        self.assertEqual("boneweaver.check_and_preview", view.primary_action.operator_id)
        self.assertEqual("检查并预览", view.primary_action.label)
        self.assertTrue(view.primary_action.enabled)

    def test_ready_warning_and_blocker_are_distinct(self):
        ready = self._derive(runtime=RuntimeSummary(
            state=PlanState.ANALYZED.value, plan_id="p", selection_signature="sel-a",
            settings_signature="settings-a", bone_count=6, chain_count=1,
        ), availability=PlanAvailability.AVAILABLE)
        warning = self._derive(runtime=RuntimeSummary(
            state=PlanState.ANALYZED.value, plan_id="p", selection_signature="sel-a",
            settings_signature="settings-a", bone_count=6, chain_count=1, warning_count=1,
        ), availability=PlanAvailability.AVAILABLE)
        blocked = self._derive(runtime=RuntimeSummary(
            state=PlanState.ANALYZED.value, plan_id="p", selection_signature="sel-a",
            settings_signature="settings-a", bone_count=6, chain_count=1, blocker_count=2,
        ), availability=PlanAvailability.AVAILABLE)
        self.assertEqual(WorkflowStage.READY_TO_APPLY.value, ready.workflow_stage)
        self.assertEqual("boneweaver.apply", ready.primary_action.operator_id)
        self.assertEqual(WorkflowStage.NEEDS_ATTENTION.value, warning.workflow_stage)
        self.assertEqual("boneweaver.apply", warning.primary_action.operator_id)
        self.assertEqual(WorkflowStage.BLOCKED.value, blocked.workflow_stage)
        self.assertNotEqual("boneweaver.apply", blocked.primary_action.operator_id)
        self.assertIn("不能转换", blocked.result.title)

    def test_stale_settings_selection_and_lost_plan_have_recheck_action(self):
        base = dict(state=PlanState.ANALYZED.value, plan_id="p", selection_signature="sel-a",
                    settings_signature="settings-a", bone_count=6, chain_count=1)
        stale_settings = self._derive(runtime=RuntimeSummary(**base), availability=PlanAvailability.AVAILABLE,
                                      settings="settings-b")
        stale_selection = self._derive(runtime=RuntimeSummary(**base), availability=PlanAvailability.AVAILABLE,
                                       selection="sel-b")
        lost = self._derive(runtime=RuntimeSummary(**base), availability=PlanAvailability.MISSING)
        lost_after_apply = self._derive(runtime=RuntimeSummary(
            **{**base, "state": PlanState.RESTORABLE.value}
        ), availability=PlanAvailability.MISSING, snapshot=SnapshotSummary(True, "BONEWEAVER_SNAPSHOT::1", 6))
        self.assertEqual(WorkflowStage.STALE_SETTINGS.value, stale_settings.workflow_stage)
        self.assertEqual(WorkflowStage.STALE_SELECTION.value, stale_selection.workflow_stage)
        self.assertEqual(WorkflowStage.PLAN_LOST.value, lost.workflow_stage)
        self.assertEqual(WorkflowStage.PLAN_LOST.value, lost_after_apply.workflow_stage)
        for view in (stale_settings, stale_selection, lost, lost_after_apply):
            self.assertEqual("boneweaver.check_and_preview", view.primary_action.operator_id)
            self.assertEqual("重新检查", view.primary_action.label)

        stale_source = self._derive(runtime=RuntimeSummary(
            **{**base, "state": PlanState.STALE.value}, last_error="BONEWEAVER_STATE_CHANGED_AFTER_ANALYZE"
        ), availability=PlanAvailability.AVAILABLE)
        self.assertEqual(WorkflowStage.STALE_SELECTION.value, stale_source.workflow_stage)
        self.assertEqual("boneweaver.check_and_preview", stale_source.primary_action.operator_id)

    def test_busy_applied_rollback_and_error_states_are_explainable(self):
        analyzing = self._derive(runtime=RuntimeSummary(state=PlanState.IDLE.value, is_busy=True))
        applying = self._derive(runtime=RuntimeSummary(state=PlanState.APPLYING.value, is_busy=True))
        applied = self._derive(runtime=RuntimeSummary(state=PlanState.RESTORABLE.value, bone_count=6),
                               snapshot=SnapshotSummary(True, "BONEWEAVER_SNAPSHOT::1", 6))
        rollback = self._derive(runtime=RuntimeSummary(state=PlanState.ERROR.value, last_error="BONEWEAVER_ROLLBACK_FAILED"))
        error = self._derive(runtime=RuntimeSummary(state=PlanState.ERROR.value, last_error="BONEWEAVER_INTERNAL_ERROR"))
        self.assertEqual(WorkflowStage.ANALYZING.value, analyzing.workflow_stage)
        self.assertFalse(analyzing.primary_action.enabled)
        self.assertEqual(WorkflowStage.APPLYING.value, applying.workflow_stage)
        self.assertEqual(WorkflowStage.APPLIED.value, applied.workflow_stage)
        self.assertTrue(applied.snapshot_available)
        self.assertEqual(WorkflowStage.ROLLBACK_FAILED.value, rollback.workflow_stage)
        self.assertEqual(WorkflowStage.ERROR.value, error.workflow_stage)


if __name__ == "__main__":
    unittest.main()
