"""Viewport handler consuming a frozen line cache; no analysis runs per frame."""

from __future__ import annotations

import bpy


_HANDLER = None
_CACHE = ()


def _draw_callback():
    if not _CACHE:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    for start, end, color in _CACHE:
        batch = batch_for_shader(shader, "LINES", {"pos": (start, end)})
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("viewportSize", (1.0, 1.0))
        shader.uniform_float("lineWidth", 2.0)
        batch.draw(shader)


def enable_preview(cache):
    global _HANDLER, _CACHE
    disable_preview()
    _CACHE = tuple(cache)
    _HANDLER = bpy.types.SpaceView3D.draw_handler_add(_draw_callback, (), "WINDOW", "POST_VIEW")


def disable_preview():
    global _HANDLER, _CACHE
    if _HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_HANDLER, "WINDOW")
    _HANDLER = None
    _CACHE = ()


def is_preview_enabled():
    return _HANDLER is not None


def preview_cache():
    return _CACHE
