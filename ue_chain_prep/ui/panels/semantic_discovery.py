"""Minimal explicit-confirmation UI for semantic chain discovery."""

import bpy

from ...contracts import OPERATOR_IDS


class UECP_PT_semantic_discovery(bpy.types.Panel):
    bl_idname = "UECP_PT_semantic_discovery"
    bl_label = "Semantic Chain Discovery"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        runtime = wm.uecp_runtime

        layout.operator(
            OPERATOR_IDS["discover_secondary_chains"],
            text="发现次级骨链（只读）",
            icon="VIEWZOOM",
        )
        if not runtime.semantic_discovery_active:
            layout.label(text="发现不会修改选择，也不会自动分析", icon="INFO")
            return

        summary = layout.box()
        summary.label(text=f"候选链：{runtime.semantic_chain_count}")
        summary.label(text=f"已确认：{runtime.semantic_confirmed_count}")
        if runtime.semantic_scope_used:
            summary.label(text="确认链已冻结给下一次 Analyze", icon="LOCKED")
        summary.label(text="AUTO 也必须点击确认；分叉不会自动选主路径", icon="ERROR")

        for item in wm.uecp_semantic_chain_items:
            box = layout.box()
            header = box.row(align=True)
            header.label(text=item.root_name, icon="BONE_DATA")
            header.label(text=f"{item.category} · {item.discovery_class}")
            header.label(text=f"{item.discovery_score:.2f}")
            box.label(text=f"分叉：{item.branch_count}")
            if item.reason_codes:
                box.label(text=f"理由：{item.reason_codes}")
            operator = box.operator(
                OPERATOR_IDS["select_discovered_chain"],
                text="已确认 · 重新选择" if item.confirmed else "确认并仅选择此链",
                icon="CHECKMARK" if item.confirmed else "RESTRICT_SELECT_OFF",
            )
            operator.chain_id = item.chain_id

        row = layout.row(align=True)
        use = row.row(align=True)
        use.enabled = runtime.semantic_confirmed_count > 0
        use.operator(
            OPERATOR_IDS["use_discovered_chains"],
            text="用于下一次 Analyze",
            icon="CHECKMARK",
        )
        row.operator(
            OPERATOR_IDS["export_semantic_discovery"],
            text="导出 JSON",
            icon="EXPORT",
        )
        layout.operator(
            OPERATOR_IDS["clear_semantic_discovery"],
            text="清除语义发现",
            icon="X",
        )
