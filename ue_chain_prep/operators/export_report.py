"""Diagnostic report export operator shell."""

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from ..contracts import OPERATOR_IDS
from ..core.runtime_store import get_report
from ..core.serialization import dumps


class UECP_OT_export_report(bpy.types.Operator, ExportHelper):
    bl_idname = OPERATOR_IDS["export_report"]
    bl_label = "Export UECP Diagnostic Report"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    include_plan: BoolProperty(default=True)
    include_weight_stats: BoolProperty(default=True)
    include_snapshot_summary: BoolProperty(default=True)

    def execute(self, context):
        report = get_report()
        if report is None:
            return {"CANCELLED"}
        with open(self.filepath, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(dumps(report))
        context.scene.uecp_settings.last_export_directory = str(__import__("pathlib").Path(self.filepath).parent)
        return {"FINISHED"}
