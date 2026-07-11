from __future__ import annotations

import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain


class RestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        for name in ("Bone_1", "Bone_2"):
            group = self.mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40

    def tearDown(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.62
        settings.candidate_minimum_margin = 0.08
        settings.minimum_confidence = 0.70
        ue_chain_prep.unregister()
        for text in tuple(bpy.data.texts):
            if text.name.startswith("UECP_SNAPSHOT::"):
                bpy.data.texts.remove(text)
        clear_scene()

    def geometry(self):
        return tuple((bone.name, tuple(bone.head_local), tuple(bone.tail_local), bone.use_connect) for bone in self.rig.data.bones)

    def apply(self):
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertEqual(bpy.ops.uecp.apply(plan_id=runtime.plan_id), {"FINISHED"})
        return runtime

    def test_restore_returns_exact_pre_state(self) -> None:
        before = self.geometry()
        runtime = self.apply()
        self.assertNotEqual(self.geometry(), before)
        self.assertEqual(bpy.ops.uecp.restore_snapshot(snapshot_text_name=runtime.snapshot_text_name), {"FINISHED"})
        self.assertEqual(self.geometry(), before)
        self.assertEqual(runtime.state, "RESTORED")

    def test_restore_conflict_does_not_overwrite_manual_change(self) -> None:
        runtime = self.apply()
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode="EDIT")
        self.rig.data.edit_bones["Bone_0"].tail.x += 0.125
        bpy.ops.object.mode_set(mode="OBJECT")
        changed = self.geometry()
        self.assertEqual(bpy.ops.uecp.restore_snapshot(snapshot_text_name=runtime.snapshot_text_name), {"CANCELLED"})
        self.assertEqual(self.geometry(), changed)
        self.assertEqual(runtime.last_error, "UECP_RESTORE_CONFLICT")


if __name__ == "__main__":
    unittest.main()
