"""Diagnostic report export operator shell."""

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from ..contracts import OPERATOR_IDS


class UECP_OT_export_report(bpy.types.Operator, ExportHelper):
    bl_idname = OPERATOR_IDS["export_report"]
    bl_label = "Export UECP Diagnostic Report"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    include_plan: BoolProperty(default=True)
    include_weight_stats: BoolProperty(default=True)
    include_snapshot_summary: BoolProperty(default=True)

    def execute(self, context):
        self.report({"ERROR"}, "No diagnostic report is available")
        return {"CANCELLED"}
