"""Explicit read-only semantic discovery operator."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)
from ..controllers.selection import SelectionController


class UECP_OT_discover_secondary_chains(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["discover_secondary_chains"]
    bl_label = "Discover Secondary Chains"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        armature, _source = SelectionController.armature_from_context(context)
        return bool(runtime and not runtime.is_busy and armature is not None)

    def execute(self, context):
        try:
            SemanticDiscoveryController.discover(context)
        except SemanticDiscoveryRuntimeError as exc:
            context.window_manager.uecp_runtime.last_error = str(exc)
            return {"CANCELLED"}
        except Exception:
            context.window_manager.uecp_runtime.last_error = "UECP_INTERNAL_ERROR"
            return {"CANCELLED"}
        return {"FINISHED"}
