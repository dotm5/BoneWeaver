"""Snapshot restore operator shell."""

import bpy
from bpy.props import BoolProperty, StringProperty

from ..contracts import OPERATOR_IDS
from ..contracts import PlanState
from ..core.restore import restore_snapshot


class UECP_OT_restore_snapshot(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["restore_snapshot"]
    bl_label = "Restore UECP Snapshot"
    bl_options = {"REGISTER", "UNDO"}

    snapshot_text_name: StringProperty()
    allow_partial: BoolProperty(default=False)

    def execute(self, context):
        runtime = context.window_manager.uecp_runtime
        text_name = self.snapshot_text_name or runtime.snapshot_text_name
        success, error = restore_snapshot(context, text_name)
        if not success:
            runtime.last_error = error
            return {"CANCELLED"}
        runtime.state = PlanState.RESTORED.value
        runtime.last_error = ""
        return {"FINISHED"}
