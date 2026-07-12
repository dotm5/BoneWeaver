from __future__ import annotations

import unittest

import bpy

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from boneweaver.core.mesh_resolver import find_associated_meshes


class MeshResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()

    def tearDown(self) -> None:
        clear_scene()

    def test_resolves_by_armature_modifier_not_parent(self) -> None:
        rig = make_chain()
        mesh, modifier = make_bound_mesh(rig)
        mesh.parent = None
        bindings, issues = find_associated_meshes(rig)
        self.assertEqual([(item.object_name, item.modifier_name) for item in bindings], [(mesh.name, modifier.name)])
        self.assertEqual(issues, ())

    def test_duplicate_modifiers_to_same_armature_block(self) -> None:
        rig = make_chain()
        mesh, _ = make_bound_mesh(rig)
        duplicate = mesh.modifiers.new(name="Armature Duplicate", type="ARMATURE")
        duplicate.object = rig
        bindings, issues = find_associated_meshes(rig)
        self.assertEqual(bindings, ())
        self.assertIn("BONEWEAVER_AMBIGUOUS_ARMATURE_MODIFIER", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
