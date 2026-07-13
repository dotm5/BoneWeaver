"""Operator class registry."""

from .analyze import BONEWEAVER_OT_analyze
from .apply import BONEWEAVER_OT_apply
from .check_and_preview import BONEWEAVER_OT_check_and_preview
from .clear_runtime import BONEWEAVER_OT_clear_runtime
from .export_report import BONEWEAVER_OT_export_report
from .export_conversion import BONEWEAVER_OT_export_conversion
from .preview import BONEWEAVER_OT_preview_toggle
from .locate_issue import BONEWEAVER_OT_locate_issue
from .load_details import BONEWEAVER_OT_load_details
from .restore import BONEWEAVER_OT_restore_snapshot
from .validate import BONEWEAVER_OT_validate
from .inspect_hierarchy import BONEWEAVER_OT_inspect_active_hierarchy
from .select_inspected_scope import (
    BONEWEAVER_OT_select_inspected_scope,
    BONEWEAVER_OT_use_inspected_scope,
)
from .set_branch_continuation import BONEWEAVER_OT_set_branch_continuation
from .clear_hierarchy_inspection import BONEWEAVER_OT_clear_hierarchy_inspection
from .discover_secondary_chains import BONEWEAVER_OT_discover_secondary_chains
from .select_discovered_chain import BONEWEAVER_OT_select_discovered_chain
from .use_discovered_chains import BONEWEAVER_OT_use_discovered_chains
from .clear_semantic_discovery import BONEWEAVER_OT_clear_semantic_discovery
from .export_semantic_discovery import BONEWEAVER_OT_export_semantic_discovery
from .quick_reorient import QUICK_REORIENT_OPERATOR_CLASSES


OPERATOR_CLASSES = (
    BONEWEAVER_OT_analyze,
    BONEWEAVER_OT_check_and_preview,
    BONEWEAVER_OT_apply,
    BONEWEAVER_OT_validate,
    BONEWEAVER_OT_preview_toggle,
    BONEWEAVER_OT_locate_issue,
    BONEWEAVER_OT_load_details,
    BONEWEAVER_OT_restore_snapshot,
    BONEWEAVER_OT_export_report,
    BONEWEAVER_OT_export_conversion,
    BONEWEAVER_OT_clear_runtime,
    BONEWEAVER_OT_inspect_active_hierarchy,
    BONEWEAVER_OT_select_inspected_scope,
    BONEWEAVER_OT_use_inspected_scope,
    BONEWEAVER_OT_set_branch_continuation,
    BONEWEAVER_OT_clear_hierarchy_inspection,
    BONEWEAVER_OT_discover_secondary_chains,
    BONEWEAVER_OT_select_discovered_chain,
    BONEWEAVER_OT_use_discovered_chains,
    BONEWEAVER_OT_clear_semantic_discovery,
    BONEWEAVER_OT_export_semantic_discovery,
) + QUICK_REORIENT_OPERATOR_CLASSES
