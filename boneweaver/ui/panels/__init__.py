"""Layered sidebar panels."""

from .advanced import BONEWEAVER_PT_advanced
from .details import BONEWEAVER_PT_details
from .developer import BONEWEAVER_PT_developer
from .main import BONEWEAVER_PT_main
from .recovery import BONEWEAVER_PT_recovery
from .hierarchy import BONEWEAVER_PT_hierarchy
from .semantic_discovery import BONEWEAVER_PT_semantic_discovery

PANEL_CLASSES = (
    BONEWEAVER_PT_main,
    BONEWEAVER_PT_hierarchy,
    BONEWEAVER_PT_semantic_discovery,
    BONEWEAVER_PT_advanced,
    BONEWEAVER_PT_details,
    BONEWEAVER_PT_recovery,
    BONEWEAVER_PT_developer,
)
