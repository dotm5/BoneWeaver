"""Export the current immutable semantic plan as strict JSON."""

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..contracts import OPERATOR_IDS
from ..controllers.semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)


class BONEWEAVER_OT_export_semantic_discovery(bpy.types.Operator, ExportHelper):
    bl_idname = OPERATOR_IDS["export_semantic_discovery"]
    bl_label = "Export Semantic Discovery"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.semantic_discovery_active)

    def execute(self, context):
        try:
            SemanticDiscoveryController.export_json(context, self.filepath)
        except SemanticDiscoveryRuntimeError as exc:
            context.window_manager.boneweaver_runtime.last_error = str(exc)
            return {"CANCELLED"}
        except OSError:
            context.window_manager.boneweaver_runtime.last_error = "BONEWEAVER_SEMANTIC_EXPORT_FAILED"
            return {"CANCELLED"}
        context.window_manager.boneweaver_runtime.last_error = ""
        return {"FINISHED"}
