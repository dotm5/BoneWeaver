"""Session lifecycle and lazy transient RNA synchronization."""

from __future__ import annotations

import bpy
from bpy.app.handlers import persistent

from ..contracts import PlanState
from ..core.runtime_store import clear_plans
from ..core.runtime_store import get_plan, has_plan
from .preview import PreviewController


class SessionController:
    @staticmethod
    def _clear_collections(context) -> None:
        wm = context.window_manager
        for name in ("uecp_chain_items", "uecp_proposal_items", "uecp_issue_items"):
            collection = getattr(wm, name, None)
            if collection is not None:
                collection.clear()

    @staticmethod
    def clear_analysis(context) -> None:
        PreviewController.disable(context)
        clear_plans()
        SessionController._clear_collections(context)
        runtime = context.window_manager.uecp_runtime
        runtime.state = PlanState.IDLE.value
        runtime.plan_id = ""
        runtime.plan_fingerprint = ""
        runtime.plan_summary = ""
        runtime.selection_signature = ""
        runtime.settings_signature = ""
        runtime.plan_bone_count = 0
        runtime.plan_chain_count = 0
        runtime.terminal_reliable_count = 0
        runtime.terminal_attention_count = 0
        runtime.issue_count_info = 0
        runtime.issue_count_warning = 0
        runtime.issue_count_blocker = 0
        runtime.active_chain_index = 0
        runtime.active_proposal_index = 0
        runtime.active_issue_index = 0
        runtime.details_loaded = False
        runtime.last_error = ""
        runtime.is_busy = False

    @staticmethod
    def reset_session(context) -> None:
        SessionController.clear_analysis(context)
        context.window_manager.uecp_runtime.generation = 0

    @staticmethod
    def populate_details(context, max_items: int = 200) -> bool:
        runtime = context.window_manager.uecp_runtime
        if not runtime.plan_id or not has_plan(runtime.plan_id):
            runtime.last_error = "UECP_EXPORT_PLAN_MISSING"
            return False
        plan = get_plan(runtime.plan_id)
        SessionController._clear_collections(context)
        wm = context.window_manager
        for chain in plan.physics_graph.chains[:max_items]:
            item = wm.uecp_chain_items.add()
            item.chain_id = chain.chain_id
            item.root_name = chain.real_bone_names[0]
            item.leaf_name = chain.real_bone_names[-1]
            item.resolved = chain.resolved
        for proposal in plan.proposals[:max_items]:
            item = wm.uecp_proposal_items.add()
            item.bone_name = proposal.bone_name
            item.role = proposal.role
            item.confidence = proposal.confidence
        for issue in plan.issues[:max_items]:
            item = wm.uecp_issue_items.add()
            item.severity = issue.severity
            item.code = issue.code
            item.message = issue.message
            item.bone_name = issue.bone_names[0] if issue.bone_names else ""
        runtime.details_loaded = True
        return True

    @staticmethod
    def invalidate_for_scene_change(context, reason: str) -> None:
        PreviewController.disable(context)
        clear_plans()
        SessionController._clear_collections(context)
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if runtime is None:
            return
        runtime.details_loaded = False
        runtime.active_chain_index = 0
        runtime.active_proposal_index = 0
        runtime.active_issue_index = 0
        runtime.last_error = "UECP_SCENE_CHANGED_RECHECK"
        runtime.is_busy = False

    @staticmethod
    @persistent
    def on_load_pre(_unused):
        if hasattr(bpy.context.window_manager, "uecp_runtime"):
            SessionController.invalidate_for_scene_change(bpy.context, "load_pre")

    @staticmethod
    @persistent
    def on_load_post(_unused):
        if hasattr(bpy.context.window_manager, "uecp_runtime"):
            SessionController.invalidate_for_scene_change(bpy.context, "load_post")

    @staticmethod
    @persistent
    def on_undo_post(_unused):
        if hasattr(bpy.context.window_manager, "uecp_runtime"):
            SessionController.invalidate_for_scene_change(bpy.context, "undo_redo")

    @staticmethod
    @persistent
    def on_redo_post(_unused):
        if hasattr(bpy.context.window_manager, "uecp_runtime"):
            SessionController.invalidate_for_scene_change(bpy.context, "undo_redo")

    @classmethod
    def register_handlers(cls) -> None:
        for collection, callback in (
            (bpy.app.handlers.load_pre, cls.on_load_pre),
            (bpy.app.handlers.load_post, cls.on_load_post),
            (bpy.app.handlers.undo_post, cls.on_undo_post),
            (bpy.app.handlers.redo_post, cls.on_redo_post),
        ):
            if callback not in collection:
                collection.append(callback)

    @classmethod
    def unregister_handlers(cls) -> None:
        for collection, callback in (
            (bpy.app.handlers.load_pre, cls.on_load_pre),
            (bpy.app.handlers.load_post, cls.on_load_post),
            (bpy.app.handlers.undo_post, cls.on_undo_post),
            (bpy.app.handlers.redo_post, cls.on_redo_post),
        ):
            while callback in collection:
                collection.remove(callback)
