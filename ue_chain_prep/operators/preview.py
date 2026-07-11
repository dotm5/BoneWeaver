"""Thin preview toggle adapter."""

import bpy

from ..contracts import OPERATOR_IDS, PlanState
from ..controllers.preview import PreviewController


class UECP_OT_preview_toggle(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["preview_toggle"]
    bl_label = "显示/隐藏预览"

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(runtime and runtime.state in {PlanState.ANALYZED.value, PlanState.RESTORABLE.value})

    def execute(self, context):
        PreviewController.toggle(context)
        return {"FINISHED"}
