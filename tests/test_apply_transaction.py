from __future__ import annotations

import unittest
import json

import bpy
import boneweaver

from tests.fixture_builders import clear_scene, make_bag_branch, make_bound_mesh, make_chain
from boneweaver.core.apply_transaction import apply_plan
from boneweaver.core.runtime_store import get_plan
from boneweaver.core.runtime_store import get_performance
from boneweaver.controllers.workflow import WorkflowController


class ApplyTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        boneweaver.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        for name in ("Bone_1", "Bone_2"):
            group = self.mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.boneweaver_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40
        settings.create_role_collections = False

    def tearDown(self) -> None:
        settings = bpy.context.scene.boneweaver_settings
        settings.minimum_candidate_score = 0.62
        settings.candidate_minimum_margin = 0.08
        settings.minimum_confidence = 0.70
        settings.create_role_collections = False
        boneweaver.unregister()
        for text in tuple(bpy.data.texts):
            if text.name.startswith("BONEWEAVER_SNAPSHOT::"):
                bpy.data.texts.remove(text)
        clear_scene()

    def _geometry(self):
        return tuple((bone.name, tuple(bone.head_local), tuple(bone.tail_local), bone.use_connect) for bone in self.rig.data.bones)

    def test_analyze_is_deterministic_and_apply_consumes_exact_plan(self) -> None:
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        first_id = runtime.plan_id
        first_graph = get_plan(first_id).physics_graph.graph_id
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        self.assertEqual(runtime.plan_id, first_id)
        self.assertEqual(get_plan(runtime.plan_id).physics_graph.graph_id, first_graph)
        object_count = len(bpy.data.objects)
        bone_count = len(self.rig.data.bones)
        self.assertEqual(bpy.ops.boneweaver.apply(plan_id=runtime.plan_id), {"FINISHED"})
        self.assertEqual(runtime.state, "RESTORABLE")
        performance = get_performance(runtime.plan_id)
        self.assertGreater(performance["apply_time"], 0.0)
        self.assertGreater(performance["validation_time"], 0.0)
        self.assertTrue(runtime.snapshot_text_name.startswith("BONEWEAVER_SNAPSHOT::"))
        self.assertIn(runtime.snapshot_text_name, bpy.data.texts)
        self.assertEqual(len(bpy.data.objects), object_count)
        self.assertEqual(len(self.rig.data.bones), bone_count)
        self.assertEqual(tuple(self.rig.data.bones["Bone_0"].tail_local), tuple(self.rig.data.bones["Bone_1"].head_local))
        self.assertEqual(tuple(self.rig.data.bones["Bone_1"].tail_local), tuple(self.rig.data.bones["Bone_2"].head_local))

    def test_source_change_after_analyze_marks_plan_stale(self) -> None:
        bpy.ops.boneweaver.analyze()
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan_id = runtime.plan_id
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode="EDIT")
        self.rig.data.edit_bones["Bone_0"].tail.x += 0.25
        bpy.ops.object.mode_set(mode="OBJECT")
        self.assertEqual(bpy.ops.boneweaver.apply(plan_id=plan_id), {"CANCELLED"})
        self.assertEqual(runtime.state, "STALE")

    def test_edit_mode_change_is_flushed_before_apply_stale_check(self) -> None:
        bpy.ops.boneweaver.analyze()
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan_id = runtime.plan_id
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bone = self.rig.data.edit_bones["Bone_0"]
        edit_bone.tail.x += 0.375
        changed_tail = tuple(edit_bone.tail)

        self.assertEqual(
            WorkflowController.apply(bpy.context, requested_plan_id=plan_id),
            {"CANCELLED"},
        )
        self.assertEqual(runtime.state, "STALE")
        self.assertEqual(bpy.context.mode, "EDIT_ARMATURE")
        self.assertEqual(tuple(self.rig.data.edit_bones["Bone_0"].tail), changed_tail)

    def test_validation_failure_rolls_back_all_allowed_fields(self) -> None:
        bpy.ops.boneweaver.analyze()
        plan = get_plan(bpy.context.window_manager.boneweaver_runtime.plan_id)
        before = self._geometry()
        result = apply_plan(bpy.context, plan, validator=lambda *_: False)
        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(self._geometry(), before)

    def test_legacy_role_collection_setting_is_behaviorless(self) -> None:
        bpy.context.scene.boneweaver_settings.create_role_collections = True
        bpy.ops.boneweaver.analyze()
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual(bpy.ops.boneweaver.apply(plan_id=runtime.plan_id), {"FINISHED"})
        self.assertFalse(
            {
                "BONEWEAVER_Anchors", "BONEWEAVER_Dynamics",
                "BONEWEAVER_BranchBoundaries", "BONEWEAVER_LowConfidence",
            }.intersection(self.rig.data.collections.keys())
        )

    def test_branch_apply_preserves_child_heads_and_parents_with_one_main_connection(self) -> None:
        clear_scene()
        self.rig = make_bag_branch()
        self.mesh, _ = make_bound_mesh(self.rig)
        for bone_name in self.rig.data.bones.keys():
            group = self.mesh.vertex_groups.new(name=bone_name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        before = {
            bone.name: (
                tuple(bone.head_local),
                bone.parent.name if bone.parent else None,
            )
            for bone in self.rig.data.bones
        }
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_plan(runtime.plan_id)
        resolution = next(item for item in plan.branch_resolutions if item.branch_bone_name == "bag_r_03")
        self.assertEqual(resolution.selected_child_name, "bag_r_04")
        self.assertIsNotNone(plan.topology_ledger)
        self.assertEqual(plan.topology_ledger.resolved_branch_count, 1)
        self.assertEqual(plan.topology_ledger.proposal_count, len(plan.proposals))
        self.assertEqual(runtime.issue_count_blocker, 0)
        self.assertEqual(bpy.ops.boneweaver.apply(plan_id=runtime.plan_id), {"FINISHED"})
        self.assertEqual(
            tuple(self.rig.data.bones["bag_r_03"].tail_local),
            tuple(self.rig.data.bones["bag_r_04"].head_local),
        )
        self.assertTrue(self.rig.data.bones["bag_r_04"].use_connect)
        self.assertFalse(self.rig.data.bones["bag_r_03a_01"].use_connect)
        snapshot = json.loads(bpy.data.texts[runtime.snapshot_text_name].as_string())
        records = snapshot["mutation_records"]
        proposal_ids = {proposal.proposal_id for proposal in plan.proposals}
        self.assertGreater(len(records), 0)
        self.assertTrue(all(record["proposal_id"] in proposal_ids for record in records))
        side_record = next(record for record in records if record["bone_name"] == "bag_r_03a_01")
        self.assertTrue(side_record["use_connect_changed"])
        self.assertIn("BRANCH_SIDE_ROOT", side_record["reason_codes"])
        self.assertEqual(snapshot["topology_ledger"]["mutation_record_count"], len(records))
        after = {
            bone.name: (
                tuple(bone.head_local),
                bone.parent.name if bone.parent else None,
            )
            for bone in self.rig.data.bones
        }
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
