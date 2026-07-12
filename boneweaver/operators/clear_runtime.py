"""Thin session reset adapter; persistent snapshots are never deleted."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.session import SessionController


class BONEWEAVER_OT_clear_runtime(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["clear_runtime"]
    bl_label = "重置本次会话"

    def execute(self, context):
        SessionController.reset_session(context)
        return {"FINISHED"}
