"""Selection identity and issue-location helpers."""

from __future__ import annotations

import hashlib
import json


class SelectionController:
    @staticmethod
    def armature_from_context(context):
        active = getattr(context, "active_object", None)
        if active is not None and active.type == "ARMATURE":
            return active, "ARMATURE"
        if active is not None and active.type == "MESH":
            for modifier in active.modifiers:
                if modifier.type == "ARMATURE" and modifier.object is not None:
                    return modifier.object, "ARMATURE_MODIFIER"
        return None, "NONE"

    @staticmethod
    def selected_bone_names(context, armature=None) -> tuple[str, ...]:
        armature = armature or SelectionController.armature_from_context(context)[0]
        if armature is None:
            return ()
        return tuple(sorted(
            pose_bone.name for pose_bone in armature.pose.bones
            if bool(getattr(pose_bone, "select", getattr(pose_bone.bone, "select", False)))
        ))

    @staticmethod
    def signature(context, bone_names=None) -> str:
        armature, _source = SelectionController.armature_from_context(context)
        if armature is None:
            return ""
        names = tuple(sorted(bone_names)) if bone_names is not None else SelectionController.selected_bone_names(context, armature)
        payload = json.dumps((armature.data.name, names), ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def locate_bone(context, bone_name: str) -> bool:
        armature, _source = SelectionController.armature_from_context(context)
        if armature is None or bone_name not in armature.data.bones:
            return False
        context.view_layer.objects.active = armature
        armature.select_set(True)
        if context.mode == "POSE" and context.object == armature:
            try:
                import bpy
                bpy.ops.pose.select_all(action="DESELECT")
            except RuntimeError:
                pass
        for pose_bone in armature.pose.bones:
            pose_bone.select = pose_bone.name == bone_name
        armature.data.bones.active = armature.data.bones[bone_name]
        context.view_layer.update()
        area = getattr(context, "area", None)
        if area is not None and area.type == "VIEW_3D":
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region is not None:
                try:
                    import bpy
                    with context.temp_override(area=area, region=region, space_data=area.spaces.active):
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                except RuntimeError:
                    pass
        return True
