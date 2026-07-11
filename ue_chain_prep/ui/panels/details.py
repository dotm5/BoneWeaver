"""Natural-language result details with explicit lazy RNA materialization."""

import bpy

from ...contracts import OPERATOR_IDS


class UECP_PT_details(bpy.types.Panel):
    bl_idname = "UECP_PT_details"
    bl_label = "结果详情"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        runtime = context.window_manager.uecp_runtime
        layout.label(text=f"{runtime.plan_chain_count} 条链 · {runtime.plan_bone_count} 根骨骼")
        layout.label(text=f"需要处理：{runtime.issue_count_blocker} · 建议确认：{runtime.issue_count_warning}")
        if not runtime.details_loaded:
            layout.operator(OPERATOR_IDS["load_details"], icon="PRESET")
            return
        wm = context.window_manager
        if wm.uecp_chain_items:
            layout.template_list("UECP_UL_chains", "", wm, "uecp_chain_items", runtime, "active_chain_index", rows=3)
        if wm.uecp_issue_items:
            layout.template_list("UECP_UL_issues", "", wm, "uecp_issue_items", runtime, "active_issue_index", rows=4)
            item = wm.uecp_issue_items[min(runtime.active_issue_index, len(wm.uecp_issue_items) - 1)]
            if item.bone_name:
                op = layout.operator(OPERATOR_IDS["locate_issue"], icon="VIEWZOOM")
                op.issue_index = runtime.active_issue_index
                op.bone_name = item.bone_name
        if wm.uecp_proposal_items:
            layout.template_list("UECP_UL_proposals", "", wm, "uecp_proposal_items", runtime, "active_proposal_index", rows=4)
