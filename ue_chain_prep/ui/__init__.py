"""User-interface class registry."""

from .panel import UECP_PT_main
from .lists import UI_LIST_CLASSES


UI_CLASSES = UI_LIST_CLASSES + (UECP_PT_main,)
