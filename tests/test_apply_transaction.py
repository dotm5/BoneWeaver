from __future__ import annotations

import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.apply_transaction import apply_plan
from ue_chain_prep.core.runtime_store import get_plan


class ApplyTransactionTests(unittest.TestCase):
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

    def _geometry(self):
        return tuple((bone.name, tuple(bone.head_local), tuple(bone.tail_local), bone.use_connect) for bone in self.rig.data.bones)

    def test_analyze_is_deterministic_and_apply_consumes_exact_plan(self) -> None:
        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.uecp_runtime
        first_id = runtime.plan_id
        first_graph = get_plan(first_id).physics_graph.graph_id
        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        self.assertEqual(runtime.plan_id, first_id)
        self.assertEqual(get_plan(runtime.plan_id).physics_graph.graph_id, first_graph)
        object_count = len(bpy.data.objects)
        bone_count = len(self.rig.data.bones)
        self.assertEqual(bpy.ops.uecp.apply(plan_id=runtime.plan_id), {"FINISHED"})
        self.assertEqual(runtime.state, "RESTORABLE")
        self.assertTrue(runtime.snapshot_text_name.startswith("UECP_SNAPSHOT::"))
        self.assertIn(runtime.snapshot_text_name, bpy.data.texts)
        self.assertEqual(len(bpy.data.objects), object_count)
        self.assertEqual(len(self.rig.data.bones), bone_count)
        self.assertEqual(tuple(self.rig.data.bones["Bone_0"].tail_local), tuple(self.rig.data.bones["Bone_1"].head_local))
        self.assertEqual(tuple(self.rig.data.bones["Bone_1"].tail_local), tuple(self.rig.data.bones["Bone_2"].head_local))

    def test_source_change_after_analyze_marks_plan_stale(self) -> None:
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        plan_id = runtime.plan_id
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode="EDIT")
        self.rig.data.edit_bones["Bone_0"].tail.x += 0.25
        bpy.ops.object.mode_set(mode="OBJECT")
        self.assertEqual(bpy.ops.uecp.apply(plan_id=plan_id), {"CANCELLED"})
        self.assertEqual(runtime.state, "STALE")

    def test_validation_failure_rolls_back_all_allowed_fields(self) -> None:
        bpy.ops.uecp.analyze()
        plan = get_plan(bpy.context.window_manager.uecp_runtime.plan_id)
        before = self._geometry()
        result = apply_plan(bpy.context, plan, validator=lambda *_: False)
        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(self._geometry(), before)


if __name__ == "__main__":
    unittest.main()
