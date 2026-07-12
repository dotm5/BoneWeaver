"""Blender adapters for immutable hierarchy inspection and frozen Analyze scopes."""

from __future__ import annotations

import dataclasses

import bpy

from ..contracts import PlanState
from ..core.armature_reader import read_bone_states, selected_bone_names
from ..core.fingerprint import current_source_fingerprint, settings_fingerprint
from ..core.hierarchy_index import ArmatureHierarchyIndex, HierarchyBoneSnapshot
from ..core.hierarchy_inspection import (
    HierarchyInspectionError,
    HierarchyInspectionInput,
    HierarchySelectionMode,
    build_hierarchy_inspection_plan,
)
from ..core.overrides import armature_structural_fingerprint
from ..core.preflight import run_preflight
from ..core.runtime_store import (
    FrozenInspectionScope,
    HierarchyInspectionSession,
    get_hierarchy_inspection,
    get_plan,
    get_used_semantic_scope,
    get_used_inspection_scope,
    has_plan,
    put_hierarchy_inspection,
    put_used_inspection_scope,
    clear_hierarchy_inspection as clear_stored_hierarchy_inspection,
)
from ..core.tip_helpers import classify_tip_helpers
from .selection import SelectionController
from .hierarchy_overlay import HierarchyOverlayController
from .semantic_discovery import SemanticDiscoveryController


class HierarchyInspectionRuntimeError(RuntimeError):
    """A hierarchy operation cannot safely use the current Blender context."""


class HierarchyInspectionController:
    @staticmethod
    def _mark_analyzed_plan_stale(context) -> None:
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if runtime is None or runtime.state != PlanState.ANALYZED.value or not runtime.plan_id:
            return
        from .preview import PreviewController
        PreviewController.disable(context)
        runtime.state = PlanState.STALE.value
        runtime.last_error = "UECP_HIERARCHY_SCOPE_CHANGED_REANALYZE"

    @staticmethod
    def _source_filepath() -> str:
        return str(getattr(bpy.data, "filepath", "") or "")

    @staticmethod
    def _active_armature(context):
        armature, _source = SelectionController.armature_from_context(context)
        if armature is None:
            raise HierarchyInspectionRuntimeError("UECP_NO_ACTIVE_ARMATURE")
        return armature

    @staticmethod
    def _active_bone_name(context, armature) -> str:
        if context.mode == "EDIT_ARMATURE" and context.object == armature:
            active = getattr(armature.data.edit_bones, "active", None)
        elif context.mode == "POSE" and context.object == armature:
            active = getattr(context, "active_pose_bone", None)
        else:
            active = getattr(armature.data.bones, "active", None)
        if active is None or active.name not in armature.data.bones:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_NO_ACTIVE_BONE")
        return active.name

    @staticmethod
    def _build_index(armature) -> ArmatureHierarchyIndex:
        return ArmatureHierarchyIndex.from_bones(
            HierarchyBoneSnapshot(
                name=bone.name,
                parent_name=bone.parent.name if bone.parent else None,
            )
            for bone in armature.data.bones
        )

    @staticmethod
    def _plan_evidence(context, armature, fingerprint):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if (
            runtime is None
            or runtime.state != PlanState.ANALYZED.value
            or not runtime.plan_id
            or not has_plan(runtime.plan_id)
        ):
            return None
        plan = get_plan(runtime.plan_id)
        settings = getattr(context.scene, "uecp_settings", None)
        if (
            settings is None
            or settings_fingerprint(settings) != plan.settings_fingerprint
            or current_source_fingerprint(context, plan) != plan.source_fingerprint
        ):
            return None
        if plan.armature_object_name != armature.name:
            return None
        plan_names = {state.name for state in plan.bone_states}
        if not plan_names.issubset(armature.data.bones.keys()):
            return (), (), ()
        for state in plan.bone_states:
            bone = armature.data.bones[state.name]
            if (
                (bone.parent.name if bone.parent else None) != state.parent_name
                or tuple(float(value) for value in bone.head_local) != state.head
            ):
                return None
        if armature_structural_fingerprint(armature) != fingerprint:
            return None
        tip_names = tuple(item.bone_name for item in plan.tip_helpers)
        excluded_names = tuple(
            child_name
            for item in plan.tip_helpers
            for child_name in item.excluded_child_names
        )
        continuations = tuple(
            (item.branch_bone_name, item.selected_child_name)
            for item in plan.branch_resolutions
            if item.selected_child_name
        )
        return tip_names, excluded_names, continuations

    @staticmethod
    def _fresh_tip_helper_evidence(context, armature):
        """Classify helpers before Analyze using one read-only weight scan."""
        names = tuple(sorted(bone.name for bone in armature.data.bones))
        bone_states = read_bone_states(armature, names)
        weight_clouds = SemanticDiscoveryController._weight_clouds(
            context, armature, bone_states,
        )
        if not weight_clouds:
            return (), ()
        preflight = run_preflight(context, scope_names=names)
        settings = getattr(context.scene, "uecp_settings", None)
        helpers = classify_tip_helpers(
            bone_states,
            weight_clouds,
            preflight.issues,
            minimum_length_ratio=(
                settings.minimum_length_ratio if settings is not None else 0.25
            ),
            maximum_length_ratio=(
                settings.maximum_length_ratio if settings is not None else 2.0
            ),
        )
        return (
            tuple(item.bone_name for item in helpers),
            tuple(
                child_name
                for item in helpers
                for child_name in item.excluded_child_names
            ),
        )

    @staticmethod
    def _same_inspection_source(session, armature, fingerprint, source_filepath) -> bool:
        return bool(
            session
            and session.plan.armature_object_name == armature.name
            and session.armature_data_name == armature.data.name
            and session.plan.armature_fingerprint == fingerprint
            and session.source_filepath == source_filepath
        )

    @staticmethod
    def _sync_runtime(context, session, *, scope_used: bool | None = None) -> None:
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if runtime is None:
            return
        plan = session.plan
        runtime.hierarchy_inspection_active = True
        runtime.hierarchy_inspection_id = plan.inspection_id
        runtime.hierarchy_active_bone_name = plan.active_bone_name
        runtime.hierarchy_parent_context_name = plan.parent_context_name or ""
        runtime.hierarchy_selection_mode = plan.selection_mode
        runtime.hierarchy_armature_fingerprint = plan.armature_fingerprint
        runtime.hierarchy_source_filepath = session.source_filepath
        runtime.hierarchy_bone_count = len(plan.selected_bone_names)
        runtime.hierarchy_branch_count = len(plan.branch_bone_names)
        runtime.hierarchy_tip_helper_count = len(plan.tip_helper_names)
        runtime.hierarchy_excluded_helper_count = len(plan.excluded_helper_names)
        if runtime.hierarchy_branch_bone_name not in plan.branch_bone_names:
            runtime.hierarchy_branch_bone_name = (
                plan.branch_bone_names[0] if plan.branch_bone_names else ""
            )
            runtime.hierarchy_selected_child_name = ""
        branch_name = runtime.hierarchy_branch_bone_name
        if (
            branch_name
            and runtime.hierarchy_selected_child_name
            not in session.index.children_of(branch_name)
        ):
            runtime.hierarchy_selected_child_name = ""
        if scope_used is not None:
            runtime.hierarchy_scope_used = scope_used
        runtime.last_error = ""

    @staticmethod
    def _clear_runtime_fields(context) -> None:
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if runtime is None:
            return
        runtime.hierarchy_inspection_active = False
        runtime.hierarchy_scope_used = False
        runtime.hierarchy_inspection_id = ""
        runtime.hierarchy_active_bone_name = ""
        runtime.hierarchy_parent_context_name = ""
        runtime.hierarchy_armature_fingerprint = ""
        runtime.hierarchy_source_filepath = ""
        runtime.hierarchy_bone_count = 0
        runtime.hierarchy_branch_count = 0
        runtime.hierarchy_tip_helper_count = 0
        runtime.hierarchy_excluded_helper_count = 0
        runtime.hierarchy_overlay_enabled = False
        runtime.hierarchy_branch_bone_name = ""
        runtime.hierarchy_selected_child_name = ""

    @classmethod
    def inspect(cls, context):
        """Capture hierarchy state without changing Blender bone selection."""
        armature = cls._active_armature(context)
        active_name = cls._active_bone_name(context, armature)
        fingerprint = armature_structural_fingerprint(armature)
        source_filepath = cls._source_filepath()
        index = cls._build_index(armature)
        plan_evidence = cls._plan_evidence(
            context, armature, fingerprint,
        )
        if plan_evidence is None:
            tip_names, excluded_names = cls._fresh_tip_helper_evidence(
                context, armature,
            )
            plan_continuations = ()
        else:
            tip_names, excluded_names, plan_continuations = plan_evidence
        semantic_categories, semantic_excluded_names = (
            SemanticDiscoveryController.valid_hierarchy_evidence(
                context, armature, fingerprint,
            )
        )
        excluded_names = tuple(sorted(
            (set(excluded_names) | set(semantic_excluded_names)) - set(tip_names)
        ))
        previous = get_hierarchy_inspection()
        manual_continuations = (
            previous.manual_branch_continuations
            if cls._same_inspection_source(previous, armature, fingerprint, source_filepath)
            else ()
        )
        continuation_by_branch = dict(plan_continuations)
        continuation_by_branch.update(dict(manual_continuations))
        runtime = context.window_manager.uecp_runtime
        mode = getattr(
            runtime,
            "hierarchy_selection_mode",
            HierarchySelectionMode.LINEAR_CHAIN.value,
        )
        snapshot = HierarchyInspectionInput(
            armature_object_name=armature.name,
            armature_fingerprint=fingerprint,
            active_bone_name=active_name,
            selection_mode=mode,
            selected_bone_names=selected_bone_names(context, armature),
            branch_continuations=tuple(continuation_by_branch.items()),
            tip_helper_names=tip_names,
            excluded_helper_names=excluded_names,
            semantic_categories=semantic_categories,
        )
        plan = build_hierarchy_inspection_plan(index, snapshot)
        session = HierarchyInspectionSession(
            plan=plan,
            index=index,
            snapshot=snapshot,
            source_filepath=source_filepath,
            armature_data_name=armature.data.name,
            manual_branch_continuations=manual_continuations,
        )
        put_hierarchy_inspection(session)
        used = get_used_inspection_scope()
        if used is not None and used.inspection_id != plan.inspection_id:
            put_used_inspection_scope(None)
            used = None
        cls._sync_runtime(
            context,
            session,
            scope_used=bool(used and used.inspection_id == plan.inspection_id),
        )
        can_draw_overlay = bool(
            not bpy.app.background
            and getattr(context, "screen", None) is not None
            and any(area.type == "VIEW_3D" for area in context.screen.areas)
        )
        if can_draw_overlay:
            try:
                HierarchyOverlayController.enable(context)
            except Exception:
                clear_stored_hierarchy_inspection(clear_used_scope=True)
                cls._clear_runtime_fields(context)
                raise
        else:
            # Inspection remains useful for scripts and background acceptance;
            # only the transient GPU presentation layer is unavailable.
            runtime.hierarchy_overlay_enabled = False
        return plan

    @classmethod
    def _validated_session(cls, context) -> tuple[HierarchyInspectionSession, object]:
        session = get_hierarchy_inspection()
        if session is None:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_INSPECTION_MISSING")
        if cls._source_filepath() != session.source_filepath:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_FILE_CHANGED")
        armature = context.scene.objects.get(session.plan.armature_object_name)
        if (
            armature is None
            or armature.type != "ARMATURE"
            or armature.name != session.plan.armature_object_name
            or armature.data.name != session.armature_data_name
        ):
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_ARMATURE_CHANGED")
        if armature_structural_fingerprint(armature) != session.plan.armature_fingerprint:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_ARMATURE_CHANGED")
        return session, armature

    @classmethod
    def select_scope(cls, context) -> tuple[str, ...]:
        """Select the inspected names while preserving the inspection root as active."""
        session, armature = cls._validated_session(context)
        plan = session.plan
        names = set(plan.selected_bone_names) - set(session.snapshot.excluded_helper_names)
        if (
            plan.parent_context_name is not None
            and plan.parent_context_name not in plan.selected_bone_names
        ):
            names.discard(plan.parent_context_name)
        context.view_layer.objects.active = armature
        armature.select_set(True)
        if context.mode == "EDIT_ARMATURE" and context.object == armature:
            for bone in armature.data.edit_bones:
                selected = bone.name in names
                bone.select = selected
                bone.select_head = selected
                bone.select_tail = selected
            armature.data.edit_bones.active = armature.data.edit_bones.get(plan.active_bone_name)
        else:
            # Blender 5.2 moved object/pose selection to PoseBone.
            # In Pose Mode the selection cache can retain the previous active
            # set until the pose operator explicitly clears it.  Direct RNA
            # assignment alone then appears to succeed but leaves no selected
            # bones in the interactive viewport.
            if context.mode == "POSE" and context.object == armature:
                try:
                    bpy.ops.pose.select_all(action="DESELECT")
                except RuntimeError:
                    pass
            for pose_bone in armature.pose.bones:
                pose_bone.select = pose_bone.name in names
            armature.data.bones.active = armature.data.bones.get(plan.active_bone_name)
            context.view_layer.update()
        return session.index.order_names(names)

    @staticmethod
    def _freeze(session: HierarchyInspectionSession) -> FrozenInspectionScope:
        accepted_names = (
            set(session.plan.selected_bone_names)
            | set(session.plan.side_branch_root_names)
        ) - set(session.snapshot.excluded_helper_names)
        bone_names = session.index.order_names(
            accepted_names
        )
        return FrozenInspectionScope(
            inspection_id=session.plan.inspection_id,
            armature_object_name=session.plan.armature_object_name,
            armature_data_name=session.armature_data_name,
            armature_fingerprint=session.plan.armature_fingerprint,
            source_filepath=session.source_filepath,
            bone_names=bone_names,
            manual_branch_continuations=session.manual_branch_continuations,
            reference_only_tip_helper_names=session.plan.tip_helper_names,
        )

    @classmethod
    def use_scope(cls, context) -> FrozenInspectionScope:
        session, _armature = cls._validated_session(context)
        if get_used_semantic_scope() is not None:
            raise HierarchyInspectionRuntimeError("UECP_SCOPE_SOURCE_CONFLICT")
        selected = set(session.plan.selected_bone_names)
        missing_helper_parents = tuple(
            parent_name
            for helper_name in session.plan.tip_helper_names
            for parent_name in (session.index.parent_of(helper_name),)
            if parent_name is not None and parent_name not in selected
        )
        if missing_helper_parents:
            raise HierarchyInspectionRuntimeError(
                "UECP_HIERARCHY_TIP_HELPER_PARENT_REQUIRED: "
                + ", ".join(sorted(set(missing_helper_parents)))
            )
        scope = cls._freeze(session)
        if not scope.bone_names:
            raise HierarchyInspectionRuntimeError("UECP_EMPTY_SELECTION")
        put_used_inspection_scope(scope)
        cls._sync_runtime(context, session, scope_used=True)
        cls._mark_analyzed_plan_stale(context)
        return scope

    @classmethod
    def set_branch_continuation(cls, context, branch_name: str, child_name: str):
        session, _armature = cls._validated_session(context)
        effective_children = tuple(
            name
            for name in session.index.children_of(branch_name)
            if name not in session.snapshot.excluded_helper_names
        ) if branch_name in session.index else ()
        if (
            branch_name not in session.plan.branch_bone_names
            or child_name not in effective_children
        ):
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_BRANCH_INVALID")
        if len(effective_children) <= 1:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_BRANCH_INVALID")
        continuations = dict(session.snapshot.branch_continuations)
        continuations[branch_name] = child_name
        manual_continuations = dict(session.manual_branch_continuations)
        manual_continuations[branch_name] = child_name
        selection_mode = session.snapshot.selection_mode
        if selection_mode in {
            HierarchySelectionMode.LINEAR_CHAIN.value,
            HierarchySelectionMode.SAME_STEM_CHAIN.value,
        }:
            selection_mode = HierarchySelectionMode.MAIN_PATH_TO_LEAF.value
        snapshot = dataclasses.replace(
            session.snapshot,
            selection_mode=selection_mode,
            branch_continuations=tuple(continuations.items()),
        )
        try:
            plan = build_hierarchy_inspection_plan(session.index, snapshot)
        except HierarchyInspectionError as exc:
            raise HierarchyInspectionRuntimeError(str(exc)) from exc
        updated = dataclasses.replace(
            session,
            plan=plan,
            snapshot=snapshot,
            manual_branch_continuations=tuple(sorted(manual_continuations.items())),
        )
        previous_used = get_used_inspection_scope()
        put_hierarchy_inspection(updated)
        if previous_used and previous_used.inspection_id == session.plan.inspection_id:
            put_used_inspection_scope(cls._freeze(updated))
            scope_used = True
        else:
            put_used_inspection_scope(None)
            scope_used = False
        cls._sync_runtime(context, updated, scope_used=scope_used)
        if scope_used:
            cls._mark_analyzed_plan_stale(context)
        HierarchyOverlayController.refresh(context)
        return plan

    @classmethod
    def validate_frozen_scope(cls, context, scope: FrozenInspectionScope) -> object:
        if cls._source_filepath() != scope.source_filepath:
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_FILE_CHANGED")
        armature = context.scene.objects.get(scope.armature_object_name)
        if (
            armature is None
            or armature.type != "ARMATURE"
            or armature.name != scope.armature_object_name
            or armature.data.name != scope.armature_data_name
            or armature_structural_fingerprint(armature) != scope.armature_fingerprint
        ):
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_ARMATURE_CHANGED")
        if any(name not in armature.data.bones for name in scope.bone_names):
            raise HierarchyInspectionRuntimeError("UECP_HIERARCHY_ARMATURE_CHANGED")
        return armature

    @classmethod
    def analysis_scope(cls, context) -> FrozenInspectionScope | None:
        scope = get_used_inspection_scope()
        if scope is not None:
            cls.validate_frozen_scope(context, scope)
        return scope

    @classmethod
    def clear(cls, context) -> None:
        HierarchyOverlayController.disable(context)
        clear_stored_hierarchy_inspection(clear_used_scope=True)
        cls._clear_runtime_fields(context)
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        if runtime is not None:
            runtime.last_error = ""
