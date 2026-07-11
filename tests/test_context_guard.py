from __future__ import annotations

import unittest

import bpy

from tests.fixture_builders import clear_scene, make_chain
from ue_chain_prep.core.context_guard import ContextStateGuard


class ContextGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()

    def tearDown(self) -> None:
        clear_scene()

    def test_restores_active_object_selection_mode_and_x_mirror(self) -> None:
        rig = make_chain()
        other = bpy.data.objects.new("Other", None)
        bpy.context.scene.collection.objects.link(other)
        other.select_set(True)
        rig.data.use_mirror_x = True
        original_selected = {obj.name for obj in bpy.context.selected_objects}
        with ContextStateGuard(bpy.context):
            rig.data.use_mirror_x = False
            other.select_set(False)
            bpy.context.view_layer.objects.active = rig
            bpy.ops.object.mode_set(mode="EDIT")
        self.assertEqual(bpy.context.mode, "OBJECT")
        self.assertEqual(bpy.context.view_layer.objects.active, rig)
        self.assertEqual({obj.name for obj in bpy.context.selected_objects}, original_selected)
        self.assertTrue(rig.data.use_mirror_x)


if __name__ == "__main__":
    unittest.main()
