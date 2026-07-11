"""Thin snapshot restore adapter."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.workflow import WorkflowController


class UECP_OT_restore_snapshot(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["restore_snapshot"]
    bl_label = "恢复转换前状态"
    bl_options = {"REGISTER", "UNDO"}

    snapshot_text_name: StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(runtime and runtime.snapshot_text_name and not runtime.is_busy)

    def execute(self, context):
        return WorkflowController.restore(context, self.snapshot_text_name)
