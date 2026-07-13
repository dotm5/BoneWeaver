from __future__ import annotations

import unittest

import bpy
import boneweaver

from tests.fixture_builders import clear_scene, make_quick_finger_tree, make_quick_straight_chain


class NativeLinkedSelectTests(unittest.TestCase):
    def setUp(self):
        boneweaver.unregister()
        clear_scene()
        boneweaver.register()

    def tearDown(self):
        boneweaver.unregister()
        for text in tuple(bpy.data.texts):
            if text.name.startswith("BONEWEAVER_QUICK_SNAPSHOT::"):
                bpy.data.texts.remove(text)
        clear_scene()

    def _apply_and_native_select(self, rig, active_name):
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.armature.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for pose_bone in rig.pose.bones:
            pose_bone.select = pose_bone.name == active_name
        rig.data.bones.active = rig.data.bones[active_name]
        bpy.ops.object.mode_set(mode="EDIT")
        self.assertEqual(bpy.ops.armature.select_linked(), {"FINISHED"})
        return {bone.name for bone in rig.data.edit_bones if bone.select}

    def test_native_l_selects_full_straight_component(self):
        rig = make_quick_straight_chain()
        self.assertEqual(
            self._apply_and_native_select(rig, "chain_02"),
            {"chain_01", "chain_02", "chain_03", "chain_04"},
        )

    def test_native_l_stops_at_hand_branch(self):
        rig = make_quick_finger_tree()
        selected = self._apply_and_native_select(rig, "index_02")
        self.assertEqual(selected, {"index_01", "index_02", "index_03"})
        self.assertNotIn("hand", selected)


if __name__ == "__main__":
    unittest.main()
