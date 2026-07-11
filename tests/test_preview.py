from __future__ import annotations

import unittest

import bpy

from tests.fixture_builders import clear_scene
from ue_chain_prep.controllers.preview import PreviewController
from ue_chain_prep.ui import draw


class PreviewLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        PreviewController.disable(bpy.context)

    def tearDown(self) -> None:
        PreviewController.disable(bpy.context)
        clear_scene()

    def test_handler_uses_cache_and_creates_no_scene_objects(self) -> None:
        before = tuple(bpy.data.objects.keys())
        cache = (((0.0,0.0,0.0), (0.0,1.0,0.0), (0.2,0.8,1.0,1.0)),)
        PreviewController.enable(bpy.context, cache)
        self.assertTrue(PreviewController.is_enabled())
        self.assertEqual(draw.preview_cache(), cache)
        self.assertEqual(tuple(bpy.data.objects.keys()), before)
        PreviewController.disable(bpy.context)
        self.assertFalse(PreviewController.is_enabled())
        self.assertEqual(tuple(bpy.data.objects.keys()), before)


if __name__ == "__main__":
    unittest.main()
