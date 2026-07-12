"""Natural-language result details with explicit lazy RNA materialization."""

import bpy

from ...contracts import OPERATOR_IDS
from ..view_model import details_panel_view_from_context


class BONEWEAVER_PT_details(bpy.types.Panel):
    bl_idname = "BONEWEAVER_PT_details"
    bl_label = "结果详情"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneWeaver"
    bl_parent_id = "BONEWEAVER_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        view = details_panel_view_from_context(context)
        layout.label(text=f"{view.chain_count} 条链 · {view.bone_count} 根骨骼")
        layout.label(text=f"需要处理：{view.blocker_count} · 建议确认：{view.warning_count}")
        if not view.details_loaded:
            layout.operator(OPERATOR_IDS["load_details"], icon="PRESET")
            return
        if view.has_chains:
            layout.template_list("BONEWEAVER_UL_chains", "", view.window_manager, "boneweaver_chain_items", view.active_data, "active_chain_index", rows=3)
        if view.has_issues:
            layout.template_list("BONEWEAVER_UL_issues", "", view.window_manager, "boneweaver_issue_items", view.active_data, "active_issue_index", rows=4)
            if view.selected_issue_bone:
                op = layout.operator(OPERATOR_IDS["locate_issue"], text=f"定位：{view.selected_issue_bone}", icon="VIEWZOOM")
                op.issue_index = view.active_issue_index
                op.bone_name = view.selected_issue_bone
        if view.has_proposals:
            layout.template_list("BONEWEAVER_UL_proposals", "", view.window_manager, "boneweaver_proposal_items", view.active_data, "active_proposal_index", rows=4)
