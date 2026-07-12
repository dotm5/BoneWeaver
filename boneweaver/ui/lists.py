"""Compact chain, proposal, and issue UI lists."""

import bpy

from .issue_presenter import issue_summary


class BONEWEAVER_UL_chains(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=f"{item.root_name} → {item.leaf_name}", icon="BONE_DATA")


class BONEWEAVER_UL_proposals(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=f"{item.bone_name} · {item.role}", icon="CON_BONE")


class BONEWEAVER_UL_issues(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        issue_icon = "ERROR" if item.severity == "BLOCKER" else ("INFO" if item.severity == "INFO" else "QUESTION")
        layout.label(text=issue_summary(item.code, item.message, item.bone_name), icon=issue_icon)


UI_LIST_CLASSES = (BONEWEAVER_UL_chains, BONEWEAVER_UL_proposals, BONEWEAVER_UL_issues)
