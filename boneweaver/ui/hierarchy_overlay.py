"""GPU hierarchy overlay drawing from frozen world-space cache only."""

from __future__ import annotations

from dataclasses import dataclass

import bpy


@dataclass(frozen=True, slots=True)
class HierarchyOverlayOptions:
    show_names: bool = True
    show_parent: bool = True
    show_side_branches: bool = True
    show_tip_helpers: bool = True


_VIEW_HANDLER = None
_TEXT_HANDLER = None
_CACHE = None
_GPU_BATCHES = ()
_OPTIONS = HierarchyOverlayOptions()


def _role_visible(role: str) -> bool:
    if role == "PARENT_CONTEXT":
        return _OPTIONS.show_parent
    if role == "SIDE_BRANCH":
        return _OPTIONS.show_side_branches
    if role in {"TIP_HELPER", "EXCLUDED_HELPER"}:
        return _OPTIONS.show_tip_helpers
    return True


def _build_gpu_batches(cache):
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    batches = tuple(
        (
            batch_for_shader(shader, "LINES", {"pos": (segment.start, segment.end)}),
            segment.color,
            segment.width,
            segment.role,
        )
        for segment in cache.segments
    )
    return shader, batches


def _draw_view_callback():
    if _CACHE is None or not _GPU_BATCHES:
        return
    import gpu

    _, _, width, height = gpu.state.viewport_get()
    viewport_size = (max(1.0, float(width)), max(1.0, float(height)))
    shader, batches = _GPU_BATCHES
    # The inspection overlay is an interaction aid, so it must remain readable
    # through the character mesh.  POST_VIEW inherits the viewport depth state;
    # without overriding it the local chain can be completely occluded.
    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("ALPHA")
    try:
        for batch, color, line_width, role in batches:
            if not _role_visible(role):
                continue
            shader.bind()
            shader.uniform_float("color", color)
            shader.uniform_float("viewportSize", viewport_size)
            shader.uniform_float("lineWidth", line_width)
            batch.draw(shader)
    finally:
        gpu.state.blend_set("NONE")
        gpu.state.depth_test_set("LESS_EQUAL")


def _draw_text_callback():
    if _CACHE is None or not _OPTIONS.show_names:
        return
    context = bpy.context
    region = getattr(context, "region", None)
    space = getattr(context, "space_data", None)
    if region is None or space is None or getattr(space, "type", None) != "VIEW_3D":
        return
    region_3d = getattr(space, "region_3d", None)
    if region_3d is None:
        return
    import blf
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    from mathutils import Vector

    font_id = 0
    blf.size(font_id, 12)
    for label in _CACHE.labels:
        if not _role_visible(label.role):
            continue
        point = location_3d_to_region_2d(region, region_3d, Vector(label.position))
        if point is None:
            continue
        blf.color(font_id, *label.color)
        blf.position(font_id, float(point.x) + 5.0, float(point.y) + 5.0, 0.0)
        blf.draw(font_id, label.text)


def enable(cache, options: HierarchyOverlayOptions) -> None:
    global _VIEW_HANDLER, _TEXT_HANDLER, _CACHE, _GPU_BATCHES, _OPTIONS
    disable()
    _CACHE = cache
    _OPTIONS = options
    _GPU_BATCHES = _build_gpu_batches(cache)
    try:
        _VIEW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            _draw_view_callback, (), "WINDOW", "POST_VIEW",
        )
        _TEXT_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            _draw_text_callback, (), "WINDOW", "POST_PIXEL",
        )
    except Exception:
        disable()
        raise


def disable() -> None:
    global _VIEW_HANDLER, _TEXT_HANDLER, _CACHE, _GPU_BATCHES
    if _VIEW_HANDLER is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_VIEW_HANDLER, "WINDOW")
        except (ReferenceError, RuntimeError, TypeError, ValueError):
            pass
    if _TEXT_HANDLER is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_TEXT_HANDLER, "WINDOW")
        except (ReferenceError, RuntimeError, TypeError, ValueError):
            pass
    _VIEW_HANDLER = None
    _TEXT_HANDLER = None
    _CACHE = None
    _GPU_BATCHES = ()


def set_options(options: HierarchyOverlayOptions) -> None:
    global _OPTIONS
    _OPTIONS = options


def is_enabled() -> bool:
    return _VIEW_HANDLER is not None and _TEXT_HANDLER is not None


def overlay_cache():
    return _CACHE
