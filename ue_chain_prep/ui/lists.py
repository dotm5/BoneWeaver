"""Compact chain, proposal, and issue UI lists."""

import bpy


class UECP_UL_chains(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=f"{item.root_name} → {item.leaf_name}", icon="BONE_DATA")


class UECP_UL_proposals(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=f"{item.bone_name} · {item.role}", icon="CON_BONE")


class UECP_UL_issues(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        issue_icon = "ERROR" if item.severity == "BLOCKER" else ("INFO" if item.severity == "INFO" else "QUESTION")
        layout.label(text=item.message, icon=issue_icon)


UI_LIST_CLASSES = (UECP_UL_chains, UECP_UL_proposals, UECP_UL_issues)
