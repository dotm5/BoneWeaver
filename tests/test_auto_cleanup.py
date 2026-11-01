import json
import unittest
import bpy
import boneweaver
from mathutils import Vector
from tests.fixture_builders import clear_scene, make_quick_straight_chain, make_bound_mesh
from boneweaver.core.auto_cleanup import (
    build_cleanup_plan, apply_cleanup_plan, restore_cleanup_snapshot, _data_signature,
)


class AutoCleanupTests(unittest.TestCase):
    def setUp(self):
        boneweaver.unregister()
        clear_scene()
        boneweaver.register()

    def tearDown(self):
        boneweaver.unregister()
        clear_scene()

    def fixture(self):
        rig = make_quick_straight_chain()
        rig.data.bones['chain_04'].name = 'chain_end'
        mesh, mod = make_bound_mesh(rig)
        mesh.vertex_groups[0].name = 'chain_03'
        return rig, mesh

    def test_only_interior_reoriented_then_helper_deleted_exact_restore(self):
        rig, mesh = self.fixture()
        original = rig.data
        signature = _data_signature(original)
        plan = build_cleanup_plan(bpy.context)
        self.assertEqual(plan.delete_names, ('chain_end',))
        proposals = {p.bone_name: p for p in plan.quick_plan.proposals}
        self.assertTrue(proposals['chain_01'].skipped)
        self.assertTrue(proposals['chain_end'].skipped)
        self.assertEqual(proposals['chain_03'].target_tail, (0., 3., 0.))
        name, report = apply_cleanup_plan(bpy.context, plan)
        self.assertEqual(report['deleted'], 1)
        self.assertNotIn('chain_end', rig.data.bones)
        self.assertEqual(tuple(rig.data.bones['chain_03'].tail_local), (0., 3., 0.))
        self.assertEqual(tuple(rig.data.bones['chain_01'].tail_local), tuple(original.bones['chain_01'].tail_local))
        self.assertTrue(restore_cleanup_snapshot(bpy.context, name))
        self.assertEqual(rig.data, original)
        self.assertEqual(signature, _data_signature(rig.data))

    def test_tiny_weights_on_hidden_lod_protect_terminal(self):
        rig, mesh = self.fixture()
        lod, _ = make_bound_mesh(rig, name='LOD')
        lod.hide_viewport = True
        group = lod.vertex_groups.new(name='chain_end')
        group.add([0], 1e-10, 'REPLACE')
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_no_mesh_evidence_never_deletes(self):
        rig = make_quick_straight_chain()
        rig.data.bones['chain_04'].name = 'chain_end'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_unknown_weightless_leaf_preserved(self):
        rig, mesh = self.fixture()
        rig.data.bones['chain_end'].name = 'unknown_joint'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_ue_metadata_weightless_terminal_selected(self):
        rig, mesh = self.fixture()
        bone = rig.data.bones['chain_end']
        bone.name = 'joint_04'
        bone['orig_loc'] = (0., 1., 0.)
        bone['orig_quat'] = (1., 0., 0., 0.)
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ('joint_04',))

    def test_socket_and_attachment_are_retained(self):
        rig, mesh = self.fixture()
        rig.data.bones['chain_end']['is_socket'] = True
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())
        del rig.data.bones['chain_end']['is_socket']
        empty = bpy.data.objects.new('Attachment', None)
        bpy.context.scene.collection.objects.link(empty)
        empty.parent, empty.parent_type, empty.parent_bone = rig, 'BONE', 'chain_end'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_external_constraint_protects_terminal(self):
        rig, mesh = self.fixture()
        empty = bpy.data.objects.new('Follower', None)
        bpy.context.scene.collection.objects.link(empty)
        c = empty.constraints.new('COPY_LOCATION')
        c.target, c.subtarget = rig, 'chain_end'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_weight_change_invalidates_plan(self):
        rig, mesh = self.fixture()
        plan = build_cleanup_plan(bpy.context)
        mesh.vertex_groups.new(name='chain_end').add([0], .2, 'REPLACE')
        original = rig.data
        with self.assertRaises(ValueError):
            apply_cleanup_plan(bpy.context, plan)
        self.assertEqual(original, rig.data)

    def test_post_delete_failure_rolls_back_topology(self):
        rig, mesh = self.fixture()
        original = rig.data
        signature = _data_signature(original)
        with self.assertRaises(RuntimeError):
            apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context), validator=lambda *_: False)
        self.assertEqual(original, rig.data)
        self.assertEqual(signature, _data_signature(rig.data))

    def test_restore_rejects_later_edit(self):
        rig, mesh = self.fixture()
        name, _ = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        rig.data.bones['chain_02']['user_edit'] = 1
        self.assertFalse(restore_cleanup_snapshot(bpy.context, name))
        self.assertNotIn('chain_end', rig.data.bones)

    def test_second_run_never_recursively_peels_weighted_parent(self):
        rig, mesh = self.fixture()
        name, _ = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        plan = build_cleanup_plan(bpy.context)
        self.assertEqual(plan.delete_names, ())
        for p in plan.quick_plan.proposals:
            self.assertLess((Vector(p.target_tail)-rig.data.bones[p.bone_name].tail_local).length, 1e-6)
        data = rig.data
        repeated, result = apply_cleanup_plan(bpy.context, plan)
        self.assertEqual(result['status'], 'NOOP')
        self.assertEqual(repeated, name)
        self.assertEqual(rig.data, data)

    def test_shared_data_other_object_unchanged(self):
        rig, mesh = self.fixture()
        other = rig.copy()
        bpy.context.scene.collection.objects.link(other)
        signature = _data_signature(other.data)
        apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        self.assertNotEqual(rig.data, other.data)
        self.assertEqual(signature, _data_signature(other.data))

    def test_operator_and_restore(self):
        rig, mesh = self.fixture()
        self.assertEqual(bpy.ops.boneweaver.auto_cleanup(), {'FINISHED'})
        self.assertNotIn('chain_end', rig.data.bones)
        self.assertEqual(bpy.ops.boneweaver.restore_auto_cleanup(), {'FINISHED'})
        self.assertIn('chain_end', rig.data.bones)

    def test_static_pose_deformation_preserved_and_restored(self):
        rig, mesh = self.fixture()
        bone = rig.pose.bones['chain_02']
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler.z = .45
        bone.location.x = .15
        bpy.context.view_layer.update()
        from boneweaver.core.auto_cleanup import _capture_neutral, _capture_delta, _pose_state
        before = _capture_neutral(rig)
        pose = _pose_state(rig)
        name, _ = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        after = _capture_neutral(rig)
        self.assertLess(_capture_delta(before[mesh.name], after[mesh.name])[0], 1e-6)
        self.assertTrue(restore_cleanup_snapshot(bpy.context, name))
        self.assertEqual(pose, _pose_state(rig))

    def test_driver_target_retains_helper(self):
        rig, mesh = self.fixture()
        driver = mesh.driver_add('location', 0).driver
        variable = driver.variables.new()
        variable.type = 'TRANSFORMS'
        variable.targets[0].id = rig
        variable.targets[0].bone_target = 'chain_end'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_hook_modifier_retains_helper(self):
        rig, mesh = self.fixture()
        hook = mesh.modifiers.new('Hook', 'HOOK')
        hook.object, hook.subtarget = rig, 'chain_end'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_bbone_handle_retains_helper(self):
        rig, mesh = self.fixture()
        rig.data.bones['chain_02'].bbone_custom_handle_end = rig.data.bones['chain_end']
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ())

    def test_deleted_helper_pose_display_and_ik_settings_restore(self):
        rig, mesh = self.fixture()
        shape = bpy.data.objects.new('CustomShape', None)
        bpy.context.scene.collection.objects.link(shape)
        bone = rig.pose.bones['chain_end']
        bone.custom_shape = shape
        bone.lock_ik_x = True
        bone.ik_stiffness_y = .4
        name, _ = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        self.assertTrue(restore_cleanup_snapshot(bpy.context, name))
        restored = rig.pose.bones['chain_end']
        self.assertEqual(restored.custom_shape, shape)
        self.assertTrue(restored.lock_ik_x)
        self.assertAlmostEqual(restored.ik_stiffness_y, .4)

    def test_restore_detects_envelope_edit(self):
        rig, mesh = self.fixture()
        name, _ = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        rig.data.bones['chain_02'].envelope_distance += .1
        self.assertFalse(restore_cleanup_snapshot(bpy.context, name))

    def test_numbered_direction_leaf_with_weighted_parent(self):
        rig, mesh = self.fixture()
        rig.data.bones['chain_end'].name = 'chain_04'
        self.assertEqual(build_cleanup_plan(bpy.context).delete_names, ('chain_04',))

    def test_active_action_is_rejected_without_mutation(self):
        rig, mesh = self.fixture()
        bone = rig.pose.bones['chain_02']
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler.z = 0.1
        bone.keyframe_insert('rotation_euler', frame=1)
        bone.rotation_euler.z = .6
        bone.keyframe_insert('rotation_euler', frame=10)
        bpy.context.scene.frame_set(5)
        from boneweaver.core.auto_cleanup import _capture_neutral, _capture_delta
        from boneweaver.core.animation_basis import capture_animation_state, animation_state_matches
        animation = capture_animation_state(rig)
        original = rig.data
        with self.assertRaises(ValueError):
            build_cleanup_plan(bpy.context)
        self.assertEqual(original, rig.data)
        self.assertTrue(animation_state_matches(rig, animation))

    def test_zero_sum_branch_does_not_invent_positive_z(self):
        rig, mesh = self.fixture()
        bpy.ops.object.mode_set(mode='EDIT')
        parent = rig.data.edit_bones['chain_02']
        rig.data.edit_bones['chain_03'].head = (1, 1, 0)
        extra = rig.data.edit_bones.new('opposite')
        extra.head, extra.tail, extra.parent = (-1, 1, 0), (-1, 1, .2), parent
        bpy.ops.object.mode_set(mode='OBJECT')
        plan = build_cleanup_plan(bpy.context)
        p = next(p for p in plan.quick_plan.proposals if p.bone_name=='chain_02')
        self.assertTrue(p.skipped)
        self.assertEqual(p.source, 'KEEP_CANCELLED_BRANCH')

    def add_bone(self, rig, name, parent, head=(0, 3, 0)):
        bpy.ops.object.mode_set(mode='EDIT')
        bone = rig.data.edit_bones.new(name)
        bone.parent = rig.data.edit_bones[parent]
        bone.head, bone.tail = head, (head[0], head[1], head[2]+.2)
        bpy.ops.object.mode_set(mode='OBJECT')

    def test_zero_corrective_subtree_and_fan_cleanup(self):
        rig, mesh = self.fixture()
        self.add_bone(rig, 'chain_03_SR', 'chain_03', (0, 2, 0))
        self.add_bone(rig, 'chain_03_ST', 'chain_03_SR', (0, 2, 0))
        self.add_bone(rig, 'MassCenter', 'chain_03')
        self.add_bone(rig, 'MassCenter_1', 'MassCenter')
        self.add_bone(rig, 'MassCenter_2', 'MassCenter')
        original = rig.data
        plan = build_cleanup_plan(bpy.context, mode='CLEANUP')
        self.assertEqual(set(plan.delete_names), {'chain_end', 'chain_03_SR', 'chain_03_ST', 'MassCenter', 'MassCenter_1', 'MassCenter_2'})
        name, result = apply_cleanup_plan(bpy.context, plan)
        self.assertEqual((result['reoriented'], result['connected'], result['deleted']), (0, 0, 6))
        for bone in rig.data.bones:
            self.assertEqual(bone.matrix_local, original.bones[bone.name].matrix_local)
            self.assertEqual(bone.use_connect, original.bones[bone.name].use_connect)
        self.assertTrue(restore_cleanup_snapshot(bpy.context, name))

    def test_weighted_descendant_retains_zero_support_chain(self):
        rig, mesh = self.fixture()
        self.add_bone(rig, 'MassCenter', 'chain_03')
        self.add_bone(rig, 'MassCenter_1', 'MassCenter')
        mesh.vertex_groups.new(name='MassCenter_1').add([0], 1e-10, 'REPLACE')
        plan = build_cleanup_plan(bpy.context)
        self.assertNotIn('MassCenter', plan.delete_names)
        self.assertNotIn('MassCenter_1', plan.delete_names)
        self.assertEqual(dict(plan.decisions)['MassCenter'], 'KEEP_REQUIRED_ANCESTOR')

    def test_gameplay_subtrees_protected_in_all_modes(self):
        for mode in ('AUTO', 'REORIENT', 'CONNECT', 'CLEANUP'):
            with self.subTest(mode=mode):
                rig, mesh = self.fixture()
                names = ['ik_hand_gun', 'WeaponProp01', 'CameraPosition', 'HitCase', 'SocketADS', 'NekoBotHit']
                for i, n in enumerate(names):
                    self.add_bone(rig, n, 'chain_03', (i+1, 2, 0))
                    self.add_bone(rig, n+'_end', n, (i+1, 3, 0))
                original = rig.data
                plan = build_cleanup_plan(bpy.context, mode=mode)
                snapshot, result = apply_cleanup_plan(bpy.context, plan)
                for n in names:
                    for name in (n, n+'_end'):
                        self.assertIn(name, rig.data.bones)
                        self.assertLess(max(abs(a-b) for ra, rb in zip(rig.data.bones[name].matrix_local, original.bones[name].matrix_local) for a,b in zip(ra,rb)), 1e-6)
                        self.assertEqual(rig.data.bones[name].use_connect, original.bones[name].use_connect)
                if result['status'] != 'NOOP':
                    self.assertTrue(restore_cleanup_snapshot(bpy.context, snapshot))
                clear_scene()

    def test_mode_isolation_switch_and_repeat(self):
        rig, mesh = self.fixture()
        first, reorient = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context, mode='REORIENT'))
        self.assertEqual((reorient['deleted'], reorient['connected']), (0, 0))
        self.assertIn('chain_end', rig.data.bones)
        second, connect = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context, mode='CONNECT'))
        self.assertEqual((connect['deleted'], connect['reoriented']), (0, 0))
        self.assertGreater(connect['connected'], 0)
        third, clean = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context, mode='CLEANUP'))
        self.assertEqual((clean['connected'], clean['reoriented'], clean['deleted']), (0, 0, 1))
        repeated, result = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context, mode='CLEANUP'))
        self.assertEqual(result['status'], 'NOOP')
        for name in (third, second, first):
            self.assertTrue(restore_cleanup_snapshot(bpy.context, name))

    def test_invalid_mode_rejected(self):
        self.fixture()
        with self.assertRaises(ValueError):
            build_cleanup_plan(bpy.context, mode='INVALID')

    def test_generic_descendant_of_weapon_node_is_protected(self):
        rig, mesh = self.fixture()
        self.add_bone(rig, 'WeaponProp01', 'chain_03')
        self.add_bone(rig, 'generic_end', 'WeaponProp01')
        self.add_bone(rig, 'generic_tip', 'generic_end')
        plan = build_cleanup_plan(bpy.context)
        self.assertNotIn('generic_end', plan.delete_names)
        self.assertNotIn('generic_tip', plan.delete_names)
        proposals = {p.bone_name: p for p in plan.quick_plan.proposals}
        self.assertTrue(proposals['generic_end'].skipped)
