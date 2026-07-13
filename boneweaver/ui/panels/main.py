"""Compact user workflow panel driven by PanelViewState."""

import bpy

from ...contracts import OPERATOR_IDS
from ..view_model import panel_view_state_from_context, quick_reorient_view_from_context


class BONEWEAVER_PT_main(bpy.types.Panel):
    bl_idname = "BONEWEAVER_PT_main"
    bl_label = "BoneWeaver"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneWeaver"

    def draw(self, context):
        layout = self.layout
        view = panel_view_state_from_context(context)
        quick = quick_reorient_view_from_context(context)
        quick_box = layout.box()
        quick_box.label(text="全自动骨架转换", icon="MOD_ARMATURE")
        quick_box.label(text="自动重定向并重建 Blender 原生 L 键骨链")
        quick_row = quick_box.row()
        quick_row.scale_y = 1.6
        quick_row.enabled = quick.button_enabled
        quick_row.operator(
            OPERATOR_IDS["quick_reorient_auto"],
            text="全自动转换并重建 L 键骨链",
            icon="PLAY",
        )
        if quick.summary:
            icon = "ERROR" if quick.state in {"BLOCKED", "ERROR", "ROLLED_BACK"} else "CHECKMARK"
            quick_box.label(text=quick.summary, icon=icon)
            quick_box.label(
                text=(
                    f"{quick.processed_bones}/{quick.total_bones} 根骨骼 · "
                    f"{quick.component_count} 个 L 键分量 · "
                    f"{quick.connected_edges} 条连接"
                )
            )
            if quick.source:
                quick_box.label(text=f"来源：{quick.source}", icon="INFO")
        if quick.restore_enabled:
            quick_box.operator(
                OPERATOR_IDS["quick_reorient_restore"],
                text="恢复全自动转换前状态",
                icon="LOOP_BACK",
            )
        box = layout.box()
        box.label(text=f"骨架：{view.target.armature_name or '未找到'}", icon="ARMATURE_DATA")
        box.label(text=f"已选择：{view.target.selected_bone_count} 根骨骼")
        if view.target.source_kind == "ARMATURE_MODIFIER":
            box.label(text="来源：当前模型的骨架修改器")
        layout.prop(context.scene.boneweaver_settings, "physics_profile", text="目标用途")
        if context.scene.boneweaver_settings.physics_profile == "VISUAL_CHAIN_CLEANUP":
            layout.label(text="仅用于不保留原 UE 动画的显式视觉整理", icon="ERROR")
            layout.prop(
                context.scene.boneweaver_settings,
                "tip_helper_usage",
                text="末端提示骨",
            )
            layout.label(text="分叉只接受手动指定的主延续", icon="INFO")
        if view.result:
            result_box = layout.box()
            result_box.label(text=view.result.title, icon="CHECKMARK" if not view.result.blocker_count else "ERROR")
            result_box.label(text=view.result.description)
            if view.result.bone_count:
                result_box.label(text=f"{view.result.chain_count} 条骨骼链 · {view.result.bone_count} 根骨骼")
        for notice in view.notice_lines:
            layout.label(text=notice, icon="INFO")
        if view.secondary_actions:
            row = layout.row(align=True)
            for action in view.secondary_actions:
                row.operator(action.operator_id, text=action.label, icon=action.icon)
        if view.primary_action:
            row = layout.row()
            row.scale_y = 1.5
            row.enabled = view.primary_action.enabled
            row.operator(view.primary_action.operator_id, text=view.primary_action.label, icon=view.primary_action.icon)
            if not view.primary_action.enabled and view.primary_action.disabled_reason:
                layout.label(text=view.primary_action.disabled_reason, icon="INFO")
