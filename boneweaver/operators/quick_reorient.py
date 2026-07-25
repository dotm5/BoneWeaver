"""Thin operator adapters for one-button Quick Reorient."""

from __future__ import annotations

import bpy

from ..contracts import (
    OPERATOR_IDS,
    QUICK_REORIENT_MODE_HYBRID,
    QUICK_REORIENT_MODE_LINKS_ONLY,
    QUICK_REORIENT_MODE_UEFORMAT,
)
from ..controllers.quick_reorient import QuickReorientController


class BONEWEAVER_OT_quick_reorient_auto(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["quick_reorient_auto"]
    bl_label = "原版：全自动转换并重建 L 键骨链"
    bl_description = (
        "自动重定向整个骨架、重建线性连接层级并启用 Blender 原生 L 键快速选择"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return QuickReorientController.can_run(context)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        success = QuickReorientController.run(
            context, mode=QUICK_REORIENT_MODE_UEFORMAT
        )
        state = context.window_manager.boneweaver_runtime
        self.report({"INFO"} if success else {"WARNING"}, state.quick_summary)
        return {"FINISHED"} if success else {"CANCELLED"}


class BONEWEAVER_OT_quick_reorient_links_only(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["quick_reorient_links_only"]
    bl_label = "仅重建连接：保留现有朝向"
    bl_description = (
        "面向朝向已经正确的骨架；不运行朝向识别，只在整个骨架上重建线性层级的 "
        "Blender 原生连接，使 L 键可选中单条完整骨链"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return QuickReorientController.can_run(context)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        success = QuickReorientController.run(
            context, mode=QUICK_REORIENT_MODE_LINKS_ONLY
        )
        state = context.window_manager.boneweaver_runtime
        self.report({"INFO"} if success else {"WARNING"}, state.quick_summary)
        return {"FINISHED"} if success else {"CANCELLED"}


class BONEWEAVER_OT_quick_reorient_hybrid_auto(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["quick_reorient_hybrid_auto"]
    bl_label = "实验性：多特征识别 + UEFormat 回退"
    bl_description = (
        "对整个骨架运行多特征朝向识别；逐骨采用可信结果，无法可靠识别的骨骼自动使用 "
        "UEFormat 兼容算法回退，任何单骨识别失败都不会阻断转换"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return QuickReorientController.can_run(context)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        success = QuickReorientController.run(
            context, mode=QUICK_REORIENT_MODE_HYBRID
        )
        state = context.window_manager.boneweaver_runtime
        self.report({"INFO"} if success else {"WARNING"}, state.quick_summary)
        return {"FINISHED"} if success else {"CANCELLED"}


class BONEWEAVER_OT_quick_reorient_restore(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["quick_reorient_restore"]
    bl_label = "恢复全自动转换前状态"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return QuickReorientController.can_restore(context)

    def execute(self, context):
        success = QuickReorientController.restore(context)
        state = context.window_manager.boneweaver_runtime
        message = state.quick_summary if success else "检测到后续手工修改，拒绝覆盖"
        self.report({"INFO"} if success else {"WARNING"}, message)
        return {"FINISHED"} if success else {"CANCELLED"}


QUICK_REORIENT_OPERATOR_CLASSES = (
    BONEWEAVER_OT_quick_reorient_auto,
    BONEWEAVER_OT_quick_reorient_links_only,
    BONEWEAVER_OT_quick_reorient_hybrid_auto,
    BONEWEAVER_OT_quick_reorient_restore,
)
