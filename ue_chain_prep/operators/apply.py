"""Apply operator shell."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS, PlanState
from ..core.apply_transaction import apply_plan
from ..core.fingerprint import current_source_fingerprint, settings_fingerprint
from ..core.runtime_store import get_plan, has_plan


class UECP_OT_apply(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["apply"]
    bl_label = "Apply Chain Conversion"
    bl_options = {"REGISTER", "UNDO"}

    plan_id: StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(
            runtime
            and not runtime.is_busy
            and runtime.state == PlanState.ANALYZED.value
            and runtime.issue_count_blocker == 0
            and runtime.plan_id
        )

    def execute(self, context):
        runtime = context.window_manager.uecp_runtime
        requested = self.plan_id or runtime.plan_id
        if requested != runtime.plan_id or not has_plan(requested):
            runtime.state = PlanState.STALE.value
            return {"CANCELLED"}
        plan = get_plan(requested)
        if current_source_fingerprint(context, plan) != plan.source_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "UECP_STATE_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        if settings_fingerprint(context.scene.uecp_settings) != plan.settings_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "UECP_SETTINGS_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        runtime.is_busy = True
        runtime.state = PlanState.APPLYING.value
        try:
            result = apply_plan(context, plan)
            runtime.snapshot_id = result.snapshot_id
            runtime.snapshot_text_name = result.snapshot_text_name
            if result.success:
                runtime.state = PlanState.RESTORABLE.value
                runtime.last_error = ""
                return {"FINISHED"}
            runtime.state = PlanState.ANALYZED.value if result.rolled_back else PlanState.ERROR.value
            runtime.last_error = result.error or "UECP_INTERNAL_ERROR"
            return {"CANCELLED"}
        finally:
            runtime.is_busy = False
