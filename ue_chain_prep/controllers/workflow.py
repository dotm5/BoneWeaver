"""Authoritative workflow transitions for analyze, apply, validate, and restore."""

from __future__ import annotations

import time
import tracemalloc

from ..contracts import PlanState, TerminalResolutionClass
from ..core.apply_transaction import apply_plan
from ..core.fingerprint import current_source_fingerprint, settings_fingerprint
from ..core.planner import build_plan, last_build_metrics
from ..core.restore import restore_snapshot
from ..core.runtime_store import (
    get_performance, get_plan, has_plan, put_performance, put_plan,
    put_preview_cache, put_report,
)
from ..core.serialization import build_diagnostic_report
from ..core.validation import capture_neutral_meshes, validate_post_apply
from ..ui.draw import build_plan_cache
from .preview import PreviewController
from .selection import SelectionController
from .session import SessionController


class WorkflowController:
    @staticmethod
    def can_analyze(context) -> bool:
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return runtime is not None and not runtime.is_busy

    @staticmethod
    def can_apply(context) -> bool:
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.state == PlanState.ANALYZED.value
                    and runtime.issue_count_blocker == 0 and runtime.plan_id
                    and has_plan(runtime.plan_id))

    @staticmethod
    def analyze(context, *, auto_preview: bool) -> set[str]:
        runtime = context.window_manager.uecp_runtime
        runtime.is_busy = True
        owns_tracemalloc = not tracemalloc.is_tracing()
        if owns_tracemalloc:
            tracemalloc.start()
        context.window_manager.progress_begin(0, 100)
        PreviewController.disable(context)
        try:
            context.window_manager.progress_update(10)
            plan = build_plan(context)
            if plan is None:
                runtime.last_error = "UECP_NO_ACTIVE_ARMATURE"
                runtime.state = PlanState.IDLE.value
                return {"CANCELLED"}
            context.window_manager.progress_update(80)
            counts = {"INFO": 0, "WARNING": 0, "BLOCKER": 0}
            for issue in plan.issues:
                counts[issue.severity] = counts.get(issue.severity, 0) + 1
            reliable = sum(solution.resolution_class in {
                TerminalResolutionClass.AUTO_CONFIDENT.value,
                TerminalResolutionClass.MANUAL.value,
            } for solution in plan.terminal_solutions)
            attention = sum(solution.requires_confirmation for solution in plan.terminal_solutions)
            _current_memory, tracemalloc_peak = tracemalloc.get_traced_memory()
            preview_started = time.perf_counter()
            cache = build_plan_cache(plan)
            preview_build_time = time.perf_counter() - preview_started
            put_plan(plan)
            metrics = last_build_metrics()
            metrics.update(
                tracemalloc_peak=tracemalloc_peak,
                preview_build_time=preview_build_time,
                ui_item_count=0,
            )
            put_performance(plan.plan_id, metrics)
            put_preview_cache(cache)
            SessionController._clear_collections(context)
            runtime.issue_count_info = counts["INFO"]
            runtime.issue_count_warning = counts["WARNING"]
            runtime.issue_count_blocker = counts["BLOCKER"]
            runtime.plan_bone_count = len(plan.bone_states)
            runtime.plan_chain_count = len(plan.physics_graph.chains)
            runtime.terminal_reliable_count = reliable
            runtime.terminal_attention_count = attention
            runtime.plan_summary = f"{len(plan.bone_states)} bones, {len(plan.physics_graph.chains)} chains, {len(plan.issues)} issues"
            runtime.plan_id = plan.plan_id
            runtime.plan_fingerprint = plan.source_fingerprint
            runtime.selection_signature = SelectionController.signature(
                context, bone_names=tuple(state.name for state in plan.bone_states)
            )
            runtime.settings_signature = plan.settings_fingerprint
            runtime.state = PlanState.ANALYZED.value
            runtime.generation += 1
            runtime.details_loaded = False
            runtime.last_error = ""
            context.window_manager.progress_update(95)
            if auto_preview and cache:
                PreviewController.enable(context, cache)
            context.window_manager.progress_update(100)
            return {"FINISHED"}
        except Exception as exc:
            runtime.state = PlanState.ERROR.value
            runtime.last_error = str(exc) or "UECP_INTERNAL_ERROR"
            return {"CANCELLED"}
        finally:
            if owns_tracemalloc and tracemalloc.is_tracing():
                tracemalloc.stop()
            context.window_manager.progress_end()
            runtime.is_busy = False

    @staticmethod
    def apply(context, requested_plan_id: str = "") -> set[str]:
        runtime = context.window_manager.uecp_runtime
        requested = requested_plan_id or runtime.plan_id
        if requested != runtime.plan_id or not has_plan(requested):
            runtime.state = PlanState.STALE.value
            runtime.last_error = "UECP_STATE_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        plan = get_plan(requested)
        if current_source_fingerprint(context, plan) != plan.source_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "UECP_STATE_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        if settings_fingerprint(context.scene.uecp_settings) != plan.settings_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "UECP_SETTINGS_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        PreviewController.disable(context)
        runtime.is_busy = True
        runtime.state = PlanState.APPLYING.value
        try:
            result = apply_plan(context, plan)
            performance = get_performance(plan.plan_id)
            performance.update(apply_time=result.apply_time, validation_time=result.validation_time)
            put_performance(plan.plan_id, performance)
            runtime.snapshot_id = result.snapshot_id
            runtime.snapshot_text_name = result.snapshot_text_name
            if result.success:
                runtime.state = PlanState.RESTORABLE.value
                runtime.last_error = ""
                return {"FINISHED"}
            runtime.state = PlanState.ANALYZED.value if result.rolled_back else PlanState.ERROR.value
            runtime.last_error = result.error or "UECP_INTERNAL_ERROR"
            return {"CANCELLED"}
        finally:
            runtime.is_busy = False

    @staticmethod
    def validate(context) -> set[str]:
        runtime = context.window_manager.uecp_runtime
        if not runtime.plan_id or not has_plan(runtime.plan_id):
            runtime.last_error = "UECP_EXPORT_PLAN_MISSING"
            return {"CANCELLED"}
        plan = get_plan(runtime.plan_id)
        baseline = capture_neutral_meshes(plan)
        validation = validate_post_apply(context, plan, baseline)
        put_report(build_diagnostic_report(plan, validation, runtime.snapshot_id or None))
        runtime.last_error = "" if validation.success else validation.issues[0]
        return {"FINISHED"}

    @staticmethod
    def restore(context, snapshot_text_name: str = "") -> set[str]:
        runtime = context.window_manager.uecp_runtime
        PreviewController.disable(context)
        text_name = snapshot_text_name or runtime.snapshot_text_name
        success, error = restore_snapshot(context, text_name)
        if not success:
            runtime.last_error = error
            return {"CANCELLED"}
        SessionController.clear_analysis(context)
        runtime.state = PlanState.RESTORED.value
        runtime.last_error = ""
        return {"FINISHED"}
