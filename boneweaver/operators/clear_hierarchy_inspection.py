"""Discard only transient hierarchy inspection and its accepted scope."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.hierarchy_inspection import HierarchyInspectionController


class BONEWEAVER_OT_clear_hierarchy_inspection(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["clear_hierarchy_inspection"]
    bl_label = "Clear Hierarchy Inspection"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.hierarchy_inspection_active)

    def execute(self, context):
        HierarchyInspectionController.clear(context)
        return {"FINISHED"}
