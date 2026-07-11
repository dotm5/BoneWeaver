from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_plan_cache_honors_public_preview_filters(self) -> None:
        nodes = (
            SimpleNamespace(node_id="a", joint_position=(0, 0, 0)),
            SimpleNamespace(node_id="b", joint_position=(0, 1, 0)),
            SimpleNamespace(node_id="c", joint_position=(0, 2, 0)),
        )
        edges = (
            SimpleNamespace(parent_node_id="a", child_node_id="b", kind="HIERARCHY_SEGMENT"),
            SimpleNamespace(parent_node_id="b", child_node_id="c", kind="VIRTUAL_TIP_SEGMENT"),
        )
        plan = SimpleNamespace(physics_graph=SimpleNamespace(nodes=nodes, edges=edges))
        settings = SimpleNamespace(preview_show_joint_graph=True, preview_show_virtual_tips=False)
        self.assertEqual(1, len(draw.build_plan_cache(plan, settings)))
        settings.preview_show_joint_graph = False
        self.assertEqual(0, len(draw.build_plan_cache(plan, settings)))

    def test_draw_callback_uses_actual_viewport_dimensions(self) -> None:
        uniforms = {}
        shader = SimpleNamespace(
            bind=lambda: None,
            uniform_float=lambda name, value: uniforms.__setitem__(name, value),
        )
        batch = SimpleNamespace(draw=lambda _shader: None)
        draw._CACHE = (((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 1.0, 1.0)),)
        draw._GPU_CACHE = (shader, ((batch, (1.0, 1.0, 1.0, 1.0)),))
        fake_gpu = SimpleNamespace(
            state=SimpleNamespace(viewport_get=lambda: (0, 0, 1920, 1080))
        )

        with patch.dict(sys.modules, {"gpu": fake_gpu}):
            draw._draw_callback()

        self.assertEqual((1920.0, 1080.0), uniforms["viewportSize"])


if __name__ == "__main__":
    unittest.main()
