"""Thin conversion-copy export adapter."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.export import ExportController


class BONEWEAVER_OT_export_conversion(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["export_conversion"]
    bl_label = "Export Converted Copy"

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        return ExportController.export_conversion(context, self.filepath)
