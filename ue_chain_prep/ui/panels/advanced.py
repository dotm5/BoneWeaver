"""Advanced algorithm and preview settings, closed by default."""

import bpy


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
        scope = layout.box()
        scope.label(text="选择范围")
        scope.prop(settings, "scope_mode", text="骨骼范围")
        scope.prop(settings, "mesh_scope", text="网格来源")
        scope.prop(settings, "branch_resolution_mode", text="分叉策略")
        terminal = layout.box()
        terminal.label(text="末端方向")
        terminal.prop(settings, "terminal_mode", text="识别策略")
        terminal.prop(settings, "bone_forward_axis", text="导入轴")
        terminal.prop(settings, "tip_length_mode", text="长度来源")
        if settings.tip_length_mode == "ABSOLUTE":
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
        roll.prop(settings, "roll_mode", text="Roll 策略")
        if settings.roll_mode == "RADIAL_REFERENCE":
            roll.prop(settings, "radial_reference_mode", text="参考来源")
            roll.prop(settings, "radial_reference_object", text="参考对象")
            roll.prop(settings, "radial_reference_bone", text="参考骨骼")
        elif settings.roll_mode == "PARALLEL_TRANSPORT":
            roll.prop(settings, "parallel_transport_weight")
            roll.prop(settings, "old_axis_weight")
        preview = layout.box()
        preview.label(text="预览")
        preview.prop(settings, "preview_show_joint_graph", text="显示骨骼图")
        preview.prop(settings, "preview_show_virtual_tips", text="显示虚拟末端")
        preview.prop(settings, "preview_axis_scale", text="预览尺寸")
        safety = layout.box()
        safety.label(text="安全与验证")
        safety.prop(settings, "strict_whole_armature_pose", text="要求中性姿态")
        safety.prop(settings, "validate_full_mesh", text="验证全部相关网格")
        safety.prop(settings, "validation_tolerance_mode", text="验证容差")
        safety.prop(settings, "create_role_collections", text="创建角色 Bone Collection")
        layout.label(text=f"自定义末端覆盖：{len(settings.terminal_overrides)} 项")
