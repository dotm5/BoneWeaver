from __future__ import annotations

import types
import unittest
from unittest.mock import patch

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bag_branch, make_bound_mesh
from ue_chain_prep.controllers.hierarchy_inspection import HierarchyInspectionController
from ue_chain_prep.controllers.hierarchy_overlay import HierarchyOverlayController
from ue_chain_prep.controllers.session import SessionController
from ue_chain_prep.core.hierarchy_index import (
    ArmatureHierarchyIndex,
    HierarchyBoneSnapshot,
)
from ue_chain_prep.core.hierarchy_inspection import (
    HierarchyInspectionInput,
    build_hierarchy_inspection_plan,
    hierarchy_inspection_plan_to_data,
)
from ue_chain_prep.core.mesh_scan_cache import MeshScanCache
from ue_chain_prep.core.runtime_store import (
    get_hierarchy_inspection,
    get_plan,
    get_used_inspection_scope,
)


def _index(*pairs):
    return ArmatureHierarchyIndex.from_bones(
        HierarchyBoneSnapshot(name, parent) for name, parent in pairs
    )


def _snapshot(mode, active, *, selected=(), continuations=(), tips=(), excluded=()):
    return HierarchyInspectionInput(
        armature_object_name="Rig",
        armature_fingerprint="fingerprint",
        active_bone_name=active,
        selection_mode=mode,
        selected_bone_names=selected,
        branch_continuations=continuations,
        tip_helper_names=tips,
        excluded_helper_names=excluded,
    )


class HierarchyInspectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index(
            ("hand_l", None),
            ("finger_index_l_01", "hand_l"),
            ("finger_index_l_02", "finger_index_l_01"),
            ("finger_index_l_03", "finger_index_l_02"),
            ("finger_index_l_tip", "finger_index_l_03"),
            ("finger_middle_l_01", "hand_l"),
            ("finger_middle_l_02", "finger_middle_l_01"),
            ("ik_hand_l", "hand_l"),
            ("spine_01", None),
            ("spine_02", "spine_01"),
            ("spine_03", "spine_02"),
            ("clavicle_l", "spine_03"),
            ("neck_01", "spine_03"),
            ("socket_weapon", "clavicle_l"),
        )

    def test_unconnected_linear_chain_uses_parent_links_and_stops_at_branch(self) -> None:
        plan = build_hierarchy_inspection_plan(
            self.index, _snapshot("LINEAR_CHAIN", "finger_index_l_01"),
        )
        self.assertEqual(
            plan.selected_bone_names,
            (
                "finger_index_l_01", "finger_index_l_02",
                "finger_index_l_03", "finger_index_l_tip",
            ),
        )
        self.assertEqual(plan.parent_context_name, "hand_l")
        self.assertNotIn("hand_l", plan.selected_bone_names)

        branch = build_hierarchy_inspection_plan(
            self.index, _snapshot("LINEAR_CHAIN", "spine_01"),
        )
        self.assertEqual(branch.selected_bone_names, ("spine_01", "spine_02", "spine_03"))
        self.assertEqual(branch.branch_bone_names, ("spine_03",))
        self.assertEqual(branch.side_branch_root_names, ("clavicle_l", "neck_01"))
        self.assertIn("UECP_HIERARCHY_BRANCH_AMBIGUOUS", branch.issue_codes)

    def test_full_subtree_includes_tip_and_skips_excluded_helpers(self) -> None:
        plan = build_hierarchy_inspection_plan(
            self.index,
            _snapshot(
                "FULL_SUBTREE",
                "hand_l",
                tips=("finger_index_l_tip",),
                excluded=("ik_hand_l", "socket_weapon"),
            ),
        )
        self.assertIn("finger_index_l_tip", plan.selected_bone_names)
        self.assertEqual(plan.tip_helper_names, ("finger_index_l_tip",))
        self.assertNotIn("ik_hand_l", plan.selected_bone_names)
        self.assertEqual(plan.excluded_helper_names, ("ik_hand_l",))
        self.assertNotIn("socket_weapon", plan.excluded_helper_names)

    def test_same_stem_chain_follows_unique_sequence(self) -> None:
        plan = build_hierarchy_inspection_plan(
            self.index, _snapshot("SAME_STEM_CHAIN", "finger_index_l_01"),
        )
        self.assertEqual(
            plan.selected_bone_names,
            ("finger_index_l_01", "finger_index_l_02", "finger_index_l_03"),
        )
        self.assertIn("UECP_HIERARCHY_STEM_NO_CONTINUATION", plan.issue_codes)

    def test_selected_roots_union_only_selected_subtrees(self) -> None:
        plan = build_hierarchy_inspection_plan(
            self.index,
            _snapshot(
                "SELECTED_ROOTS_AND_DESCENDANTS",
                "spine_01",
                selected=("finger_index_l_01", "finger_middle_l_01"),
                excluded=("ik_hand_l", "socket_weapon"),
            ),
        )
        self.assertEqual(
            plan.selected_bone_names,
            (
                "finger_index_l_01", "finger_index_l_02", "finger_index_l_03",
                "finger_index_l_tip", "finger_middle_l_01", "finger_middle_l_02",
            ),
        )
        self.assertNotIn("spine_01", plan.selected_bone_names)

    def test_main_path_requires_explicit_direct_child_continuation(self) -> None:
        stopped = build_hierarchy_inspection_plan(
            self.index, _snapshot("MAIN_PATH_TO_LEAF", "spine_01"),
        )
        self.assertEqual(stopped.selected_bone_names, ("spine_01", "spine_02", "spine_03"))
        self.assertIn("UECP_HIERARCHY_BRANCH_AMBIGUOUS", stopped.issue_codes)

        continued = build_hierarchy_inspection_plan(
            self.index,
            _snapshot(
                "MAIN_PATH_TO_LEAF", "spine_01",
                continuations=(("spine_03", "neck_01"),),
            ),
        )
        self.assertEqual(
            continued.selected_bone_names,
            ("spine_01", "spine_02", "spine_03", "neck_01"),
        )
        self.assertEqual(continued.side_branch_root_names, ("clavicle_l",))
        self.assertFalse(continued.issue_codes)

    def test_inspection_id_and_schema_data_are_deterministic(self) -> None:
        first = build_hierarchy_inspection_plan(
            self.index,
            _snapshot(
                "SELECTED_ROOTS_AND_DESCENDANTS",
                "finger_index_l_01",
                selected=("finger_middle_l_01", "finger_index_l_01"),
            ),
        )
        second = build_hierarchy_inspection_plan(
            self.index,
            _snapshot(
                "SELECTED_ROOTS_AND_DESCENDANTS",
                "finger_index_l_01",
                selected=("finger_index_l_01", "finger_middle_l_01"),
            ),
        )
        self.assertEqual(first.inspection_id, second.inspection_id)
        self.assertEqual(
            hierarchy_inspection_plan_to_data(first),
            hierarchy_inspection_plan_to_data(second),
        )

    def test_overlay_roles_include_only_locally_encountered_exclusions(self) -> None:
        snapshot = _snapshot(
            "FULL_SUBTREE",
            "finger_index_l_01",
            tips=("finger_index_l_tip",),
            excluded=("ik_hand_l", "socket_weapon"),
        )
        plan = build_hierarchy_inspection_plan(self.index, snapshot)
        session = types.SimpleNamespace(plan=plan, snapshot=snapshot, index=self.index)
        roles = HierarchyOverlayController._role_by_name(session)
        self.assertEqual(roles["finger_index_l_01"], "ACTIVE_ROOT")
        self.assertEqual(roles["hand_l"], "PARENT_CONTEXT")
        self.assertEqual(roles["finger_index_l_tip"], "TIP_HELPER")
        self.assertNotIn("ik_hand_l", roles)
        self.assertNotIn("socket_weapon", roles)


class HierarchyInspectionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        data = bpy.data.armatures.new("TipRigData")
        self.rig = bpy.data.objects.new("TipRig", data)
        bpy.context.scene.collection.objects.link(self.rig)
        bpy.context.view_layer.objects.active = self.rig
        self.rig.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        parent = None
        for name, y in (("hair_01", 0.0), ("hair_02", 1.0), ("hair_end", 2.0)):
            bone = data.edit_bones.new(name)
            bone.head = (0.0, y, 0.0)
            bone.tail = (0.0, y + 0.2, 0.0)
            bone.parent = parent
            bone.use_connect = False
            parent = bone
        bpy.ops.object.mode_set(mode="OBJECT")
        for pose_bone in self.rig.pose.bones:
            pose_bone.select = pose_bone.name == "hair_01"
        data.bones.active = data.bones["hair_01"]

        vertices = [
            (-0.05, 0.2, 0.0), (0.0, 0.6, 0.0), (0.05, 0.9, 0.0),
            (-0.05, 1.2, 0.0), (0.0, 1.6, 0.0), (0.05, 1.9, 0.0),
        ]
        mesh_data = bpy.data.meshes.new("TipMeshData")
        mesh_data.from_pydata(vertices, [(0, 1), (1, 2), (3, 4), (4, 5)], [])
        self.mesh = bpy.data.objects.new("TipMesh", mesh_data)
        bpy.context.scene.collection.objects.link(self.mesh)
        for name, indices in (("hair_01", (0, 1, 2)), ("hair_02", (3, 4, 5))):
            group = self.mesh.vertex_groups.new(name=name)
            group.add(indices, 1.0, "REPLACE")
        modifier = self.mesh.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = self.rig
        bpy.context.window_manager.uecp_runtime.hierarchy_selection_mode = "FULL_SUBTREE"

    def tearDown(self) -> None:
        HierarchyInspectionController.clear(bpy.context)
        ue_chain_prep.unregister()
        clear_scene()

    def test_fresh_inspection_classifies_tip_helper_and_freezes_reference_identity(self) -> None:
        before_selection = tuple(
            pose_bone.name for pose_bone in self.rig.pose.bones if pose_bone.select
        )
        scan_count = 0
        original_scan = MeshScanCache.scan

        def counted_scan(*args, **kwargs):
            nonlocal scan_count
            scan_count += 1
            return original_scan(*args, **kwargs)

        with (
            patch.object(MeshScanCache, "scan", side_effect=counted_scan),
        ):
            plan = HierarchyInspectionController.inspect(bpy.context)

        self.assertEqual(scan_count, 1)
        self.assertEqual(plan.tip_helper_names, ("hair_end",))
        self.assertFalse(bpy.context.window_manager.uecp_runtime.hierarchy_overlay_enabled)
        self.assertEqual(
            tuple(pose_bone.name for pose_bone in self.rig.pose.bones if pose_bone.select),
            before_selection,
        )
        selected = HierarchyInspectionController.select_scope(bpy.context)
        self.assertEqual(selected, ("hair_01", "hair_02", "hair_end"))
        self.assertEqual(
            tuple(pose_bone.name for pose_bone in self.rig.pose.bones if pose_bone.select),
            ("hair_01", "hair_02", "hair_end"),
        )
        self.assertEqual(self.rig.data.bones.active.name, "hair_01")
        scope = HierarchyInspectionController.use_scope(bpy.context)
        self.assertEqual(scope.reference_only_tip_helper_names, ("hair_end",))
        self.assertIn("hair_end", scope.bone_names)

    def test_undo_lifecycle_clears_plan_scope_and_runtime(self) -> None:
        HierarchyInspectionController.inspect(bpy.context)
        HierarchyInspectionController.use_scope(bpy.context)
        self.assertIsNotNone(get_hierarchy_inspection())
        self.assertIsNotNone(get_used_inspection_scope())
        SessionController.on_undo_post(None)
        self.assertIsNone(get_hierarchy_inspection())
        self.assertIsNone(get_used_inspection_scope())
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertFalse(runtime.hierarchy_inspection_active)
        self.assertFalse(runtime.hierarchy_scope_used)
        self.assertFalse(runtime.hierarchy_overlay_enabled)

    def test_selected_roots_pose_selection_does_not_add_unselected_active_bone(self) -> None:
        bpy.ops.object.mode_set(mode="EDIT")
        for name, x in (("other_root", 1.0), ("idle_active", 2.0)):
            bone = self.rig.data.edit_bones.new(name)
            bone.head = (x, 0.0, 0.0)
            bone.tail = (x, 0.2, 0.0)
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.pose.select_all(action="DESELECT")
        self.rig.pose.bones["hair_01"].select = True
        self.rig.pose.bones["other_root"].select = True
        self.rig.data.bones.active = self.rig.data.bones["idle_active"]
        runtime = bpy.context.window_manager.uecp_runtime
        runtime.hierarchy_selection_mode = "SELECTED_ROOTS_AND_DESCENDANTS"

        plan = HierarchyInspectionController.inspect(bpy.context)
        self.assertNotIn("idle_active", plan.selected_bone_names)
        selected = HierarchyInspectionController.select_scope(bpy.context)

        self.assertNotIn("idle_active", selected)
        self.assertFalse(self.rig.pose.bones["idle_active"].select)
        self.assertEqual(self.rig.data.bones.active.name, "idle_active")

    def test_manual_branch_continuation_reaches_analyze_plan(self) -> None:
        clear_scene()
        self.rig = make_bag_branch()
        self.mesh, _modifier = make_bound_mesh(self.rig)
        for bone_name in self.rig.data.bones.keys():
            group = self.mesh.vertex_groups.new(name=bone_name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        runtime = bpy.context.window_manager.uecp_runtime
        runtime.hierarchy_selection_mode = "LINEAR_CHAIN"
        self.rig.data.bones.active = self.rig.data.bones["bag_r_02"]

        inspected = HierarchyInspectionController.inspect(bpy.context)
        self.assertIn("bag_r_03", inspected.branch_bone_names)
        continued = HierarchyInspectionController.set_branch_continuation(
            bpy.context, "bag_r_03", "bag_r_04",
        )
        self.assertEqual(continued.side_branch_root_names, ("bag_r_03a_01",))
        scope = HierarchyInspectionController.use_scope(bpy.context)
        self.assertIn("bag_r_03a_01", scope.bone_names)

        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        plan = get_plan(runtime.plan_id)
        resolution = next(
            item for item in plan.branch_resolutions
            if item.branch_bone_name == "bag_r_03"
        )
        self.assertEqual(resolution.selected_child_name, "bag_r_04")
        self.assertEqual(plan.topology_ledger.resolved_branch_count, 1)


if __name__ == "__main__":
    unittest.main()
