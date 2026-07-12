"""Advanced algorithm and preview settings, closed by default."""

import bpy
from ..view_model import advanced_panel_view_from_context


class UECP_PT_advanced(bpy.types.Panel):
    bl_idname = "UECP_PT_advanced"
    bl_label = "高级设置"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.uecp_settings
        visual_cleanup = settings.physics_profile == "VISUAL_CHAIN_CLEANUP"
        view = advanced_panel_view_from_context(context)
        scope = layout.box()
        scope.label(text="选择范围")
        scope.prop(settings, "scope_mode", text="骨骼范围")
        scope.prop(settings, "mesh_scope", text="网格来源")
        if visual_cleanup:
            scope.label(text="分叉策略：仅接受手动主延续", icon="LOCKED")
        else:
            scope.prop(settings, "branch_resolution_mode", text="分叉策略")
        scope.prop(settings, "weight_island_policy", text="权重岛策略")
        terminal = layout.box()
        terminal.label(text="末端方向")
        if visual_cleanup:
            terminal.label(text="Existing Tip Helper → 安全父链外推 → 手动")
            terminal.prop(settings, "tip_helper_usage", text="末端提示骨")
        else:
            terminal.prop(settings, "tip_helper_usage", text="末端提示骨")
            if settings.tip_helper_usage == "INCLUDE_AS_PHYSICS_TERMINAL":
                terminal.label(text="显式转换仅允许主体骨视觉整理", icon="ERROR")
            terminal.prop(settings, "terminal_mode", text="识别策略")
            terminal.prop(settings, "bone_forward_axis", text="导入轴")
            terminal.prop(settings, "tip_length_mode", text="长度来源")
            if view.show_absolute_length:
                terminal.prop(settings, "absolute_tip_length", text="末端长度")
            terminal.prop(settings, "minimum_candidate_score", text="最低候选分数")
            terminal.prop(settings, "candidate_minimum_margin", text="候选差值")
        evidence = layout.box()
        evidence.label(text="权重证据")
        evidence.prop(settings, "minimum_weight", text="最小权重")
        evidence.prop(settings, "weight_exponent", text="权重指数")
        evidence.prop(settings, "use_vertex_area_weight", text="顶点面积加权")
        evidence.prop(settings, "exclusivity_mode", text="排他模式")
        roll = layout.box()
        roll.label(text="Roll 与局部轴")
        if visual_cleanup:
            roll.label(text="Roll 策略：Minimal Twist", icon="LOCKED")
        else:
            roll.prop(settings, "roll_mode", text="Roll 策略")
        if not visual_cleanup and view.show_radial_reference:
            roll.prop(settings, "radial_reference_mode", text="参考来源")
            roll.prop(settings, "radial_reference_object", text="参考对象")
            roll.prop(settings, "radial_reference_bone", text="参考骨骼")
        elif not visual_cleanup and view.show_parallel_transport:
            roll.prop(settings, "parallel_transport_weight")
            roll.prop(settings, "old_axis_weight")
        preview = layout.box()
        preview.label(text="预览")
        preview.prop(settings, "preview_show_joint_graph", text="显示骨骼图")
        preview.prop(settings, "preview_show_virtual_tips", text="显示虚拟末端")
        safety = layout.box()
        safety.label(text="安全与验证")
        safety.prop(settings, "strict_whole_armature_pose", text="要求中性姿态")
        safety.prop(settings, "validate_full_mesh", text="验证全部相关网格")
        safety.prop(settings, "validation_tolerance_mode", text="验证容差")
        deprecated_collections = safety.row()
        deprecated_collections.enabled = False
        deprecated_collections.prop(
            settings, "create_role_collections", text="角色 Bone Collection（已弃用）",
        )
        semantic_rules = layout.box()
        semantic_rules.label(text="语义发现规则（后者优先）")
        semantic_rules.prop(
            settings, "semantic_source_adapter_rule_path", text="Source Adapter",
        )
        semantic_rules.prop(settings, "semantic_game_rule_path", text="游戏规则")
        semantic_rules.prop(settings, "semantic_user_rule_path", text="用户规则")
        layout.label(text=f"自定义末端覆盖：{view.override_count} 项")
