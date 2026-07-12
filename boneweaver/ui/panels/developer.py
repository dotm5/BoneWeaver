"""Opt-in raw diagnostics for maintainers."""

import bpy

from ...contracts import ADDON_ID, ALGORITHM_VERSION, OPERATOR_IDS, SCHEMA_VERSION
from ..view_model import developer_panel_view_from_context


class BONEWEAVER_PT_developer(bpy.types.Panel):
    bl_idname = "BONEWEAVER_PT_developer"
    bl_label = "开发者诊断"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneWeaver"
    bl_parent_id = "BONEWEAVER_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        addon = context.preferences.addons.get(ADDON_ID)
        return bool(addon and addon.preferences.enable_developer_diagnostics)

    def draw(self, context):
        layout = self.layout
        view = developer_panel_view_from_context(context)
        layout.label(text=f"Plan State: {view.plan_state}")
        layout.label(text=f"Plan ID: {view.plan_id or '-'}")
        layout.label(text=f"Source Fingerprint: {view.source_fingerprint or '-'}")
        layout.label(text=f"Algorithm: {ALGORITHM_VERSION}")
        layout.label(text=f"Schema: {SCHEMA_VERSION}")
        if view.last_error:
            layout.label(text=view.last_error, icon="ERROR")
        layout.operator(OPERATOR_IDS["export_report"], icon="EXPORT")
        layout.operator(OPERATOR_IDS["clear_runtime"], icon="FILE_REFRESH")
