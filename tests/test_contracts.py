from __future__ import annotations

import unittest

from ue_chain_prep import contracts


class ContractSnapshotTests(unittest.TestCase):
    def test_versions_and_identity_are_stable(self) -> None:
        self.assertEqual(contracts.ADDON_ID, "ue_chain_prep")
        self.assertEqual(contracts.ADDON_VERSION, "0.1.2")
        self.assertEqual(contracts.SCHEMA_VERSION, "3.1.0")
        self.assertEqual(contracts.ALGORITHM_VERSION, "uecp-physics-graph-v3-interaction-hardening")

    def test_stable_enum_values_match_spec(self) -> None:
        expected = {
            "ScopeMode": {"SELECTED_BONES", "SELECTED_ROOTS_AND_DESCENDANTS", "ACTIVE_BONE_COLLECTION"},
            "MeshScope": {"ACTIVE_ASSOCIATED_MESH", "CHECKED_ASSOCIATED_MESHES", "ALL_ASSOCIATED_MESHES"},
            "PhysicsProfile": {"BONEX_ROTATION_CHAIN", "BONEX_TRANSLATION_ALLOWED", "WIGGLE2_ROTATION_CHAIN", "WIGGLE2_STRETCH_CHAIN", "GEOMETRY_ONLY"},
            "TerminalMode": {"AUTO_HYBRID", "UNIQUE_CHILD_ONLY", "IMPORTED_FORWARD_AXIS_ONLY", "WEIGHT_CLOUD_ONLY", "PARENT_EXTRAPOLATION_ONLY", "ORIGINAL_AXIS_ONLY", "MANUAL_ONLY"},
            "TerminalSource": {"MANUAL_OVERRIDE", "UNIQUE_DIRECT_CHILD_HEAD", "IMPORTED_FORWARD_AXIS_DUMMY", "WEIGHT_CLOUD_LINEAR", "WEIGHT_CLOUD_PLANAR_BLEND", "PARENT_CHAIN_EXTRAPOLATION", "ORIGINAL_LOCAL_Y", "HYBRID_CANDIDATE_SCORE", "UNRESOLVED"},
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
                "analyze": "uecp.analyze",
                "check_and_preview": "uecp.check_and_preview",
                "apply": "uecp.apply",
                "validate": "uecp.validate",
                "preview_toggle": "uecp.preview_toggle",
                "restore_snapshot": "uecp.restore_snapshot",
                "export_report": "uecp.export_report",
                "export_conversion": "uecp.export_conversion",
                "clear_runtime": "uecp.clear_runtime",
                "locate_issue": "uecp.locate_issue",
                "load_details": "uecp.load_details",
            },
        )

    def test_required_error_codes_are_present(self) -> None:
        required = {
            "UECP_NO_ACTIVE_ARMATURE", "UECP_EMPTY_SELECTION", "UECP_NON_IDENTITY_POSE",
            "UECP_EXTERNAL_CONNECTED_CHILD", "UECP_BRANCH_AMBIGUOUS", "UECP_COINCIDENT_HELPER",
            "UECP_TERMINAL_CANDIDATE_AMBIGUOUS", "UECP_PHYSICS_GRAPH_INVALID",
            "UECP_GRAPH_PROJECTION_MISMATCH", "UECP_STATE_CHANGED_AFTER_ANALYZE",
            "UECP_WEIGHT_DIGEST_CHANGED", "UECP_NEUTRAL_MESH_CHANGED",
            "UECP_SNAPSHOT_WRITE_FAILED", "UECP_ROLLBACK_FAILED", "UECP_RESTORE_CONFLICT",
            "UECP_SCHEMA_VERSION_UNSUPPORTED", "UECP_INTERNAL_ERROR",
        }
        self.assertTrue(required.issubset(contracts.ERROR_CODES))
        self.assertTrue(all(code.startswith("UECP_") for code in contracts.ERROR_CODES))

    def test_candidate_scoring_profile_is_versioned_and_normalized(self) -> None:
        profile = dict(contracts.CANDIDATE_SCORING_PROFILE)
        self.assertEqual(
            set(profile),
            {"mesh_support", "chain_continuity", "cloud_shape_suitability", "imported_axis_prior", "length_plausibility"},
        )
        self.assertAlmostEqual(sum(profile.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
