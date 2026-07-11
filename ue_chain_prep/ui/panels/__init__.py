"""Layered sidebar panels."""

from .advanced import UECP_PT_advanced
from .details import UECP_PT_details
from .developer import UECP_PT_developer
from .main import UECP_PT_main
from .recovery import UECP_PT_recovery

PANEL_CLASSES = (UECP_PT_main, UECP_PT_advanced, UECP_PT_details, UECP_PT_recovery, UECP_PT_developer)
