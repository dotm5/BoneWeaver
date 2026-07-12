"""Restore user context on both successful and exceptional mode changes."""

from __future__ import annotations

import bpy


class ContextStateGuard:
    def __init__(self, context):
        self.context = context
        self.active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None
        self.selected_names = tuple(obj.name for obj in context.selected_objects)
        self.mode = context.object.mode if context.object else "OBJECT"
        self.armature_name = context.object.name if context.object and context.object.type == "ARMATURE" else None
        self.use_mirror_x = context.object.data.use_mirror_x if self.armature_name else None
        self.pose_position = context.object.data.pose_position if self.armature_name else None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        current = self.context.view_layer.objects.active
        if current and current.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for name in self.selected_names:
            obj = bpy.data.objects.get(name)
            if obj:
                obj.select_set(True)
        active = bpy.data.objects.get(self.active_name) if self.active_name else None
        self.context.view_layer.objects.active = active
        armature = bpy.data.objects.get(self.armature_name) if self.armature_name else None
        if armature:
            armature.data.use_mirror_x = self.use_mirror_x
            armature.data.pose_position = self.pose_position
        if active and self.mode != "OBJECT":
            bpy.ops.object.mode_set(mode=self.mode)
        return False
