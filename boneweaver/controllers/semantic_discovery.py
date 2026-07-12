"""Blender adapter for immutable semantic discovery and confirmed Analyze scope."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import bpy

from ..contracts import PlanState
from ..core.armature_reader import read_bone_states
from ..core.canonical import sha256
from ..core.fingerprint import current_source_fingerprint, settings_fingerprint
from ..core.mesh_resolver import find_associated_meshes
from ..core.mesh_scan_cache import MeshScanCache
from ..core.runtime_store import (
    FrozenSemanticScope,
    SemanticDiscoverySession,
    bind_analysis_scope,
    clear_semantic_discovery as clear_stored_semantic_discovery,
    get_analysis_scope,
    get_plan,
    get_semantic_discovery,
    get_used_inspection_scope,
    get_used_semantic_scope,
    has_plan,
    put_semantic_discovery,
    put_used_semantic_scope,
)
from ..core.semantic_discovery import build_semantic_discovery_plan
from ..core.semantic_models import (
    SecondaryBoneCategory,
    SemanticDiscoveryClass,
)
from ..core.semantic_serialization import semantic_discovery_plan_to_json
from ..core.semantic_rule_loader import (
    load_default_rule_set,
    load_rule_set,
    merge_rule_sets,
)
from ..core.weight_cloud import analyze_weight_cloud
from ..core.weight_islands import resolve_weight_islands
from .selection import SelectionController


_HIERARCHY_HELPER_EXCLUSION_CATEGORIES = frozenset({
    SecondaryBoneCategory.SOCKET.value,
    SecondaryBoneCategory.IK_CONTROL.value,
    SecondaryBoneCategory.TWIST_DEFORM.value,
})


class SemanticDiscoveryRuntimeError(RuntimeError):
    """A discovery operation cannot safely use the current Blender context."""


class SemanticDiscoveryController:
    @staticmethod
    def _armature_fingerprint(armature, bone_states=None) -> str:
        states = bone_states or read_bone_states(
            armature,
            tuple(sorted(bone.name for bone in armature.data.bones)),
        )
        return sha256(
            (
                armature.data.name,
                tuple(
                    (
                        state.name, state.parent_name, state.child_names,
                        state.head, state.tail, state.use_connect, state.use_deform,
                        state.is_socket, state.importer_metadata_flags,
                    )
                    for state in states
                ),
            )
        )

    @staticmethod
    def _source_filepath() -> str:
        return str(getattr(bpy.data, "filepath", "") or "")

    @staticmethod
    def _active_armature(context):
        armature, _source = SelectionController.armature_from_context(context)
        if armature is None:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_NO_ACTIVE_ARMATURE")
        return armature

    @staticmethod
    def _reusable_weight_clouds(context, armature, bone_states):
        """Reuse an already-valid Analyze snapshot without reading meshes again."""
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if (
            runtime is None
            or runtime.state != PlanState.ANALYZED.value
            or not runtime.plan_id
            or not has_plan(runtime.plan_id)
        ):
            return ()
        plan = get_plan(runtime.plan_id)
        settings = getattr(context.scene, "boneweaver_settings", None)
        if (
            runtime.plan_fingerprint != plan.source_fingerprint
            or settings is None
            or settings_fingerprint(settings) != plan.settings_fingerprint
            or plan.armature_object_name != armature.name
            or plan.armature_data_name != armature.data.name
        ):
            return ()
        current_names = {state.name for state in bone_states}
        plan_names = {state.name for state in plan.bone_states}
        cloud_names = {cloud.bone_name for cloud in plan.weight_clouds}
        if (
            plan_names != current_names
            or cloud_names != current_names
            or len(plan.weight_clouds) != len(current_names)
        ):
            return ()
        if current_source_fingerprint(context, plan) != plan.source_fingerprint:
            return ()
        current_by_name = {state.name: state for state in bone_states}
        if any(current_by_name.get(state.name) != state for state in plan.bone_states):
            return ()
        return plan.weight_clouds

    @staticmethod
    def _fresh_weight_clouds(context, armature, bone_states):
        """Collect read-only full-Armature weight evidence in one Mesh scan."""
        settings = getattr(context.scene, "boneweaver_settings", None)
        if settings is None:
            return ()
        bindings, _issues = find_associated_meshes(armature)
        mesh_objects = tuple(
            context.scene.objects.get(binding.object_name)
            for binding in bindings
        )
        mesh_objects = tuple(
            item for item in mesh_objects if item is not None and item.type == "MESH"
        )
        if not mesh_objects:
            return ()
        scan_cache = MeshScanCache.scan(
            armature,
            mesh_objects,
            tuple(state.name for state in bone_states),
            minimum_weight=settings.minimum_weight,
            weight_exponent=settings.weight_exponent,
            use_vertex_area_weight=settings.use_vertex_area_weight,
            exclusivity_mode=settings.exclusivity_mode,
        )
        clouds = []
        for state in bone_states:
            resolution = resolve_weight_islands(
                state.name,
                state.head,
                scan_cache.per_mesh_inputs_by_bone.get(state.name, ()),
                policy=settings.weight_island_policy,
            )
            cloud = analyze_weight_cloud(
                state.name,
                state.head,
                resolution.selected_weighted_points,
                tuple(item.mesh_name for item in resolution.per_mesh_clouds),
                settings.terminal_percentile,
            )
            clouds.append(dataclasses.replace(
                cloud,
                warnings=tuple(sorted(set(cloud.warnings + resolution.warnings))),
                per_mesh_clouds=resolution.per_mesh_clouds,
                component_strategy=settings.weight_island_policy,
            ))
        return tuple(clouds)

    @classmethod
    def _weight_clouds(cls, context, armature, bone_states):
        reusable = cls._reusable_weight_clouds(context, armature, bone_states)
        if reusable:
            return reusable
        return cls._fresh_weight_clouds(context, armature, bone_states)

    @staticmethod
    def _sync_runtime(context, session: SemanticDiscoverySession) -> None:
        wm = context.window_manager
        runtime = getattr(wm, "boneweaver_runtime", None)
        items = getattr(wm, "boneweaver_semantic_chain_items", None)
        if items is not None:
            items.clear()
            confirmed = set(session.confirmed_chain_ids)
            for chain in session.plan.chains:
                item = items.add()
                item.chain_id = chain.discovery_id
                item.root_name = chain.root_bone_name
                item.category = chain.category
                item.discovery_class = chain.discovery_class
                item.discovery_score = chain.discovery_score
                item.branch_count = len(chain.branch_bone_names)
                item.reason_codes = ", ".join(chain.reason_codes)
                item.confirmed = chain.discovery_id in confirmed
        if runtime is None:
            return
        runtime.semantic_discovery_active = True
        runtime.semantic_discovery_plan_id = session.discovery_plan_id
        runtime.semantic_armature_fingerprint = session.plan.armature_fingerprint
        runtime.semantic_source_filepath = session.source_filepath
        runtime.semantic_chain_count = len(session.plan.chains)
        runtime.semantic_confirmed_count = len(session.confirmed_chain_ids)
        runtime.semantic_scope_used = bool(
            get_used_semantic_scope()
            and get_used_semantic_scope().discovery_plan_id == session.discovery_plan_id
        )
        runtime.last_error = ""

    @staticmethod
    def _clear_runtime_fields(context) -> None:
        wm = getattr(context, "window_manager", None)
        if wm is None:
            return
        items = getattr(wm, "boneweaver_semantic_chain_items", None)
        if items is not None:
            items.clear()
        runtime = getattr(wm, "boneweaver_runtime", None)
        if runtime is None:
            return
        runtime.semantic_discovery_active = False
        runtime.semantic_scope_used = False
        runtime.semantic_discovery_plan_id = ""
        runtime.semantic_armature_fingerprint = ""
        runtime.semantic_source_filepath = ""
        runtime.semantic_chain_count = 0
        runtime.semantic_confirmed_count = 0
        runtime.semantic_active_chain_index = 0

    @classmethod
    def discover(cls, context):
        """Read every Armature bone and associated weights without mutation."""
        armature = cls._active_armature(context)
        bone_states = read_bone_states(
            armature,
            tuple(sorted(bone.name for bone in armature.data.bones)),
        )
        fingerprint = cls._armature_fingerprint(armature, bone_states)
        settings = getattr(context.scene, "boneweaver_settings", None)
        rule_sets = [load_default_rule_set()]
        for property_name in (
            "semantic_source_adapter_rule_path",
            "semantic_game_rule_path",
            "semantic_user_rule_path",
        ):
            raw_path = getattr(settings, property_name, "") if settings is not None else ""
            if not raw_path:
                continue
            try:
                rule_sets.append(load_rule_set(Path(bpy.path.abspath(raw_path))))
            except (OSError, ValueError) as exc:
                raise SemanticDiscoveryRuntimeError(
                    f"BONEWEAVER_SEMANTIC_RULE_LOAD_FAILED: {property_name}: {exc}"
                ) from exc
        plan = build_semantic_discovery_plan(
            bone_states,
            armature_object_name=armature.name,
            armature_fingerprint=fingerprint,
            merged_rules=merge_rule_sets(rule_sets),
            weight_summaries=cls._weight_clouds(context, armature, bone_states),
        )
        session = SemanticDiscoverySession(
            plan=plan,
            discovery_plan_id=sha256(plan),
            source_filepath=cls._source_filepath(),
            armature_data_name=armature.data.name,
        )
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is not None and runtime.plan_id:
            bound_scope = get_analysis_scope(runtime.plan_id)
            if isinstance(bound_scope, FrozenSemanticScope):
                bind_analysis_scope(runtime.plan_id, None)
                cls._mark_analyzed_plan_stale(context)
        put_semantic_discovery(session)
        put_used_semantic_scope(None)
        cls._sync_runtime(context, session)
        return plan

    @classmethod
    def _validated_session(cls, context):
        session = get_semantic_discovery()
        if session is None:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_DISCOVERY_MISSING")
        if cls._source_filepath() != session.source_filepath:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_FILE_CHANGED")
        armature = context.scene.objects.get(session.plan.armature_object_name)
        if (
            armature is None
            or armature.type != "ARMATURE"
            or armature.data.name != session.armature_data_name
            or cls._armature_fingerprint(armature) != session.plan.armature_fingerprint
            or any(item.bone_name not in armature.data.bones for item in session.plan.bone_evidence)
        ):
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_ARMATURE_CHANGED")
        return session, armature

    @staticmethod
    def _chain(session, chain_id: str):
        chain = next(
            (item for item in session.plan.chains if item.discovery_id == chain_id),
            None,
        )
        if chain is None or chain.discovery_class == SemanticDiscoveryClass.EXCLUDE.value:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_CHAIN_INVALID")
        return chain

    @classmethod
    def select_chain(cls, context, chain_id: str) -> tuple[str, ...]:
        """Explicitly confirm one candidate, then select that complete chain only."""
        session, armature = cls._validated_session(context)
        chain = cls._chain(session, chain_id)
        newly_confirmed = chain_id not in session.confirmed_chain_ids
        confirmed = tuple(sorted(set(session.confirmed_chain_ids).union({chain_id})))
        session = dataclasses.replace(session, confirmed_chain_ids=confirmed)
        if newly_confirmed and get_used_semantic_scope() is not None:
            put_used_semantic_scope(None)
            cls._mark_analyzed_plan_stale(context)
        put_semantic_discovery(session)
        cls._sync_runtime(context, session)

        names = set(chain.bone_names) - set(session.plan.excluded_bones)
        context.view_layer.objects.active = armature
        armature.select_set(True)
        if context.mode == "EDIT_ARMATURE" and context.object == armature:
            for bone in armature.data.edit_bones:
                selected = bone.name in names
                bone.select = selected
                bone.select_head = selected
                bone.select_tail = selected
            armature.data.edit_bones.active = armature.data.edit_bones.get(chain.root_bone_name)
        else:
            # Blender 5.2 moved object/pose selection to PoseBone.
            if context.mode == "POSE" and context.object == armature:
                try:
                    bpy.ops.pose.select_all(action="DESELECT")
                except RuntimeError:
                    pass
            for pose_bone in armature.pose.bones:
                pose_bone.select = pose_bone.name in names
            armature.data.bones.active = armature.data.bones.get(chain.root_bone_name)
            context.view_layer.update()
        return tuple(sorted(names))

    @staticmethod
    def _mark_analyzed_plan_stale(context) -> None:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is None or runtime.state != PlanState.ANALYZED.value or not runtime.plan_id:
            return
        from .preview import PreviewController
        PreviewController.disable(context)
        runtime.state = PlanState.STALE.value
        runtime.last_error = "BONEWEAVER_SEMANTIC_SCOPE_CHANGED_REANALYZE"

    @classmethod
    def use_confirmed_chains(cls, context) -> FrozenSemanticScope:
        session, _armature = cls._validated_session(context)
        if get_used_inspection_scope() is not None:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SCOPE_SOURCE_CONFLICT")
        if not session.confirmed_chain_ids:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_CONFIRMATION_REQUIRED")
        chain_by_id = {chain.discovery_id: chain for chain in session.plan.chains}
        if any(chain_id not in chain_by_id for chain_id in session.confirmed_chain_ids):
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_CHAIN_INVALID")
        names = {
            name
            for chain_id in session.confirmed_chain_ids
            for name in chain_by_id[chain_id].bone_names
        } - set(session.plan.excluded_bones)
        if not names:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_EMPTY_SELECTION")
        scope = FrozenSemanticScope(
            discovery_plan_id=session.discovery_plan_id,
            armature_object_name=session.plan.armature_object_name,
            armature_data_name=session.armature_data_name,
            armature_fingerprint=session.plan.armature_fingerprint,
            source_filepath=session.source_filepath,
            bone_names=tuple(sorted(names)),
            confirmed_chain_ids=session.confirmed_chain_ids,
        )
        put_used_semantic_scope(scope)
        cls._sync_runtime(context, session)
        cls._mark_analyzed_plan_stale(context)
        return scope

    @classmethod
    def validate_frozen_scope(cls, context, scope: FrozenSemanticScope):
        if cls._source_filepath() != scope.source_filepath:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_FILE_CHANGED")
        session = get_semantic_discovery()
        if session is None or session.discovery_plan_id != scope.discovery_plan_id:
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_DISCOVERY_MISSING")
        armature = context.scene.objects.get(scope.armature_object_name)
        if (
            armature is None
            or armature.type != "ARMATURE"
            or armature.data.name != scope.armature_data_name
            or cls._armature_fingerprint(armature) != scope.armature_fingerprint
            or any(name not in armature.data.bones for name in scope.bone_names)
        ):
            raise SemanticDiscoveryRuntimeError("BONEWEAVER_SEMANTIC_ARMATURE_CHANGED")
        return armature

    @classmethod
    def analysis_scope(cls, context) -> FrozenSemanticScope | None:
        scope = get_used_semantic_scope()
        if scope is not None:
            cls.validate_frozen_scope(context, scope)
        return scope

    @classmethod
    def valid_hierarchy_evidence(cls, context, armature, fingerprint):
        """Return current semantic labels without ever treating EXCLUDE as a Tip Helper."""
        session = get_semantic_discovery()
        if (
            session is None
            or session.source_filepath != cls._source_filepath()
            or session.plan.armature_object_name != armature.name
            or session.armature_data_name != armature.data.name
            or session.plan.armature_fingerprint != cls._armature_fingerprint(armature)
        ):
            return (), ()
        categories = tuple(
            (item.bone_name, item.category)
            for item in session.plan.bone_evidence
        )
        excluded = tuple(
            item.bone_name
            for item in session.plan.bone_evidence
            if item.discovery_class == SemanticDiscoveryClass.EXCLUDE.value
            and item.category in _HIERARCHY_HELPER_EXCLUSION_CATEGORIES
        )
        return categories, excluded

    @classmethod
    def export_json(cls, context, filepath: str) -> None:
        session, _armature = cls._validated_session(context)
        Path(filepath).write_text(
            semantic_discovery_plan_to_json(session.plan) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def clear(cls, context) -> None:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is not None and runtime.plan_id:
            scope = get_analysis_scope(runtime.plan_id)
            if isinstance(scope, FrozenSemanticScope):
                bind_analysis_scope(runtime.plan_id, None)
                cls._mark_analyzed_plan_stale(context)
        clear_stored_semantic_discovery(clear_used_scope=True)
        cls._clear_runtime_fields(context)
        if runtime is not None and runtime.state != PlanState.STALE.value:
            runtime.last_error = ""
