"""Operator class registry."""

from .analyze import UECP_OT_analyze
from .apply import UECP_OT_apply
from .check_and_preview import UECP_OT_check_and_preview
from .clear_runtime import UECP_OT_clear_runtime
from .export_report import UECP_OT_export_report
from .export_conversion import UECP_OT_export_conversion
from .preview import UECP_OT_preview_toggle
from .locate_issue import UECP_OT_locate_issue
from .load_details import UECP_OT_load_details
from .restore import UECP_OT_restore_snapshot
from .validate import UECP_OT_validate
from .inspect_hierarchy import UECP_OT_inspect_active_hierarchy
from .select_inspected_scope import (
    UECP_OT_select_inspected_scope,
    UECP_OT_use_inspected_scope,
)
from .set_branch_continuation import UECP_OT_set_branch_continuation
from .clear_hierarchy_inspection import UECP_OT_clear_hierarchy_inspection
from .discover_secondary_chains import UECP_OT_discover_secondary_chains
from .select_discovered_chain import UECP_OT_select_discovered_chain
from .use_discovered_chains import UECP_OT_use_discovered_chains
from .clear_semantic_discovery import UECP_OT_clear_semantic_discovery
from .export_semantic_discovery import UECP_OT_export_semantic_discovery


OPERATOR_CLASSES = (
    UECP_OT_analyze,
    UECP_OT_check_and_preview,
    UECP_OT_apply,
    UECP_OT_validate,
    UECP_OT_preview_toggle,
    UECP_OT_locate_issue,
    UECP_OT_load_details,
    UECP_OT_restore_snapshot,
    UECP_OT_export_report,
    UECP_OT_export_conversion,
    UECP_OT_clear_runtime,
    UECP_OT_inspect_active_hierarchy,
    UECP_OT_select_inspected_scope,
    UECP_OT_use_inspected_scope,
    UECP_OT_set_branch_continuation,
    UECP_OT_clear_hierarchy_inspection,
    UECP_OT_discover_secondary_chains,
    UECP_OT_select_discovered_chain,
    UECP_OT_use_discovered_chains,
    UECP_OT_clear_semantic_discovery,
    UECP_OT_export_semantic_discovery,
)
