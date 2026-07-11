"""Thin diagnostic report export adapter."""

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..contracts import OPERATOR_IDS
from ..controllers.export import ExportController


class UECP_OT_export_report(bpy.types.Operator, ExportHelper):
    bl_idname = OPERATOR_IDS["export_report"]
    bl_label = "Export UECP Diagnostic Report"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        return ExportController.export_report(context, self.filepath)
