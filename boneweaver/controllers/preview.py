"""Single owner for preview handler, cache, redraw, and runtime synchronization."""

from __future__ import annotations

from ..core.runtime_store import get_preview_cache, put_preview_cache
from ..ui import draw


class PreviewController:
    @staticmethod
    def enable(context, cache=None) -> bool:
        frozen_cache = tuple(get_preview_cache() if cache is None else cache)
        if not frozen_cache:
            PreviewController.disable(context)
            return False
        draw._enable_preview(frozen_cache)
        put_preview_cache(frozen_cache)
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is not None:
            runtime.preview_enabled = True
        PreviewController.tag_redraw(context)
        return True

    @staticmethod
    def disable(context=None) -> None:
        draw._disable_preview()
        if context is not None:
            runtime = getattr(context.window_manager, "boneweaver_runtime", None)
            if runtime is not None:
                runtime.preview_enabled = False
            PreviewController.tag_redraw(context)

    @staticmethod
    def toggle(context) -> bool:
        if PreviewController.is_enabled():
            PreviewController.disable(context)
            return False
        return PreviewController.enable(context)

    @staticmethod
    def rebuild(context, cache) -> bool:
        was_enabled = PreviewController.is_enabled()
        PreviewController.disable(context)
        put_preview_cache(tuple(cache))
        return PreviewController.enable(context) if was_enabled else False

    @staticmethod
    def is_enabled() -> bool:
        return draw.is_preview_enabled()

    @staticmethod
    def tag_redraw(context) -> None:
        screen = getattr(context, "screen", None)
        for area in getattr(screen, "areas", ()) if screen else ():
            if area.type == "VIEW_3D":
                area.tag_redraw()
