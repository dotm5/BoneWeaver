# Changelog

All notable changes to BoneWeaver are documented here.

## 0.4.0 - 2026-07-26

- Replaced the single panel-top action with three explicit one-click choices:
  original UEFormat-compatible conversion, link-only native-chain rebuilding,
  and experimental multi-feature conversion with per-bone fallback.
- Added whole-Armature link-only planning for already well-oriented rigs. It
  performs no direction inference and rebuilds maximal linear components for
  Blender's native `L` selection.
- Wrapped the existing weight, hierarchy, branch, terminal, and roll evidence
  pipeline as an automatic hybrid planner. Only confident per-bone proposals are
  accepted; every missing, ambiguous, invalid, or low-confidence result keeps
  the precomputed UEFormat-compatible fallback.
- Converted precision-planner blockers to advisory evidence in hybrid mode, so
  one unresolved bone or a complete precision-planner exception cannot stop the
  force-complete operation.
- Added mode-specific idempotence metadata, persistent Snapshot recovery, UI
  source counts, injected invalid-result regressions, and three-mode real-asset
  acceptance tooling.
- Validated 230 Blender-hosted tests and all three modes independently on the
  existing `x1.blend` and a raw 157-bone `.uemodel`.

## 0.3.1 - 2026-07-13

- Changed the panel-top Quick Reorient action to force-complete mode: all
  previous Action, NLA, Driver, Constraint, Pose, B-Bone, parenting, envelope,
  modifier, transform, and mesh policy blockers are now advisory diagnostics.
- Removed the confirmation dialog so the panel button starts and completes the
  automatic conversion with one click.
- Automatically localizes linked Armature data when Blender permits it and
  makes shared Armature data single-user before planning.
- Made mesh and neutral-evaluation diagnostics best-effort in one-click mode;
  failed diagnostics are recorded in the Snapshot but no longer roll back a
  completed bone conversion.
- Preserved strict validation for the separate scoped Physics Graph workflow
  and for direct callers that explicitly use strict Quick Transaction mode.
- Added a combined former-blocker regression fixture and raised the complete
  Blender-hosted suite to 223 passing tests.

## 0.3.0 - 2026-07-13

- Added a panel-top **Auto Convert and Rebuild L-key Chains** action that runs
  whole-Armature analysis, mutation, validation, Snapshot persistence, and UI
  status updates as one confirmed operation.
- Added clean-room UEFormat-compatible dominant-axis and average-child bone
  reorientation with metadata, generic-hierarchy, Socket, control-bone, and
  already-reoriented source adapters.
- Rebuilt maximal unambiguous linear components using native EditBone
  `use_connect`, while preserving branch boundaries so Blender's `L` linked
  selection works without a custom selection operator.
- Added automatic rollback, conflict-aware exact Restore, idempotence markers,
  mesh/neutral-geometry invariants, immutable Plans, and persistent Snapshots.
- Added unit, transaction, registration, Schema, UI, and native linked-selection
  coverage; 220 Blender-hosted tests pass.
- Validated numerical parity against fixed UEFormat commit
  `8da96d65f669ca688dbf7c0141f800605a6c16e6` and completed read-only real-asset
  acceptance on a raw 157-bone `.uemodel` plus `x1.blend`.

## 0.2.0 - 2026-07-12

Initial public preview.

- Renamed the complete extension, runtime, schema, and repository identity to
  BoneWeaver without legacy aliases.
- Added five hierarchy inspection modes, deterministic frozen scopes, manual
  branch continuation, cached viewport overlays, and confirmed semantic
  secondary-chain discovery.
- Added conservative Existing Tip Helper classification and opt-in
  `VISUAL_CHAIN_CLEANUP` behavior.
- Added policy-driven per-Mesh weight-island handling, Armature-scoped
  overrides, mutation/topology ledgers, export gates, and independent reopen
  validation.
- Hardened Analyze, Apply, Restore, and export against stale Edit Mode data,
  transform drift, whole-Armature conflicts, and unsafe branch/terminal
  inference.
- Fixed preview-line viewport sizing and made issue presentation identify the
  affected bone clearly.
- Validated 208 Blender-hosted tests and a real 157-bone UE asset workflow.
