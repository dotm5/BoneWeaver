"""Explicit selection and Analyze-scope acceptance for hierarchy inspection."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.hierarchy_inspection import HierarchyInspectionController


class UECP_OT_select_inspected_scope(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["select_inspected_scope"]
    bl_label = "Select Inspected Scope"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.hierarchy_inspection_active)

    def execute(self, context):
        try:
            HierarchyInspectionController.select_scope(context)
        except (RuntimeError, ValueError, KeyError) as exc:
            context.window_manager.uecp_runtime.last_error = str(exc)
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class UECP_OT_use_inspected_scope(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["use_inspected_scope"]
    bl_label = "Use Inspected Scope"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.hierarchy_inspection_active)

    def execute(self, context):
        try:
            HierarchyInspectionController.use_scope(context)
        except (RuntimeError, ValueError, KeyError) as exc:
            context.window_manager.uecp_runtime.last_error = str(exc)
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}
