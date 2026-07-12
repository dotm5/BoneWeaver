"""Viewport handler consuming a frozen line cache; no analysis runs per frame."""

from __future__ import annotations

import bpy


_HANDLER = None
_CACHE = ()
_GPU_CACHE = None


def _build_gpu_cache():
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    batches = tuple(
        (batch_for_shader(shader, "LINES", {"pos": (start, end)}), color)
        for start, end, color in _CACHE
    )
    return shader, batches


def _ensure_gpu_cache():
    global _GPU_CACHE
    if _GPU_CACHE is None:
        _GPU_CACHE = _build_gpu_cache()
    return _GPU_CACHE


def _draw_callback():
    if not _CACHE:
        return
    import gpu

    _, _, width, height = gpu.state.viewport_get()
    viewport_size = (max(1.0, float(width)), max(1.0, float(height)))
    shader, batches = _ensure_gpu_cache()
    for batch, color in batches:
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("viewportSize", viewport_size)
        shader.uniform_float("lineWidth", 2.0)
        batch.draw(shader)


def _enable_preview(cache):
    global _HANDLER, _CACHE, _GPU_CACHE
    _disable_preview()
    _CACHE = tuple(cache)
    _GPU_CACHE = None
    _HANDLER = bpy.types.SpaceView3D.draw_handler_add(_draw_callback, (), "WINDOW", "POST_VIEW")


def _disable_preview():
    global _HANDLER, _CACHE, _GPU_CACHE
    if _HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_HANDLER, "WINDOW")
    _HANDLER = None
    _CACHE = ()
    _GPU_CACHE = None


def is_preview_enabled():
    return _HANDLER is not None


def preview_cache():
    return _CACHE


def build_plan_cache(plan, settings=None):
    nodes = {node.node_id: node for node in plan.physics_graph.nodes}
    lines = []
    for edge in plan.physics_graph.edges:
        if settings is not None and not settings.preview_show_joint_graph:
            continue
        if settings is not None and edge.kind == "VIRTUAL_TIP_SEGMENT" and not settings.preview_show_virtual_tips:
            continue
        color = (1.0, 0.55, 0.1, 1.0) if edge.kind == "VIRTUAL_TIP_SEGMENT" else (0.1, 0.7, 1.0, 1.0)
        lines.append((nodes[edge.parent_node_id].joint_position, nodes[edge.child_node_id].joint_position, color))
    return tuple(lines)
