from __future__ import annotations

import unittest

import bpy
import boneweaver

from tests.fixture_builders import clear_scene
from tests.test_branch_resolution import bag_fixture
from tests.test_physics_graph import state
from boneweaver.core.branch_resolution import resolve_branch
from boneweaver.core.graph_projection import build_proposals
from boneweaver.core.physics_graph import build_physics_graph
from boneweaver.core.runtime_store import get_plan


def _make_tip_scene():
    data = bpy.data.armatures.new("CleanupRigData")
    rig = bpy.data.objects.new("CleanupRig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
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
    for pose_bone in rig.pose.bones:
        pose_bone.select = True
    data.bones.active = data.bones["hair_01"]

    vertices = [
        (-0.05, 0.2, 0.0), (0.0, 0.6, 0.0), (0.05, 0.9, 0.0),
        (-0.05, 1.2, 0.0), (0.0, 1.6, 0.0), (0.05, 1.9, 0.0),
    ]
    mesh_data = bpy.data.meshes.new("CleanupMeshData")
    mesh_data.from_pydata(vertices, [(0, 1), (1, 2), (3, 4), (4, 5)], [])
    mesh = bpy.data.objects.new("CleanupMesh", mesh_data)
    bpy.context.scene.collection.objects.link(mesh)
    for name, indices in (("hair_01", (0, 1, 2)), ("hair_02", (3, 4, 5))):
        group = mesh.vertex_groups.new(name=name)
        group.add(indices, 1.0, "REPLACE")
    modifier = mesh.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = rig
    return rig, mesh


class VisualCleanupPureTests(unittest.TestCase):
    def test_linear_profile_connects_only_interior_bones(self) -> None:
        bones = (
            state("finger_01", None, ("finger_02",), (0, 0, 0)),
            state("finger_02", "finger_01", ("finger_03",), (0, 1, 0)),
            state("finger_03", "finger_02", (), (0, 2, 0)),
        )
        graph = build_physics_graph(bones)
        proposals = build_proposals(graph, bones, "VISUAL_CHAIN_CLEANUP")
        by_name = {item.bone_name: item for item in proposals}
        self.assertFalse(by_name["finger_01"].final_use_connect)
        self.assertTrue(by_name["finger_02"].final_use_connect)

    def test_branch_never_chooses_without_explicit_continuation(self) -> None:
        bones = bag_fixture()
        graph = build_physics_graph(bones)
        unresolved = build_proposals(graph, bones, "VISUAL_CHAIN_CLEANUP")
        self.assertNotIn("bag_r_03", {item.bone_name for item in unresolved})

        resolution = resolve_branch(
            "bag_r_03",
            bones,
            mode="MANUAL_ONLY",
            manual_selected_child="bag_r_04",
        )
        proposals = build_proposals(
            graph,
            bones,
            "VISUAL_CHAIN_CLEANUP",
            branch_resolutions=(resolution,),
        )
        by_name = {item.bone_name: item for item in proposals}
        self.assertEqual(by_name["bag_r_03"].proposed_tail, (0.0, 2.0, 0.0))
        self.assertTrue(by_name["bag_r_04"].final_use_connect)
        self.assertEqual(by_name["bag_r_03a_01"].role, "BRANCH_SIDE_ROOT")
        self.assertFalse(by_name["bag_r_03a_01"].final_use_connect)


class VisualCleanupPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        boneweaver.register()
        self.rig, self.mesh = _make_tip_scene()
        settings = bpy.context.scene.boneweaver_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40

    def tearDown(self) -> None:
        boneweaver.unregister()
        clear_scene()

    def _analyze_plan(self):
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        return get_plan(bpy.context.window_manager.boneweaver_runtime.plan_id)

    def test_tip_helper_inclusion_requires_explicit_visual_profile(self) -> None:
        settings = bpy.context.scene.boneweaver_settings
        default_plan = self._analyze_plan()
        self.assertEqual(default_plan.tip_helper_usage, "REFERENCE_ONLY")
        self.assertEqual(tuple(item.bone_name for item in default_plan.tip_helpers), ("hair_end",))
        self.assertNotIn("hair_end", {item.bone_name for item in default_plan.proposals})

        settings.tip_helper_usage = "INCLUDE_AS_PHYSICS_TERMINAL"
        rejected = self._analyze_plan()
        self.assertIn(
            "BONEWEAVER_TIP_HELPER_INCLUDE_PROFILE_REQUIRED",
            {item.code for item in rejected.issues},
        )

        settings.physics_profile = "VISUAL_CHAIN_CLEANUP"
        included = self._analyze_plan()
        helper = next(item for item in included.tip_helpers if item.bone_name == "hair_end")
        self.assertFalse(helper.reference_only)
        self.assertTrue(helper.mutation_target)
        self.assertTrue(helper.requires_own_tail)
        self.assertIn("hair_end", {item.bone_name for item in included.proposals})
        self.assertNotIn(
            "BONEWEAVER_TIP_HELPER_INCLUDE_PROFILE_REQUIRED",
            {item.code for item in included.issues},
        )


if __name__ == "__main__":
    unittest.main()
