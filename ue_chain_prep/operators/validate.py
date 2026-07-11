"""Thin validation adapter; validation scope is intentionally not exposed."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.workflow import WorkflowController


class UECP_OT_validate(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["validate"]
    bl_label = "重新验证当前状态"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return WorkflowController.validate(context)
