# Changelog

All notable changes to BoneWeaver are documented here.

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
