"""Blender operator adapters for automatic cleanup."""

import bpy

from ..controllers.auto_cleanup import AutoCleanupController


class BONEWEAVER_OT_auto_cleanup(bpy.types.Operator):
    bl_idname = "boneweaver.auto_cleanup"
    bl_label = "全自动整理骨架"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="整理模式",
        items=(
            ("AUTO", "全自动整理", "重定向骨骼、连接骨链并清理辅助骨"),
            ("REORIENT", "仅父子重定向", "仅按父子关系重定向骨骼"),
            ("CONNECT", "仅连接骨链", "仅连接几何上已对齐的线性骨链，不重定向或删除骨骼"),
            ("CLEANUP", "仅清理辅助骨", "仅清理符合条件的辅助骨"),
        ),
        default="AUTO",
    )

    @classmethod
    def description(cls, context, properties):
        return {
            "AUTO": "全自动重定向骨骼、连接骨链并清理辅助骨",
            "REORIENT": "仅按父子关系重定向骨骼",
            "CONNECT": "仅连接几何上已对齐的线性骨链，不重定向或删除骨骼",
            "CLEANUP": "仅清理符合条件的辅助骨",
        }.get(properties.mode, "整理骨架")

    @classmethod
    def poll(cls, context):
        return AutoCleanupController.can_run(context)

    def execute(self, context):
        success = AutoCleanupController.run(context, mode=self.mode)
        self.report({"INFO"} if success else {"WARNING"}, context.window_manager.boneweaver_runtime.quick_summary)
        return {"FINISHED"} if success else {"CANCELLED"}


class BONEWEAVER_OT_restore_auto_cleanup(bpy.types.Operator):
    bl_idname = "boneweaver.restore_auto_cleanup"
    bl_label = "恢复整理前状态"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return AutoCleanupController.can_restore(context)

    def execute(self, context):
        success = AutoCleanupController.restore(context)
        self.report({"INFO"} if success else {"WARNING"}, context.window_manager.boneweaver_runtime.quick_summary)
        return {"FINISHED"} if success else {"CANCELLED"}


AUTO_CLEANUP_OPERATOR_CLASSES = (
    BONEWEAVER_OT_auto_cleanup,
    BONEWEAVER_OT_restore_auto_cleanup,
)
