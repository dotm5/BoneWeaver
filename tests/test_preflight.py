from __future__ import annotations

import unittest

import bpy
import boneweaver

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from boneweaver.core.preflight import run_preflight


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()

    def tearDown(self) -> None:
        boneweaver.unregister()
        clear_scene()

    def codes(self):
        return {issue.code for issue in run_preflight(bpy.context).issues}

    def test_no_active_armature_blocks(self) -> None:
        self.assertIn("BONEWEAVER_NO_ACTIVE_ARMATURE", self.codes())

    def test_empty_selection_blocks(self) -> None:
        rig = make_chain(selected=())
        make_bound_mesh(rig)
        self.assertIn("BONEWEAVER_EMPTY_SELECTION", self.codes())

    def test_valid_chain_captures_frozen_heads_and_axes(self) -> None:
        rig = make_chain()
        make_bound_mesh(rig)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        rig.data.edit_bones["Bone_0"].roll = 0.7
        bpy.ops.object.mode_set(mode="OBJECT")
        result = run_preflight(bpy.context)
        self.assertFalse(any(issue.severity == "BLOCKER" for issue in result.issues), result.issues)
        self.assertEqual(result.armature_object_name, rig.name)
        self.assertEqual(len(result.bone_states), 3)
        state = result.bone_states[0]
        self.assertEqual(len(state.local_x), 3)
        self.assertEqual(len(state.matrix_local), 16)
        self.assertEqual(state.head, (0.0, 0.0, 0.0))
        self.assertAlmostEqual(state.roll, 0.7, places=6)

    def test_shared_armature_data_blocks(self) -> None:
        rig = make_chain()
        make_bound_mesh(rig)
        other = bpy.data.objects.new("RigInstance", rig.data)
        bpy.context.scene.collection.objects.link(other)
        self.assertIn("BONEWEAVER_SHARED_ARMATURE_DATA", self.codes())

    def test_external_connected_child_blocks(self) -> None:
        rig = make_chain(selected=("Bone_0",))
        make_bound_mesh(rig)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        child = rig.data.edit_bones["Bone_1"]
        child.head = rig.data.edit_bones["Bone_0"].tail
        child.use_connect = True
        bpy.ops.object.mode_set(mode="OBJECT")
        rig.pose.bones["Bone_0"].select = True
        rig.pose.bones["Bone_1"].select = False
        self.assertIn("BONEWEAVER_EXTERNAL_CONNECTED_CHILD", self.codes())

    def test_animation_constraint_driver_envelope_and_bbone_block(self) -> None:
        rig = make_chain()
        mesh, modifier = make_bound_mesh(rig)
        rig.animation_data_create().action = bpy.data.actions.new("Action")
        rig.driver_add("hide_viewport")
        rig.pose.bones["Bone_1"].constraints.new("COPY_ROTATION")
        modifier.use_bone_envelopes = True
        rig.data.bones["Bone_1"].bbone_segments = 2
        codes = self.codes()
        self.assertTrue(
            {
                "BONEWEAVER_RELATED_ACTION", "BONEWEAVER_RELATED_DRIVER", "BONEWEAVER_RELATED_CONSTRAINT",
                "BONEWEAVER_ENVELOPE_DEFORMATION", "BONEWEAVER_BBONE_UNSUPPORTED",
            }.issubset(codes),
            codes,
        )

    def test_analyze_operator_runs_preflight_without_scene_side_effects(self) -> None:
        rig = make_chain()
        mesh, _ = make_bound_mesh(rig)
        boneweaver.register()
        before = {
            "objects": tuple(sorted(bpy.data.objects.keys())),
            "bones": tuple((bone.name, tuple(bone.head_local), tuple(bone.tail_local)) for bone in rig.data.bones),
            "vertices": tuple(tuple(vertex.co) for vertex in mesh.data.vertices),
            "modifiers": tuple((modifier.name, modifier.type) for modifier in mesh.modifiers),
        }
        result = bpy.ops.boneweaver.analyze()
        after = {
            "objects": tuple(sorted(bpy.data.objects.keys())),
            "bones": tuple((bone.name, tuple(bone.head_local), tuple(bone.tail_local)) for bone in rig.data.bones),
            "vertices": tuple(tuple(vertex.co) for vertex in mesh.data.vertices),
            "modifiers": tuple((modifier.name, modifier.type) for modifier in mesh.modifiers),
        }
        self.assertEqual(result, {"FINISHED"})
        self.assertEqual(after, before)

    def test_selected_roots_scope_includes_all_descendants(self) -> None:
        rig = make_chain(selected=("Bone_0",))
        make_bound_mesh(rig)
        boneweaver.register()
        bpy.context.scene.boneweaver_settings.scope_mode = "SELECTED_ROOTS_AND_DESCENDANTS"
        result = run_preflight(bpy.context)
        bpy.context.scene.boneweaver_settings.scope_mode = "SELECTED_BONES"
        self.assertEqual(tuple(state.name for state in result.bone_states), ("Bone_0", "Bone_1", "Bone_2"))
        self.assertNotIn("BONEWEAVER_EXTERNAL_CONNECTED_CHILD", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
