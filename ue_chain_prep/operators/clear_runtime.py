"""Clear transient plan/UI state without modifying Blender scene data."""

import bpy

from ..contracts import OPERATOR_IDS, PlanState


class UECP_OT_clear_runtime(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["clear_runtime"]
    bl_label = "Clear UECP Runtime"

    def execute(self, context):
        runtime = context.window_manager.uecp_runtime
        runtime.state = PlanState.IDLE.value
        runtime.plan_id = ""
        runtime.plan_fingerprint = ""
        runtime.plan_summary = ""
        runtime.issue_count_info = 0
        runtime.issue_count_warning = 0
        runtime.issue_count_blocker = 0
        runtime.preview_enabled = False
        runtime.last_error = ""
        runtime.is_busy = False
        return {"FINISHED"}
