# Changelog

## Interaction refactor

- Added pure `PanelViewState` workflow mapping and layered Main/Advanced/Details/Recovery/Developer panels.
- Centralized workflow, preview, session, selection, and export state changes in controllers; operators are thin adapters.
- Added Check and Preview, Apply confirmation, issue location, Plan Lost and distinct stale-selection/settings behavior.
- Made RNA detail lists lazy, cached GPU batches, compacted neutral mesh baselines, and added progress/tracemalloc metrics.
- Made Imported Axis prior metadata-aware and bumped the algorithm to `uecp-physics-graph-v3-interaction-hardening`; schema remains 3.1.0.

## Backend hardening - 2026-07-11

- Bumped schema from 3.0.0 to 3.1.0 and algorithm to `uecp-physics-graph-v2-backend-hardening`.
- Added production/strict/custom per-mesh neutral tolerance, no-op baseline, float32 ULP budget, sparse-noise gate, and recommendations.
- Added automatic safe leaf fallback, direction clustering, branch continuation, weight-island guards, scoped override upserts, mutation/topology ledgers, shared mesh scanning, export readiness, manifests, and independent reopen validation.

## 0.1.0 - 2026-07-11

- Added immutable Source Joint/Physics Graph planning from bone heads and hierarchy.
- Added virtual terminal tips, six-axis imported evidence, weight-cloud analysis, deterministic candidate scoring, and ambiguity blockers.
- Added Minimal Twist, opt-in Parallel Transport, radial roll references, and BoneX/Wiggle projection profiles.
- Added strict preflight, deterministic fingerprints, snapshot-backed atomic Apply, automatic rollback, conflict-aware Restore, preview lifecycle, validation, diagnostics, tests, and extension packaging.
- Added a version-guarded, reversible local support tool for BoneX 1.2.6's Blender 5.2 draw-context ID-write fault, with real-window regression coverage.
