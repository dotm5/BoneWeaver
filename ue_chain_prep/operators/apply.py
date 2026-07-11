"""Apply operator shell."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS, PlanState


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
        self.report({"ERROR"}, "No executable conversion transaction is available")
        return {"CANCELLED"}
