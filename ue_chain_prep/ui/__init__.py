"""User-interface class registry."""

from .lists import UI_LIST_CLASSES
from .panels import PANEL_CLASSES
from .preferences import UECP_AddonPreferences


UI_CLASSES = UI_LIST_CLASSES + (UECP_AddonPreferences,) + PANEL_CLASSES
