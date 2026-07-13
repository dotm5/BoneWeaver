from __future__ import annotations

import unittest

from boneweaver import contracts


class ContractSnapshotTests(unittest.TestCase):
    def test_versions_and_identity_are_stable(self) -> None:
        self.assertEqual(contracts.ADDON_ID, "boneweaver")
        self.assertEqual(contracts.ADDON_VERSION, "0.3.1")
        self.assertEqual(contracts.SCHEMA_VERSION, "4.0.0")
        self.assertEqual(
            contracts.ALGORITHM_VERSION,
            "boneweaver-physics-graph-v4-tip-helper-branch-island-visual-cleanup",
        )

    def test_stable_enum_values_match_spec(self) -> None:
        expected = {
            "ScopeMode": {"SELECTED_BONES", "SELECTED_ROOTS_AND_DESCENDANTS", "ACTIVE_BONE_COLLECTION"},
            "MeshScope": {"ACTIVE_ASSOCIATED_MESH", "CHECKED_ASSOCIATED_MESHES", "ALL_ASSOCIATED_MESHES"},
            "ValidationToleranceMode": {"AUTO_PRODUCTION", "STRICT_TEST", "CUSTOM"},
            "PhysicsProfile": {"BONEX_ROTATION_CHAIN", "BONEX_TRANSLATION_ALLOWED", "WIGGLE2_ROTATION_CHAIN", "WIGGLE2_STRETCH_CHAIN", "GEOMETRY_ONLY", "VISUAL_CHAIN_CLEANUP"},
            "BranchResolutionMode": {"AUTO_MAIN_PATH", "LONGEST_PATH_ONLY", "DIRECTION_CONTINUITY", "MANUAL_ONLY", "KEEP_ORIGINAL"},
            "WeightIslandPolicy": {"DOMINANT_COMPONENT", "REQUIRE_SINGLE_COMPONENT", "ALL_COMPATIBLE_COMPONENTS"},
            "TerminalMode": {"AUTO_HYBRID", "UNIQUE_CHILD_ONLY", "IMPORTED_FORWARD_AXIS_ONLY", "WEIGHT_CLOUD_ONLY", "PARENT_EXTRAPOLATION_ONLY", "ORIGINAL_AXIS_ONLY", "MANUAL_ONLY"},
            "TerminalSource": {"MANUAL_OVERRIDE", "EXISTING_TIP_HELPER_HEAD", "UNIQUE_DIRECT_CHILD_HEAD", "IMPORTED_FORWARD_AXIS_DUMMY", "WEIGHT_CLOUD_LINEAR", "WEIGHT_CLOUD_PLANAR_BLEND", "PARENT_CHAIN_EXTRAPOLATION", "ORIGINAL_LOCAL_Y", "HYBRID_CANDIDATE_SCORE", "UNRESOLVED"},
            "BoneSemanticRole": {"DEFORM_SEGMENT", "EXISTING_TIP_HELPER", "CONTROL_EFFECTOR", "TWIST_HELPER", "SOCKET_HELPER", "UNKNOWN_HELPER"},
            "TipHelperUsage": {"REFERENCE_ONLY", "INCLUDE_AS_PHYSICS_TERMINAL"},
            "TerminalResolutionClass": {"AUTO_CONFIDENT", "AUTO_SAFE_FALLBACK", "MANUAL", "UNRESOLVED"},
            "TerminalCandidateKind": {"MANUAL", "DIRECT_CHILD", "IMPORTED_AXIS", "WEIGHT_PRINCIPAL_AXIS", "WEIGHT_CENTROID", "WEIGHT_PLANAR_BLEND", "PARENT_TANGENT", "ORIGINAL_DISPLAY_AXIS"},
            "BoneForwardAxis": {"AUTO", "X_POSITIVE", "X_NEGATIVE", "Y_POSITIVE", "Y_NEGATIVE", "Z_POSITIVE", "Z_NEGATIVE"},
            "TipLengthMode": {"AUTO_EVIDENCE", "WEIGHT_PERCENTILE", "PREVIOUS_SEGMENT", "CHAIN_MEDIAN", "ABSOLUTE"},
            "PhysicsNodeKind": {"REAL_BONE", "VIRTUAL_TIP"},
            "PhysicsEdgeKind": {"HIERARCHY_SEGMENT", "VIRTUAL_TIP_SEGMENT"},
            "RollMode": {"MINIMAL_TWIST", "PARALLEL_TRANSPORT", "RADIAL_REFERENCE", "KEEP_NUMERIC_ROLL"},
            "RadialReferenceMode": {"ARMATURE_ORIGIN", "CURSOR", "OBJECT", "BONE_HEAD"},
            "ExclusivityMode": {"NONE", "CHAIN_NORMALIZED", "SELECTED_SET_NORMALIZED"},
            "PlanState": {"IDLE", "ANALYZED", "STALE", "APPLYING", "APPLIED", "VALIDATION_FAILED", "RESTORABLE", "RESTORED", "ERROR"},
            "PlanAvailability": {"NONE", "AVAILABLE", "MISSING"},
            "WorkflowStage": {"NO_CONTEXT", "READY_TO_ANALYZE", "ANALYZING", "READY_TO_APPLY", "NEEDS_ATTENTION", "BLOCKED", "STALE_SETTINGS", "STALE_SELECTION", "PLAN_LOST", "APPLYING", "APPLIED", "ROLLBACK_FAILED", "ERROR"},
            "ActionAvailability": {"ENABLED", "DISABLED"},
            "IssueSeverity": {"INFO", "WARNING", "BLOCKER"},
            "OverrideMode": {"NONE", "CURSOR_POSITION", "REFERENCE_OBJECT", "EXPLICIT_DIRECTION_LENGTH", "MESH_VERTEX"},
        }
        for name, values in expected.items():
            enum_type = getattr(contracts, name)
            self.assertEqual({item.value for item in enum_type}, values, name)

    def test_operator_ids_are_centralized(self) -> None:
        self.assertEqual(
            contracts.OPERATOR_IDS,
            {
                "analyze": "boneweaver.analyze",
                "check_and_preview": "boneweaver.check_and_preview",
                "apply": "boneweaver.apply",
                "validate": "boneweaver.validate",
                "preview_toggle": "boneweaver.preview_toggle",
                "restore_snapshot": "boneweaver.restore_snapshot",
                "export_report": "boneweaver.export_report",
                "export_conversion": "boneweaver.export_conversion",
                "clear_runtime": "boneweaver.clear_runtime",
                "locate_issue": "boneweaver.locate_issue",
                "load_details": "boneweaver.load_details",
                "inspect_active_hierarchy": "boneweaver.inspect_active_hierarchy",
                "select_inspected_scope": "boneweaver.select_inspected_scope",
                "use_inspected_scope": "boneweaver.use_inspected_scope",
                "set_branch_continuation": "boneweaver.set_branch_continuation",
                "clear_hierarchy_inspection": "boneweaver.clear_hierarchy_inspection",
                "discover_secondary_chains": "boneweaver.discover_secondary_chains",
                "select_discovered_chain": "boneweaver.select_discovered_chain",
                "use_discovered_chains": "boneweaver.use_discovered_chains",
                "clear_semantic_discovery": "boneweaver.clear_semantic_discovery",
                "export_semantic_discovery": "boneweaver.export_semantic_discovery",
                "quick_reorient_auto": "boneweaver.quick_reorient_auto",
                "quick_reorient_restore": "boneweaver.quick_reorient_restore",
            },
        )

    def test_required_error_codes_are_present(self) -> None:
        required = {
            "BONEWEAVER_NO_ACTIVE_ARMATURE", "BONEWEAVER_EMPTY_SELECTION", "BONEWEAVER_NON_IDENTITY_POSE",
            "BONEWEAVER_EXTERNAL_CONNECTED_CHILD", "BONEWEAVER_BRANCH_AMBIGUOUS", "BONEWEAVER_COINCIDENT_HELPER",
            "BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS", "BONEWEAVER_PHYSICS_GRAPH_INVALID",
            "BONEWEAVER_GRAPH_PROJECTION_MISMATCH", "BONEWEAVER_STATE_CHANGED_AFTER_ANALYZE",
            "BONEWEAVER_WEIGHT_DIGEST_CHANGED", "BONEWEAVER_NEUTRAL_MESH_CHANGED",
            "BONEWEAVER_SNAPSHOT_WRITE_FAILED", "BONEWEAVER_ROLLBACK_FAILED", "BONEWEAVER_RESTORE_CONFLICT",
            "BONEWEAVER_SCHEMA_VERSION_UNSUPPORTED", "BONEWEAVER_INTERNAL_ERROR",
            "BONEWEAVER_BRANCH_AUTO_MAIN_SKELETON_FORBIDDEN",
            "BONEWEAVER_BRANCH_AUTO_SECONDARY_SEMANTICS_REQUIRED",
            "BONEWEAVER_WEIGHT_ISLAND_POLICY_BLOCKED",
            "BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH",
            "BONEWEAVER_HIERARCHY_ARMATURE_CHANGED",
            "BONEWEAVER_SEMANTIC_CONFIRMATION_REQUIRED",
            "BONEWEAVER_SCOPE_SOURCE_CONFLICT",
        }
        self.assertTrue(required.issubset(contracts.ERROR_CODES))
        self.assertTrue(all(code.startswith("BONEWEAVER_") for code in contracts.ERROR_CODES))

    def test_candidate_scoring_profile_is_versioned_and_normalized(self) -> None:
        profile = dict(contracts.CANDIDATE_SCORING_PROFILE)
        self.assertEqual(
            set(profile),
            {"mesh_support", "chain_continuity", "cloud_shape_suitability", "imported_axis_prior", "length_plausibility"},
        )
        self.assertAlmostEqual(sum(profile.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
