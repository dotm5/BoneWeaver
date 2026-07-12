"""Small non-destructive hierarchy inspection panel."""

import bpy

from ...contracts import OPERATOR_IDS
from ...core.runtime_store import get_hierarchy_inspection


class UECP_PT_hierarchy(bpy.types.Panel):
    bl_idname = "UECP_PT_hierarchy"
    bl_label = "Hierarchy Chain Inspection"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        runtime = context.window_manager.uecp_runtime

        summary = layout.box()
        if runtime.hierarchy_inspection_active:
            summary.label(text=f"活动骨骼：{runtime.hierarchy_active_bone_name or '—'}")
            summary.label(text=f"母骨：{runtime.hierarchy_parent_context_name or '无'}")
            if runtime.hierarchy_selection_mode == "SELECTED_ROOTS_AND_DESCENDANTS":
                summary.label(text=f"范围骨骼：{runtime.hierarchy_bone_count}")
            else:
                summary.label(text=f"后代：{max(0, runtime.hierarchy_bone_count - 1)}")
            summary.label(text=f"分叉：{runtime.hierarchy_branch_count}")
            summary.label(
                text=(
                    f"末端提示骨：{runtime.hierarchy_tip_helper_count} · "
                    f"排除 Helper：{runtime.hierarchy_excluded_helper_count}"
                )
            )
            if runtime.hierarchy_scope_used:
                summary.label(text="该范围已冻结用于下一次检查", icon="LOCKED")
        else:
            summary.label(text="请选择一根活动骨骼后检查层级", icon="BONE_DATA")

        layout.prop(runtime, "hierarchy_selection_mode", text="选择方式")
        row = layout.row(align=True)
        row.operator(OPERATOR_IDS["inspect_active_hierarchy"], text="检查范围", icon="VIEWZOOM")
        select = row.row(align=True)
        select.enabled = runtime.hierarchy_inspection_active
        select.operator(OPERATOR_IDS["select_inspected_scope"], text="选择范围", icon="RESTRICT_SELECT_OFF")

        row = layout.row(align=True)
        use = row.row(align=True)
        use.enabled = runtime.hierarchy_inspection_active
        use.operator(OPERATOR_IDS["use_inspected_scope"], text="用于转换", icon="CHECKMARK")
        clear = row.row(align=True)
        clear.enabled = runtime.hierarchy_inspection_active
        clear.operator(OPERATOR_IDS["clear_hierarchy_inspection"], text="清除检查", icon="X")

        overlay = layout.box()
        overlay.label(text="视图标记", icon="HIDE_OFF")
        overlay.prop(runtime, "hierarchy_show_names", text="显示 Bone 名称")
        overlay.prop(runtime, "hierarchy_show_parent", text="显示母骨")
        overlay.prop(runtime, "hierarchy_show_side_branches", text="显示侧分支")
        overlay.prop(runtime, "hierarchy_show_tip_helpers", text="显示末端提示骨")

        if runtime.hierarchy_inspection_active and runtime.hierarchy_branch_count:
            branch = layout.box()
            branch.label(text="手动指定主延续", icon="SORT_ASC")
            session = get_hierarchy_inspection()
            if session is not None:
                for branch_name in session.plan.branch_bone_names:
                    branch.label(text=branch_name, icon="BONE_DATA")
                    children = tuple(
                        name
                        for name in session.index.children_of(branch_name)
                        if name not in session.snapshot.excluded_helper_names
                    )
                    for child_name in children:
                        operator = branch.operator(
                            OPERATOR_IDS["set_branch_continuation"],
                            text=f"→ {child_name}",
                            icon="FORWARD",
                        )
                        operator.branch_bone_name = branch_name
                        operator.selected_child_name = child_name
