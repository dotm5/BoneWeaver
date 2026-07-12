from __future__ import annotations

import types
import unittest
from unittest.mock import patch

import bpy
import boneweaver

from tests.fixture_builders import clear_scene
from tests.test_physics_graph import state
from boneweaver.core.armature_reader import read_bone_states
from boneweaver.controllers.semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)
from boneweaver.controllers.session import SessionController
from boneweaver.core.mesh_scan_cache import MeshScanCache
from boneweaver.core.runtime_store import (
    get_plan,
    get_semantic_discovery,
    get_used_semantic_scope,
)
from boneweaver.core.semantic_discovery import build_semantic_discovery_plan
from boneweaver.core.semantic_serialization import (
    semantic_discovery_plan_from_json,
    semantic_discovery_plan_to_json,
)


def _hair_states():
    return (
        state("hair_l_01", None, ("hair_l_02",), (0, 0, 0), tail=(0, 0.2, 0)),
        state("hair_l_02", "hair_l_01", ("hair_l_03",), (0, 1, 0), tail=(0, 1.2, 0)),
        state("hair_l_03", "hair_l_02", (), (0, 2, 0), tail=(0, 2.2, 0)),
    )


def _weight(name, *, sample_count=8, total=8.0, confidence=0.95, warnings=()):
    return types.SimpleNamespace(
        bone_name=name,
        sample_count=sample_count,
        effective_sample_count=float(sample_count),
        total_statistical_weight=total,
        confidence=confidence,
        warnings=tuple(warnings),
    )


def _make_weighted_hair_scene():
    data = bpy.data.armatures.new("HairRigData")
    rig = bpy.data.objects.new("HairRig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    parent = None
    for index in range(3):
        bone = data.edit_bones.new(f"hair_l_0{index + 1}")
        bone.head = (0.0, float(index), 0.0)
        bone.tail = (0.0, float(index) + 0.2, 0.0)
        bone.parent = parent
        bone.use_connect = False
        parent = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in rig.pose.bones:
        pose_bone.select = pose_bone.name == "hair_l_01"
    data.bones.active = data.bones["hair_l_01"]

    vertices = []
    for index in range(3):
        base = float(index)
        vertices.extend(
            [(-0.05, base + 0.25, 0.0), (0.0, base + 0.60, 0.0), (0.05, base + 0.95, 0.0)]
        )
    mesh_data = bpy.data.meshes.new("HairMeshData")
    mesh_data.from_pydata(
        vertices,
        [(index * 3, index * 3 + 1) for index in range(3)]
        + [(index * 3 + 1, index * 3 + 2) for index in range(3)],
        [],
    )
    mesh = bpy.data.objects.new("HairMesh", mesh_data)
    bpy.context.scene.collection.objects.link(mesh)
    for index in range(3):
        group = mesh.vertex_groups.new(name=f"hair_l_0{index + 1}")
        group.add([index * 3, index * 3 + 1, index * 3 + 2], 1.0, "REPLACE")
    modifier = mesh.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = rig
    return rig, mesh


class SemanticDiscoveryCoreTests(unittest.TestCase):
    def test_weighted_numbered_hair_chain_is_auto_include(self) -> None:
        states = _hair_states()
        plan = build_semantic_discovery_plan(
            states,
            armature_object_name="Rig",
            armature_fingerprint="fingerprint",
            weight_summaries=tuple(_weight(item.name) for item in states),
        )
        self.assertEqual(len(plan.chains), 1)
        self.assertEqual(plan.chains[0].bone_names, tuple(item.name for item in states))
        self.assertEqual(plan.chains[0].discovery_class, "AUTO_INCLUDE")
        self.assertTrue(all(item.discovery_class == "AUTO_INCLUDE" for item in plan.bone_evidence))

    def test_missing_or_insufficient_weight_never_auto_includes(self) -> None:
        states = _hair_states()
        missing = build_semantic_discovery_plan(states)
        self.assertFalse(any(chain.discovery_class == "AUTO_INCLUDE" for chain in missing.chains))
        self.assertTrue(all(
            "BONEWEAVER_SEMANTIC_WEIGHT_EVIDENCE_UNAVAILABLE" in item.reason_codes
            for item in missing.bone_evidence
        ))

        insufficient = build_semantic_discovery_plan(
            states,
            weight_summaries=tuple(
                _weight(
                    item.name,
                    sample_count=2,
                    total=1.0e-15,
                    confidence=1.0,
                    warnings=("BONEWEAVER_INSUFFICIENT_WEIGHT_CLOUD",),
                )
                for item in states
            ),
        )
        self.assertFalse(any(
            chain.discovery_class == "AUTO_INCLUDE" for chain in insufficient.chains
        ))
        self.assertTrue(all(
            "BONEWEAVER_SEMANTIC_NO_WEIGHT_SUPPORT" in item.reason_codes
            for item in insufficient.bone_evidence
        ))

    def test_hard_exclusions_override_positive_tokens(self) -> None:
        cases = (
            state("hair_twist_01", None, (), (0, 0, 0)),
            state("hair_socket_01", None, (), (0, 0, 0)),
            state("hair_ik_01", None, (), (0, 0, 0)),
            state("hair_face_01", None, (), (0, 0, 0)),
        )
        for bone in cases:
            with self.subTest(name=bone.name):
                plan = build_semantic_discovery_plan(
                    (bone,), weight_summaries=(_weight(bone.name),),
                )
                evidence = plan.bone_evidence[0]
                self.assertEqual(evidence.discovery_class, "EXCLUDE")
                self.assertIn(evidence.bone_name, plan.excluded_bones)

    def test_main_skeleton_has_zero_candidate_chains(self) -> None:
        states = (
            state("root", None, ("pelvis",), (0, 0, 0)),
            state("pelvis", "root", ("spine_01",), (0, 1, 0)),
            state("spine_01", "pelvis", ("neck_01",), (0, 2, 0)),
            state("neck_01", "spine_01", ("head",), (0, 3, 0)),
            state("head", "neck_01", (), (0, 4, 0)),
        )
        plan = build_semantic_discovery_plan(
            states, weight_summaries=tuple(_weight(item.name) for item in states),
        )
        self.assertFalse(plan.chains)
        self.assertEqual(set(plan.excluded_bones), {item.name for item in states})

    def test_plan_ids_and_json_are_deterministic_and_strict(self) -> None:
        states = _hair_states()
        weights = tuple(_weight(item.name) for item in states)
        first = build_semantic_discovery_plan(
            states, armature_fingerprint="fingerprint", weight_summaries=weights,
        )
        second = build_semantic_discovery_plan(
            tuple(reversed(states)),
            armature_fingerprint="fingerprint",
            weight_summaries=tuple(reversed(weights)),
        )
        first_json = semantic_discovery_plan_to_json(first)
        self.assertEqual(first, second)
        self.assertEqual(first_json, semantic_discovery_plan_to_json(second))
        self.assertEqual(semantic_discovery_plan_from_json(first_json), first)
        with self.assertRaises(ValueError):
            semantic_discovery_plan_from_json(first_json[:-1] + ',"unknown":true}')


class SemanticDiscoveryRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        boneweaver.register()
        self.rig, self.mesh = _make_weighted_hair_scene()

    def tearDown(self) -> None:
        boneweaver.unregister()
        clear_scene()

    def _bone_state(self):
        return tuple(
            (
                bone.name,
                tuple(bone.head_local),
                tuple(bone.tail_local),
                tuple(value for row in bone.matrix_local for value in row),
                bone.use_connect,
                self.rig.pose.bones[bone.name].select,
            )
            for bone in self.rig.data.bones
        )

    def _weights(self):
        return tuple(
            (
                vertex.index,
                tuple(sorted((item.group, float(item.weight)) for item in vertex.groups)),
            )
            for vertex in self.mesh.data.vertices
        )

    def test_fresh_discovery_scans_once_is_read_only_and_can_auto_include(self) -> None:
        before_bones = self._bone_state()
        before_weights = self._weights()
        scan_calls = []
        original_scan = MeshScanCache.scan

        def counted_scan(*args, **kwargs):
            scan_calls.append((args, kwargs))
            return original_scan(*args, **kwargs)

        with patch.object(MeshScanCache, "scan", side_effect=counted_scan):
            self.assertEqual(
                bpy.ops.boneweaver.discover_secondary_chains(), {"FINISHED"},
            )

        session = get_semantic_discovery()
        self.assertIsNotNone(session)
        self.assertEqual(len(scan_calls), 1)
        self.assertTrue(any(
            chain.discovery_class == "AUTO_INCLUDE" for chain in session.plan.chains
        ), repr((session.plan.chains, session.plan.bone_evidence)))
        self.assertEqual(self._bone_state(), before_bones)
        self.assertEqual(self._weights(), before_weights)
        self.assertEqual(bpy.context.window_manager.boneweaver_runtime.state, "IDLE")

    def test_confirmation_is_required_before_selection_and_frozen_scope(self) -> None:
        plan = SemanticDiscoveryController.discover(bpy.context)
        self.assertEqual(len(plan.chains), 1)
        with self.assertRaisesRegex(
            SemanticDiscoveryRuntimeError, "BONEWEAVER_SEMANTIC_CONFIRMATION_REQUIRED",
        ):
            SemanticDiscoveryController.use_confirmed_chains(bpy.context)

        before_geometry = tuple(
            (bone.name, tuple(bone.head_local), tuple(bone.tail_local), bone.use_connect)
            for bone in self.rig.data.bones
        )
        chain = plan.chains[0]
        selected = SemanticDiscoveryController.select_chain(
            bpy.context, chain.discovery_id,
        )
        self.assertEqual(set(selected), set(chain.bone_names))
        scope = SemanticDiscoveryController.use_confirmed_chains(bpy.context)
        self.assertEqual(set(scope.bone_names), set(chain.bone_names))
        self.assertEqual(scope.confirmed_chain_ids, (chain.discovery_id,))
        self.assertEqual(
            tuple(
                (bone.name, tuple(bone.head_local), tuple(bone.tail_local), bone.use_connect)
                for bone in self.rig.data.bones
            ),
            before_geometry,
        )

        SessionController.on_undo_post(None)
        self.assertIsNone(get_semantic_discovery())
        self.assertIsNone(get_used_semantic_scope())
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertFalse(runtime.semantic_discovery_active)
        self.assertFalse(runtime.semantic_scope_used)

    def test_partial_analyze_cache_is_not_reused_for_full_armature_discovery(self) -> None:
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_plan(runtime.plan_id)
        self.assertEqual(tuple(state.name for state in plan.bone_states), ("hair_l_01",))
        all_bone_states = read_bone_states(
            self.rig, tuple(sorted(bone.name for bone in self.rig.data.bones)),
        )
        self.assertEqual(
            SemanticDiscoveryController._reusable_weight_clouds(
                bpy.context, self.rig, all_bone_states,
            ),
            (),
        )

        original_scan = MeshScanCache.scan
        scan_calls = 0

        def counted_scan(*args, **kwargs):
            nonlocal scan_calls
            scan_calls += 1
            return original_scan(*args, **kwargs)

        with patch.object(MeshScanCache, "scan", side_effect=counted_scan):
            discovered = SemanticDiscoveryController.discover(bpy.context)

        self.assertEqual(scan_calls, 1)
        self.assertTrue(any(
            set(chain.bone_names) == {"hair_l_01", "hair_l_02", "hair_l_03"}
            for chain in discovered.chains
        ))

    def test_full_analyze_weight_cloud_cache_is_rejected_after_weight_edit(self) -> None:
        for pose_bone in self.rig.pose.bones:
            pose_bone.select = True
        self.assertEqual(bpy.ops.boneweaver.analyze(), {"FINISHED"})
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_plan(runtime.plan_id)
        bone_states = read_bone_states(
            self.rig, tuple(state.name for state in plan.bone_states),
        )
        self.assertEqual(
            SemanticDiscoveryController._reusable_weight_clouds(
                bpy.context, self.rig, bone_states,
            ),
            plan.weight_clouds,
        )

        self.mesh.vertex_groups["hair_l_01"].add([0], 0.125, "REPLACE")

        self.assertEqual(
            SemanticDiscoveryController._reusable_weight_clouds(
                bpy.context, self.rig, bone_states,
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
