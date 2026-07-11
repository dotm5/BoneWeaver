"""Thin Analyze operator adapter."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.workflow import WorkflowController


class UECP_OT_analyze(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["analyze"]
    bl_label = "Analyze UE Bone Chains"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return WorkflowController.can_analyze(context)

    def execute(self, context):
        return WorkflowController.analyze(context, auto_preview=False)
