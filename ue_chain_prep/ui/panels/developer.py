"""Opt-in raw diagnostics for maintainers."""

import bpy

from ...contracts import ADDON_ID, ALGORITHM_VERSION, OPERATOR_IDS, SCHEMA_VERSION


class UECP_PT_developer(bpy.types.Panel):
    bl_idname = "UECP_PT_developer"
    bl_label = "开发者诊断"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        addon = context.preferences.addons.get(ADDON_ID)
        return bool(addon and addon.preferences.enable_developer_diagnostics)

    def draw(self, context):
        layout = self.layout
        runtime = context.window_manager.uecp_runtime
        layout.label(text=f"Plan State: {runtime.state}")
        layout.label(text=f"Plan ID: {runtime.plan_id or '-'}")
        layout.label(text=f"Source Fingerprint: {runtime.plan_fingerprint or '-'}")
        layout.label(text=f"Algorithm: {ALGORITHM_VERSION}")
        layout.label(text=f"Schema: {SCHEMA_VERSION}")
        if runtime.last_error:
            layout.label(text=runtime.last_error, icon="ERROR")
        layout.operator(OPERATOR_IDS["export_report"], icon="EXPORT")
        layout.operator(OPERATOR_IDS["clear_runtime"], icon="FILE_REFRESH")
