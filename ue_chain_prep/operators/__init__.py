"""Operator class registry."""

from .analyze import UECP_OT_analyze
from .apply import UECP_OT_apply
from .clear_runtime import UECP_OT_clear_runtime
from .export_report import UECP_OT_export_report
from .preview import UECP_OT_preview_toggle
from .restore import UECP_OT_restore_snapshot
from .validate import UECP_OT_validate


OPERATOR_CLASSES = (
    UECP_OT_analyze,
    UECP_OT_apply,
    UECP_OT_validate,
    UECP_OT_preview_toggle,
    UECP_OT_restore_snapshot,
    UECP_OT_export_report,
    UECP_OT_clear_runtime,
)
