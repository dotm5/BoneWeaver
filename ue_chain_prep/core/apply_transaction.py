"""Atomic EditBone application with persistent pre-state snapshot and rollback."""

from __future__ import annotations

import datetime as dt
import dataclasses
import json
import time

import bpy
from mathutils import Vector

from .canonical import sha256
from .context_guard import ContextStateGuard
from .models import TransactionResult
from .mutation_ledger import (
    build_mutation_records,
    validate_mutation_records,
    with_mutation_count,
)
from .validation import capture_armature_state, capture_neutral_meshes, validate_post_apply


def _activate_armature(context, armature):
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    context.view_layer.objects.active = armature


def _capture_edit_state(armature, names):
    return {
        name: {
            "head": tuple(float(value) for value in armature.data.edit_bones[name].head),
            "parent_name": armature.data.edit_bones[name].parent.name if armature.data.edit_bones[name].parent else None,
            "tail": tuple(float(value) for value in armature.data.edit_bones[name].tail),
            "roll": float(armature.data.edit_bones[name].roll),
            "use_connect": bool(armature.data.edit_bones[name].use_connect),
        }
        for name in names
    }


def _write_fields(armature, states):
    for name in states:
        armature.data.edit_bones[name].use_connect = False
    for name, state in states.items():
        bone = armature.data.edit_bones[name]
        bone.tail = state["tail"]
        bone.roll = state["roll"]
    for name, state in states.items():
        armature.data.edit_bones[name].use_connect = state["use_connect"]


def _default_validator(context, plan):
    armature = bpy.data.objects[plan.armature_object_name]
    for proposal in plan.proposals:
        bone = armature.data.bones[proposal.bone_name]
        if (bone.tail_local - Vector(proposal.proposed_tail)).length > 1.0e-6:
            return False
        expected = next(state for state in plan.bone_states if state.name == proposal.bone_name)
        if (bone.head_local - Vector(expected.head)).length > 1.0e-7:
            return False
    return True


def apply_plan(context, plan, *, validator=None):
    apply_started = time.perf_counter()
    validation_time = 0.0
    neutral_baseline = capture_neutral_meshes(plan)
    armature_baseline = capture_armature_state(bpy.data.objects[plan.armature_object_name])
    custom_validator = validator
    armature = bpy.data.objects[plan.armature_object_name]
    proposal_names = tuple(proposal.bone_name for proposal in plan.proposals)
    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot_id = ""
    text_name = ""
    pre_state = {}
    created_role_collections = []
    mutation_records = ()
    topology_ledger = plan.topology_ledger
    with ContextStateGuard(context):
        try:
            _activate_armature(context, armature)
            armature.data.use_mirror_x = False
            bpy.ops.object.mode_set(mode="EDIT")
            pre_state = _capture_edit_state(armature, proposal_names)
            bpy.ops.object.mode_set(mode="OBJECT")
            snapshot_id = sha256((plan.plan_id, pre_state, created_at))
            text_name = f"UECP_SNAPSHOT::{snapshot_id}"
            payload = {
                "kind": "uecp.snapshot", "schema_version": plan.schema_version,
                "algorithm_version": plan.algorithm_version, "snapshot_id": snapshot_id,
                "plan_id": plan.plan_id, "physics_graph_id": plan.physics_graph.graph_id,
                "created_at": created_at,
                "armature": {"object_name": armature.name, "data_name": armature.data.name},
                "pre_bones": pre_state,
                "expected_post_bones": {
                    proposal.bone_name: {
                        "tail": proposal.proposed_tail,
                        "roll_reference_z": proposal.proposed_roll_reference_z,
                        "use_connect": proposal.final_use_connect,
                    }
                    for proposal in plan.proposals
                },
                "mesh_digests": {state.object_name: state.vertex_group_digest for state in plan.mesh_states},
                "modifier_digests": {state.object_name: state.modifier_digest for state in plan.mesh_states},
                "object_counts": {"objects": len(bpy.data.objects), "bones": len(armature.data.bones)},
                "status": "CREATED",
            }
            text = bpy.data.texts.new(text_name)
            text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
            bpy.ops.object.mode_set(mode="EDIT")
            for name in proposal_names:
                armature.data.edit_bones[name].use_connect = False
            for proposal in plan.proposals:
                bone = armature.data.edit_bones[proposal.bone_name]
                bone.tail = proposal.proposed_tail
                if "UECP_KEEP_NUMERIC_ROLL" in proposal.issue_codes:
                    bone.roll = proposal.original_roll
                else:
                    bone.align_roll(Vector(proposal.proposed_roll_reference_z))
            for proposal in plan.proposals:
                armature.data.edit_bones[proposal.bone_name].use_connect = proposal.final_use_connect
            post_state = _capture_edit_state(armature, proposal_names)
            payload["expected_post_bones"] = post_state
            mutation_records = build_mutation_records(plan, pre_state, post_state)
            ledger_issues = validate_mutation_records(plan, pre_state, post_state, mutation_records)
            if ledger_issues:
                raise RuntimeError("mutation ledger validation failed: " + ", ".join(ledger_issues))
            topology_ledger = with_mutation_count(plan.topology_ledger, len(mutation_records))
            payload["mutation_records"] = [dataclasses.asdict(record) for record in mutation_records]
            payload["topology_ledger"] = dataclasses.asdict(topology_ledger)
            bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.update()
            validation_started = time.perf_counter()
            if custom_validator is None:
                validation = validate_post_apply(context, plan, neutral_baseline, armature_baseline)
                validation_time = time.perf_counter() - validation_started
                if not validation.success:
                    raise RuntimeError(
                        "post validation failed: " + ", ".join(validation.issues)
                        + f"; maximum_neutral_mesh_delta={validation.maximum_neutral_mesh_delta:.17g}"
                        + f"; allowed_neutral_mesh_delta={validation.allowed_neutral_mesh_delta:.17g}"
                        + f"; non_target_bones={validation.non_target_bone_names}"
                    )
                payload["post_validation"] = dataclasses.asdict(validation)
            elif not custom_validator(context, plan):
                validation_time = time.perf_counter() - validation_started
                raise RuntimeError("post validation failed")
            else:
                validation_time = time.perf_counter() - validation_started
            if any("UECP_CREATE_ROLE_COLLECTIONS" in proposal.issue_codes for proposal in plan.proposals):
                collection_names = (
                    "UECP_Anchors", "UECP_Dynamics", "UECP_BranchBoundaries", "UECP_LowConfidence"
                )
                collections = {}
                for name in collection_names:
                    collection = armature.data.collections.get(name)
                    if collection is None:
                        collection = armature.data.collections.new(name)
                        created_role_collections.append(collection)
                    collections[name] = collection
                for proposal in plan.proposals:
                    target = collections["UECP_Anchors"] if proposal.role == "ANCHOR" else collections["UECP_Dynamics"]
                    target.assign(armature.data.bones[proposal.bone_name])
            payload["status"] = "APPLIED"
            text.clear()
            text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
            return TransactionResult(
                True, False, snapshot_id, text_name, None,
                mutation_records, topology_ledger,
                time.perf_counter() - apply_started, validation_time,
            )
        except Exception as error:
            try:
                _activate_armature(context, armature)
                armature.data.use_mirror_x = False
                bpy.ops.object.mode_set(mode="EDIT")
                _write_fields(armature, pre_state)
                bpy.ops.object.mode_set(mode="OBJECT")
                for collection in reversed(created_role_collections):
                    if armature.data.collections.get(collection.name):
                        armature.data.collections.remove(collection)
                context.view_layer.update()
                if text_name and text_name in bpy.data.texts:
                    payload["status"] = "ROLLED_BACK"
                    text = bpy.data.texts[text_name]
                    text.clear()
                    text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
                return TransactionResult(
                    False, True, snapshot_id, text_name, str(error),
                    mutation_records, topology_ledger,
                    time.perf_counter() - apply_started, validation_time,
                )
            except Exception as rollback_error:
                return TransactionResult(
                    False, False, snapshot_id, text_name,
                    f"{error}; rollback failed: {rollback_error}",
                    mutation_records, topology_ledger,
                    time.perf_counter() - apply_started, validation_time,
                )
