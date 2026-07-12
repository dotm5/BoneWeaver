"""Primary user action combining read-only analysis and preview."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.workflow import WorkflowController


class BONEWEAVER_OT_check_and_preview(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["check_and_preview"]
    bl_label = "检查并预览"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return WorkflowController.can_analyze(context)

    def execute(self, context):
        return WorkflowController.analyze(context, auto_preview=True)
