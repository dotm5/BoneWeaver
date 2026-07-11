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
)
