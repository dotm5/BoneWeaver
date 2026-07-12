"""Explicitly materialize capped RNA detail lists outside panel draw context."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.session import SessionController


class BONEWEAVER_OT_load_details(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["load_details"]
    bl_label = "加载结果详情"

    def execute(self, context):
        return {"FINISHED"} if SessionController.populate_details(context) else {"CANCELLED"}
