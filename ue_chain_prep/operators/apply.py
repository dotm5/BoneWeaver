"""Thin Apply operator adapter with explicit user confirmation."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.workflow import WorkflowController


class UECP_OT_apply(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["apply"]
    bl_label = "应用转换"
    bl_options = {"REGISTER", "UNDO"}

    plan_id: StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return WorkflowController.can_apply(context)

    def invoke(self, context, event):
        count = context.window_manager.uecp_runtime.plan_bone_count
        message = f"将调整 {count} 根骨骼的方向与连接方式；不会修改网格、权重、骨名或父子层级。"
        try:
            return context.window_manager.invoke_confirm(self, event, title="应用 UE Chain Prep 转换", message=message)
        except TypeError:
            return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        return WorkflowController.apply(context, self.plan_id)
