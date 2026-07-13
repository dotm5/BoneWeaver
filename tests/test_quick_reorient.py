from __future__ import annotations

import dataclasses
import json
import unittest

import bpy
import boneweaver

from tests.fixture_builders import (
    clear_scene,
    make_bound_mesh,
    make_quick_finger_tree,
    make_quick_straight_chain,
)
from boneweaver.core.quick_reorient import average_offsets, dominant_axis
from boneweaver.core.quick_source_adapter import capture_quick_source
from boneweaver.core.quick_transaction import apply_quick_plan
from boneweaver.core.runtime_store import get_quick_plan


class QuickPureTests(unittest.TestCase):
    def test_dominant_axis_matches_ueformat_strict_ties(self):
        self.assertEqual(dominant_axis((0.82, 0.12, 0.04)), (1.0, 0.0, 0.0))
        self.assertEqual(dominant_axis((1.0, 1.0, 0.0)), (0.0, 1.0, 0.0))
        self.assertEqual(dominant_axis((1.0, 0.0, 1.0)), (0.0, 0.0, 1.0))
        self.assertEqual(dominant_axis((0.0, 0.0, 0.0)), (0.0, 0.0, 1.0))

    def test_average_child_direction_and_length(self):
        average, length = average_offsets(((2, 0, 0), (0, 2, 0)))
        self.assertEqual(average, (1.0, 1.0, 0.0))
        self.assertEqual(length, 2.0)


class QuickReorientBlenderTests(unittest.TestCase):
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

    def _states(self, rig):
        states, _metadata = capture_quick_source(bpy.context, rig)
        return states

    def test_one_button_processes_whole_armature_and_connects_chain(self):
        rig = make_quick_straight_chain()
        before = {
            state.bone_name: (state.parent_name, state.head)
            for state in self._states(rig)
        }
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual(runtime.quick_state, "RESTORABLE")
        self.assertEqual(runtime.quick_total_bones, 4)
        after = {state.bone_name: state for state in self._states(rig)}
        self.assertEqual(
            {name: (state.parent_name, state.head) for name, state in after.items()},
            before,
        )
        self.assertFalse(after["chain_01"].use_connect)
        for index in range(2, 5):
            child = after[f"chain_{index:02d}"]
            parent = after[f"chain_{index - 1:02d}"]
            self.assertTrue(child.use_connect)
            self.assertEqual(parent.tail, child.head)
        snapshot = json.loads(
            bpy.data.texts[runtime.quick_snapshot_text_name].as_string()
        )
        self.assertEqual(snapshot["status"], "APPLIED")

    def test_branch_creates_separate_finger_components(self):
        make_quick_finger_tree()
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_quick_plan(runtime.quick_plan_id)
        self.assertEqual(
            {component.bone_names for component in plan.linked_components},
            {
                ("hand",),
                ("thumb_01", "thumb_02", "thumb_03"),
                ("index_01", "index_02", "index_03"),
                ("middle_01", "middle_02", "middle_03"),
            },
        )
        states = {state.bone_name: state for state in self._states(bpy.context.object)}
        for root in ("thumb_01", "index_01", "middle_01"):
            self.assertFalse(states[root].use_connect)

    def test_ueformat_already_reoriented_and_socket_are_preserved(self):
        rig = make_quick_finger_tree()
        for bone in rig.data.bones:
            bone["orig_loc"] = tuple(bone.head_local)
            bone["orig_quat"] = (1.0, 0.0, 0.0, 0.0)
        rig.data.bones["hand"]["reorient_direction"] = (0.0, 1.0, 0.0)
        rig.data.bones["middle_03"]["is_socket"] = True
        socket_before = next(
            state for state in self._states(rig) if state.bone_name == "middle_03"
        )
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual(runtime.quick_source, "UEFORMAT_ALREADY_REORIENTED")
        socket_after = next(
            state for state in self._states(rig) if state.bone_name == "middle_03"
        )
        self.assertEqual(socket_after, socket_before)

    def test_second_run_is_idempotent_and_restore_is_exact(self):
        rig = make_quick_straight_chain()
        before = self._states(rig)
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        first_snapshot = runtime.quick_snapshot_text_name
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        self.assertTrue(runtime.quick_already_normalized)
        self.assertEqual(runtime.quick_mutation_count, 0)
        second_snapshot = runtime.quick_snapshot_text_name
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_restore(), {"FINISHED"})
        self.assertNotEqual(self._states(rig), before)
        runtime.quick_snapshot_text_name = first_snapshot
        runtime.quick_state = "RESTORABLE"
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_restore(), {"FINISHED"})
        self.assertEqual(self._states(rig), before)
        self.assertNotEqual(first_snapshot, second_snapshot)

    def test_constraint_is_advisory_and_conversion_finishes(self):
        rig = make_quick_straight_chain()
        before = self._states(rig)
        rig.pose.bones["chain_02"].constraints.new("COPY_ROTATION")
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual(runtime.quick_state, "RESTORABLE")
        self.assertEqual(runtime.quick_blocker_count, 0)
        self.assertGreater(runtime.quick_warning_count, 0)
        self.assertNotEqual(self._states(rig), before)
        self.assertEqual(len(rig.pose.bones["chain_02"].constraints), 1)

    def test_all_previous_policy_blockers_are_advisory(self):
        rig = make_quick_straight_chain()
        before = self._states(rig)
        mesh, _modifier = make_bound_mesh(rig, name="QuickMesh")
        second_modifier = mesh.modifiers.new(name="ArmatureSecond", type="ARMATURE")
        second_modifier.object = rig
        _envelope_mesh, envelope_modifier = make_bound_mesh(
            rig, name="QuickEnvelopeMesh"
        )
        envelope_modifier.use_bone_envelopes = True
        rig.animation_data_create().action = bpy.data.actions.new("QuickAction")
        rig.animation_data.nla_tracks.new()
        rig.driver_add("hide_viewport")
        rig.pose.bones["chain_02"].constraints.new("COPY_ROTATION")
        rig.pose.bones["chain_03"].rotation_mode = "XYZ"
        rig.pose.bones["chain_03"].rotation_euler.x = 0.25
        rig.data.bones["chain_02"].bbone_segments = 2

        attached = bpy.data.objects.new("QuickAttached", None)
        bpy.context.scene.collection.objects.link(attached)
        attached.parent = rig
        attached.parent_type = "BONE"
        attached.parent_bone = "chain_02"
        object_constraint = attached.constraints.new("COPY_LOCATION")
        object_constraint.target = rig
        object_constraint.subtarget = "chain_03"

        shared_data = rig.data
        sibling = bpy.data.objects.new("QuickSharedInstance", shared_data)
        bpy.context.scene.collection.objects.link(sibling)
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)

        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_quick_plan(runtime.quick_plan_id)
        codes = {issue.code for issue in plan.issues}
        self.assertEqual(runtime.quick_state, "RESTORABLE")
        self.assertEqual(runtime.quick_blocker_count, 0)
        self.assertFalse(any(issue.severity == "BLOCKER" for issue in plan.issues))
        self.assertTrue(
            {
                "BONEWEAVER_AMBIGUOUS_ARMATURE_MODIFIER",
                "BONEWEAVER_NON_IDENTITY_POSE",
                "BONEWEAVER_QUICK_BBONE_UNSUPPORTED",
                "BONEWEAVER_QUICK_BONE_PARENTED_OBJECT",
                "BONEWEAVER_QUICK_ENVELOPE_DEFORMATION",
                "BONEWEAVER_QUICK_RELATED_ACTION",
                "BONEWEAVER_QUICK_RELATED_CONSTRAINT",
                "BONEWEAVER_QUICK_RELATED_DRIVER",
                "BONEWEAVER_QUICK_RELATED_NLA",
            }.issubset(codes),
            codes,
        )
        self.assertIsNot(rig.data, shared_data)
        self.assertIs(sibling.data, shared_data)
        self.assertNotEqual(self._states(rig), before)
        self.assertIn(
            "BONEWEAVER_QUICK_MESH_DIAGNOSTIC_SKIPPED",
            json.loads(
                bpy.data.texts[runtime.quick_snapshot_text_name].as_string()
            )["validation_issues"],
        )
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_restore(), {"FINISHED"})
        self.assertEqual(self._states(rig), before)

    def test_validation_failure_rolls_back(self):
        rig = make_quick_straight_chain()
        before = self._states(rig)
        from boneweaver.core.quick_reorient import build_quick_reorient_plan
        plan = build_quick_reorient_plan(bpy.context)
        result = apply_quick_plan(bpy.context, plan, validator=lambda *_: False)
        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(self._states(rig), before)

    def test_force_complete_keeps_conversion_when_diagnostic_fails(self):
        rig = make_quick_straight_chain()
        before = self._states(rig)
        from boneweaver.core.quick_reorient import build_quick_reorient_plan
        plan = build_quick_reorient_plan(bpy.context)
        result = apply_quick_plan(
            bpy.context,
            plan,
            validator=lambda *_: False,
            strict_validation=False,
        )
        self.assertTrue(result.success)
        self.assertFalse(result.rolled_back)
        self.assertIn(
            "BONEWEAVER_QUICK_CUSTOM_VALIDATION_FAILED",
            result.validation_issues,
        )
        self.assertNotEqual(self._states(rig), before)

    def test_restore_conflict_preserves_manual_edit(self):
        rig = make_quick_straight_chain()
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        rig.data.edit_bones["chain_02"].tail.z += 0.125
        bpy.ops.object.mode_set(mode="OBJECT")
        manual = self._states(rig)
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_restore(), {"CANCELLED"})
        self.assertEqual(runtime.last_error, "BONEWEAVER_QUICK_RESTORE_CONFLICT")
        self.assertEqual(self._states(rig), manual)

    def test_plan_is_frozen_and_serializable(self):
        make_quick_straight_chain()
        self.assertEqual(bpy.ops.boneweaver.quick_reorient_auto(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_quick_plan(runtime.quick_plan_id)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.plan_id = "changed"
        self.assertEqual(
            dataclasses.asdict(plan)["kind"], "boneweaver.quick_reorient_plan"
        )


if __name__ == "__main__":
    unittest.main()
