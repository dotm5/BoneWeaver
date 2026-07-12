"""Authoritative workflow transitions for analyze, apply, validate, and restore."""

from __future__ import annotations

import time
import tracemalloc

import bpy

from ..contracts import PlanState, TerminalResolutionClass
from ..core.apply_transaction import apply_plan
from ..core.fingerprint import current_source_fingerprint, settings_fingerprint
from ..core.planner import build_plan, last_build_metrics
from ..core.restore import restore_snapshot
from ..core.runtime_store import (
    FrozenSemanticScope,
    bind_analysis_scope, get_analysis_scope, get_performance, get_plan, has_plan,
    put_performance, put_plan,
    put_preview_cache, put_report,
)
from ..core.serialization import build_diagnostic_report
from ..core.validation import capture_neutral_meshes, validate_post_apply
from ..core.context_guard import ContextStateGuard
from ..ui.draw import build_plan_cache
from .preview import PreviewController
from .selection import SelectionController
from .session import SessionController
from .hierarchy_inspection import (
    HierarchyInspectionController,
    HierarchyInspectionRuntimeError,
)
from .semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)


class WorkflowController:
    @staticmethod
    def _build_analyze_plan(context):
        with ContextStateGuard(context):
            if context.object is not None and context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.update()
            scope = WorkflowController._analysis_scope(context)
            if scope is not None:
                WorkflowController._validate_scope(context, scope)
            plan = build_plan(
                context,
                scope_names=scope.bone_names if scope is not None else None,
                scoped_branch_continuations=(
                    getattr(scope, "manual_branch_continuations", ())
                    if scope is not None else ()
                ),
                required_reference_tip_helper_names=(
                    getattr(scope, "reference_only_tip_helper_names", ())
                    if scope is not None else ()
                ),
            )
            return scope, plan

    @staticmethod
    def _analysis_scope(context):
        hierarchy_scope = HierarchyInspectionController.analysis_scope(context)
        semantic_scope = SemanticDiscoveryController.analysis_scope(context)
        if hierarchy_scope is not None and semantic_scope is not None:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SCOPE_SOURCE_CONFLICT")
        return semantic_scope or hierarchy_scope

    @staticmethod
    def _validate_scope(context, scope) -> None:
        if isinstance(scope, FrozenSemanticScope):
            expected_armature = SemanticDiscoveryController.validate_frozen_scope(context, scope)
        else:
            expected_armature = HierarchyInspectionController.validate_frozen_scope(context, scope)
        active_armature, _source = SelectionController.armature_from_context(context)
        if (
            active_armature is None
            or active_armature.name != expected_armature.name
            or active_armature.data.name != expected_armature.data.name
        ):
            raise HierarchyInspectionRuntimeError("BONEWEAVER_HIERARCHY_ARMATURE_CHANGED")

    @staticmethod
    def can_analyze(context) -> bool:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return runtime is not None and not runtime.is_busy

    @staticmethod
    def can_apply(context) -> bool:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if not bool(runtime and not runtime.is_busy and runtime.state == PlanState.ANALYZED.value
                    and runtime.issue_count_blocker == 0 and runtime.plan_id
                    and has_plan(runtime.plan_id)):
            return False
        scope = get_analysis_scope(runtime.plan_id)
        try:
            if scope is not None:
                WorkflowController._validate_scope(context, scope)
            signature = SelectionController.signature(
                context,
                bone_names=scope.bone_names if scope is not None else None,
            )
        except (HierarchyInspectionRuntimeError, SemanticDiscoveryRuntimeError):
            return False
        return runtime.selection_signature == signature

    @staticmethod
    def analyze(context, *, auto_preview: bool) -> set[str]:
        runtime = context.window_manager.boneweaver_runtime
        runtime.is_busy = True
        owns_tracemalloc = not tracemalloc.is_tracing()
        if owns_tracemalloc:
            tracemalloc.start()
        context.window_manager.progress_begin(0, 100)
        PreviewController.disable(context)
        try:
            context.window_manager.progress_update(10)
            inspection_scope, plan = WorkflowController._build_analyze_plan(context)
            if plan is None:
                runtime.last_error = "BONEWEAVER_NO_ACTIVE_ARMATURE"
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
            cache = build_plan_cache(plan, context.scene.boneweaver_settings)
            preview_build_time = time.perf_counter() - preview_started
            put_plan(plan)
            bind_analysis_scope(plan.plan_id, inspection_scope)
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
                context,
                bone_names=(
                    inspection_scope.bone_names
                    if inspection_scope is not None
                    else None
                ),
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
        except (HierarchyInspectionRuntimeError, SemanticDiscoveryRuntimeError) as exc:
            runtime.state = PlanState.STALE.value
            runtime.last_error = str(exc)
            return {"CANCELLED"}
        except Exception as exc:
            runtime.state = PlanState.ERROR.value
            runtime.last_error = str(exc) or "BONEWEAVER_INTERNAL_ERROR"
            return {"CANCELLED"}
        finally:
            if owns_tracemalloc and tracemalloc.is_tracing():
                tracemalloc.stop()
            context.window_manager.progress_end()
            runtime.is_busy = False

    @staticmethod
    def apply(context, requested_plan_id: str = "") -> set[str]:
        runtime = context.window_manager.boneweaver_runtime
        requested = requested_plan_id or runtime.plan_id
        if requested != runtime.plan_id or not has_plan(requested):
            runtime.state = PlanState.STALE.value
            runtime.last_error = "BONEWEAVER_STATE_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        analysis_scope = get_analysis_scope(requested)
        try:
            if analysis_scope is not None:
                WorkflowController._validate_scope(context, analysis_scope)
            current_selection_signature = SelectionController.signature(
                context,
                bone_names=(
                    analysis_scope.bone_names
                    if analysis_scope is not None
                    else None
                ),
            )
        except (HierarchyInspectionRuntimeError, SemanticDiscoveryRuntimeError) as exc:
            runtime.state = PlanState.STALE.value
            runtime.last_error = str(exc)
            PreviewController.disable(context)
            return {"CANCELLED"}
        if runtime.selection_signature != current_selection_signature:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "BONEWEAVER_STATE_CHANGED_AFTER_ANALYZE"
            PreviewController.disable(context)
            return {"CANCELLED"}
        plan = get_plan(requested)
        if current_source_fingerprint(context, plan) != plan.source_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "BONEWEAVER_STATE_CHANGED_AFTER_ANALYZE"
            return {"CANCELLED"}
        if settings_fingerprint(context.scene.boneweaver_settings) != plan.settings_fingerprint:
            runtime.state = PlanState.STALE.value
            runtime.last_error = "BONEWEAVER_SETTINGS_CHANGED_AFTER_ANALYZE"
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
            runtime.snapshot_available = bool(result.success and result.snapshot_text_name)
            if result.success:
                HierarchyInspectionController.clear(context)
                SemanticDiscoveryController.clear(context)
                runtime.state = PlanState.RESTORABLE.value
                runtime.last_error = ""
                return {"FINISHED"}
            runtime.state = PlanState.ANALYZED.value if result.rolled_back else PlanState.ERROR.value
            runtime.last_error = result.error or "BONEWEAVER_INTERNAL_ERROR"
            return {"CANCELLED"}
        finally:
            runtime.is_busy = False

    @staticmethod
    def validate(context) -> set[str]:
        runtime = context.window_manager.boneweaver_runtime
        if not runtime.plan_id or not has_plan(runtime.plan_id):
            runtime.last_error = "BONEWEAVER_EXPORT_PLAN_MISSING"
            return {"CANCELLED"}
        plan = get_plan(runtime.plan_id)
        baseline = capture_neutral_meshes(plan)
        validation = validate_post_apply(context, plan, baseline)
        put_report(build_diagnostic_report(plan, validation, runtime.snapshot_id or None))
        runtime.last_error = "" if validation.success else validation.issues[0]
        return {"FINISHED"}

    @staticmethod
    def restore(context, snapshot_text_name: str = "") -> set[str]:
        runtime = context.window_manager.boneweaver_runtime
        PreviewController.disable(context)
        text_name = snapshot_text_name or runtime.snapshot_text_name
        success, error = restore_snapshot(context, text_name)
        if not success:
            runtime.last_error = error
            return {"CANCELLED"}
        SessionController.clear_analysis(context)
        runtime.state = PlanState.RESTORED.value
        runtime.snapshot_available = False
        runtime.last_error = ""
        return {"FINISHED"}
