"""Centralized, idempotent Blender class and RNA registration."""

from __future__ import annotations

import bpy

from .operators import OPERATOR_CLASSES
from .properties import PROPERTY_CLASSES, register_properties, unregister_properties
from .core.runtime_store import clear_plans
from .translations import register as register_translations
from .translations import unregister as unregister_translations
from .ui import UI_CLASSES
from .controllers.session import SessionController
from .controllers.preview import PreviewController
from .controllers.hierarchy_overlay import HierarchyOverlayController


CLASSES = PROPERTY_CLASSES + OPERATOR_CLASSES + UI_CLASSES
_registered = False


def register() -> None:
    global _registered
    if _registered:
        return
    registered_classes = []
    properties_attempted = False
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            registered_classes.append(cls)
        properties_attempted = True
        register_properties()
        SessionController.register_handlers()
        register_translations()
        _registered = True
    except Exception:
        SessionController.unregister_handlers()
        PreviewController.disable(bpy.context)
        HierarchyOverlayController.disable(bpy.context)
        clear_plans()
        if properties_attempted:
            unregister_properties()
        for cls in reversed(registered_classes):
            try:
                bpy.utils.unregister_class(cls)
            except RuntimeError:
                pass
        _registered = False
        raise


def unregister() -> None:
    global _registered
    if not _registered:
        SessionController.unregister_handlers()
        PreviewController.disable(bpy.context)
        HierarchyOverlayController.disable(bpy.context)
        clear_plans()
        return
    SessionController.unregister_handlers()
    PreviewController.disable(bpy.context)
    HierarchyOverlayController.disable(bpy.context)
    clear_plans()
    unregister_properties()
    unregister_translations()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _registered = False
