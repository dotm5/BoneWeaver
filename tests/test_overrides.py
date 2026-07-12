from __future__ import annotations

import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_chain
from ue_chain_prep.core.overrides import (
    armature_structural_fingerprint,
    find_terminal_override,
    find_branch_override,
    remove_stale_overrides,
    upsert_branch_override,
    upsert_terminal_override,
)


class OverrideScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.settings = bpy.context.scene.uecp_settings
        self.settings.terminal_overrides.clear()
        self.settings.branch_overrides.clear()
        self.fingerprint = armature_structural_fingerprint(self.rig)

    def tearDown(self) -> None:
        ue_chain_prep.unregister()
        clear_scene()

    def test_terminal_upsert_is_idempotent_within_scope(self) -> None:
        first = upsert_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            bone_name="Bone_2",
            chain_id="chain-a",
            mode="EXPLICIT_DIRECTION_LENGTH",
            direction=(1, 0, 0),
            length=1.0,
        )
        self.assertEqual(first.armature_data_name, self.rig.data.name)
        self.assertEqual(first.armature_structural_fingerprint, self.fingerprint)
        self.assertEqual(first.bone_name, "Bone_2")
        self.assertEqual(first.chain_id, "chain-a")
        found, legacy = find_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            bone_name="Bone_2",
            chain_id="chain-a",
        )
        self.assertIsNotNone(found)
        self.assertFalse(legacy)
        second = upsert_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            bone_name="Bone_2",
            chain_id="chain-a",
            mode="EXPLICIT_DIRECTION_LENGTH",
            direction=(0, 1, 0),
            length=2.0,
        )
        self.assertEqual(len(self.settings.terminal_overrides), 1)
        self.assertEqual(first.as_pointer(), second.as_pointer())
        self.assertEqual(tuple(second.direction), (0.0, 1.0, 0.0))
        self.assertEqual(second.length, 2.0)

    def test_different_fingerprint_does_not_match_or_cross_apply(self) -> None:
        upsert_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint="old-fingerprint",
            bone_name="Bone_2",
            chain_id="chain-a",
            mode="EXPLICIT_DIRECTION_LENGTH",
            length=1.0,
        )
        item, legacy = find_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            bone_name="Bone_2",
            chain_id="chain-a",
        )
        self.assertIsNone(item)
        self.assertFalse(legacy)
        removed = remove_stale_overrides(
            self.settings,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
        )
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.settings.terminal_overrides), 0)

    def test_legacy_unscoped_override_is_retained_but_not_applied(self) -> None:
        legacy_item = self.settings.terminal_overrides.add()
        legacy_item.bone_name = "Bone_2"
        legacy_item.mode = "EXPLICIT_DIRECTION_LENGTH"
        legacy_item.length = 2.0
        item, legacy = find_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            bone_name="Bone_2",
            chain_id="chain-a",
        )
        self.assertIsNone(item)
        self.assertTrue(legacy)
        remove_stale_overrides(
            self.settings,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
        )
        self.assertEqual(len(self.settings.terminal_overrides), 1)

    def test_branch_upsert_replaces_selected_child_in_scope(self) -> None:
        upsert_branch_override(
            self.settings.branch_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            branch_bone_name="Bone_1",
            selected_child_name="ChildA",
        )
        upsert_branch_override(
            self.settings.branch_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
            branch_bone_name="Bone_1",
            selected_child_name="ChildB",
        )
        self.assertEqual(len(self.settings.branch_overrides), 1)
        self.assertEqual(self.settings.branch_overrides[0].selected_child_name, "ChildB")

    def test_stale_cleanup_retains_other_armature_scopes(self) -> None:
        upsert_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint="stale-a",
            bone_name="Bone_2",
            chain_id="chain-a",
            mode="EXPLICIT_DIRECTION_LENGTH",
            length=1.0,
        )
        upsert_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name="RigBData",
            armature_structural_fingerprint="valid-b",
            bone_name="Bone_2",
            chain_id="chain-b",
            mode="EXPLICIT_DIRECTION_LENGTH",
            length=2.0,
        )
        upsert_branch_override(
            self.settings.branch_overrides,
            armature_data_name="RigBData",
            armature_structural_fingerprint="valid-b",
            branch_bone_name="Branch",
            selected_child_name="Child",
        )
        removed = remove_stale_overrides(
            self.settings,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=self.fingerprint,
        )
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.settings.terminal_overrides), 1)
        other_terminal, legacy = find_terminal_override(
            self.settings.terminal_overrides,
            armature_data_name="RigBData",
            armature_structural_fingerprint="valid-b",
            bone_name="Bone_2",
            chain_id="chain-b",
        )
        self.assertIsNotNone(other_terminal)
        self.assertFalse(legacy)
        other_branch, legacy = find_branch_override(
            self.settings.branch_overrides,
            armature_data_name="RigBData",
            armature_structural_fingerprint="valid-b",
            branch_bone_name="Branch",
        )
        self.assertIsNotNone(other_branch)
        self.assertFalse(legacy)


if __name__ == "__main__":
    unittest.main()
