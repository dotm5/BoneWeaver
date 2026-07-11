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


CLASSES = PROPERTY_CLASSES + OPERATOR_CLASSES + UI_CLASSES
_registered = False


def register() -> None:
    global _registered
    if _registered:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    register_properties()
    SessionController.register_handlers()
    register_translations()
    _registered = True


def unregister() -> None:
    global _registered
    if not _registered:
        SessionController.unregister_handlers()
        PreviewController.disable(bpy.context)
        clear_plans()
        unregister_properties()
        return
    SessionController.unregister_handlers()
    PreviewController.disable(bpy.context)
    clear_plans()
    unregister_properties()
    unregister_translations()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _registered = False
