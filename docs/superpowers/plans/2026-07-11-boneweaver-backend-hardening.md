# BoneWeaver Backend Hardening Implementation Plan

> **For agentic workers:** Execute inline in the listed order. Every production behavior change starts with a failing Blender unittest and is verified before the next task. Do not commit or push automatically.

**Goal:** Harden BoneWeaver analysis, projection, validation, export, and reopen verification without changing the normal panel workflow or weakening the strict mutation safety contract.

**Architecture:** Keep the immutable-plan and snapshot-backed transaction architecture. Add focused pure-Python backend modules for tolerance calculation, branch resolution, mesh scanning, ledgers, override scoping, and export readiness; Blender RNA remains a persistence adapter and the UI remains unchanged.

**Tech Stack:** Blender 5.2 Python, `bpy`, `mathutils`, Python standard library, Blender-hosted `unittest`, JSON Schema.

---

### Task 1: G01 per-mesh neutral validation

**Files:**
- Create: `boneweaver/core/validation_tolerance.py`
- Modify: `boneweaver/contracts.py`, `boneweaver/properties.py`, `boneweaver/core/models.py`, `boneweaver/core/validation.py`, `boneweaver/core/serialization.py`
- Test: `tests/test_validation_tolerance.py`, `tests/test_validation.py`

- [ ] Add failing pure tests for float32 ULP, strict/custom/auto limits, soft-noise pass, hard outlier failure, recommendations, tiny/large per-mesh scale, and non-uniform object scale independence.
- [ ] Run `blender.exe --background --factory-startup --python tests/run_blender_tests.py -- --pattern test_validation_tolerance.py --verbose` and confirm missing APIs fail.
- [ ] Implement centralized tolerance constants, `ValidationToleranceMode`, compact local captures, no-op baseline metrics, per-mesh `MeshValidationResult`, diagnostic world deltas, and aggregate post-validation status.
- [ ] Run focused validation tests and then the full Blender unittest suite.

### Task 2: G02 safe terminal fallback

**Files:**
- Modify: `boneweaver/contracts.py`, `boneweaver/core/models.py`, `boneweaver/core/terminal_candidates.py`, `boneweaver/core/planner.py`
- Test: `tests/test_terminal_fallback.py`, `tests/test_planner_settings.py`

- [ ] Add failing tests for valid/zero-length/no-parent/reverse-evidence parent fallback, 1-3 segment median length, and automatic-versus-manual classification.
- [ ] Implement `TerminalResolutionClass` and a pure parent-chain fallback resolver that yields `PARENT_CHAIN_EXTRAPOLATION`, requires confirmation, warns, and only blocks the enumerated unsafe cases.
- [ ] Verify focused and full tests.

### Task 3: G03 candidate direction clustering

**Files:**
- Modify: `boneweaver/properties.py`, `boneweaver/core/models.py`, `boneweaver/core/terminal_candidates.py`, `boneweaver/core/fingerprint.py`
- Test: `tests/test_terminal_candidates.py`

- [ ] Add failing tests for two/three near-parallel candidates, near-parallel evidence versus an opposite candidate, distinct clusters, bounded support bonus, and deterministic ordering.
- [ ] Implement 7.5-degree default clustering, weighted normalized cluster direction, capped support bonus, and cluster-to-cluster margin.
- [ ] Verify focused and full tests.

### Task 4: G04 branch continuation projection

**Files:**
- Create: `boneweaver/core/branch_resolution.py`
- Modify: `boneweaver/contracts.py`, `boneweaver/properties.py`, `boneweaver/core/models.py`, `boneweaver/core/physics_graph.py`, `boneweaver/core/graph_projection.py`, `boneweaver/core/planner.py`, `boneweaver/core/apply_transaction.py`
- Test: `tests/test_branch_resolution.py`, `tests/test_graph_projection.py`, `tests/test_apply_transaction.py`

- [ ] Add failing fixtures for the requested bag branch plus long/short, cumulative path, weight-mass tradeoff, symmetric ambiguity, three-way, socket, naming conflict, manual selection, and child head/parent invariants.
- [ ] Implement `BranchResolutionMode`, immutable candidates/resolutions, normalized documented scoring, high/medium/ambiguous gates, explicit main-child projection, and side-root disconnect intent.
- [ ] Ensure branch nodes receive `BRANCH_CONTINUATION` proposals and side-child connect changes are represented without changing parent/head.
- [ ] Verify focused and full tests.

### Task 5: G05 per-mesh clouds and disconnected islands

**Files:**
- Create: `boneweaver/core/mesh_scan_cache.py`
- Modify: `boneweaver/core/models.py`, `boneweaver/core/weight_cloud.py`, `boneweaver/core/planner.py`
- Test: `tests/test_mesh_scan_cache.py`, `tests/test_weight_cloud.py`, `tests/test_weight_collection.py`

- [ ] Add failing topology-component and multi-mesh compatibility tests, including dominant 90%, competing islands, aligned meshes, conflicting meshes, and no midpoint direction.
- [ ] Implement compact per-mesh evidence, induced-subgraph O(V+E) components, 0.70 dominant ratio, and safe fallback/block issue routing.
- [ ] Verify focused and full tests.

### Task 6: G06 scoped idempotent overrides

**Files:**
- Create: `boneweaver/core/overrides.py`
- Modify: `boneweaver/properties.py`, `boneweaver/core/fingerprint.py`, `boneweaver/core/planner.py`
- Test: `tests/test_overrides.py`, `tests/test_plan_serialization.py`

- [ ] Add failing tests for terminal/branch upsert, duplicate removal, armature/fingerprint/chain scope, stale cleanup, and legacy unscoped warnings.
- [ ] Implement scoped keys and `upsert_terminal_override`, `upsert_branch_override`, `remove_stale_overrides`; never persist automatic fallback as manual.
- [ ] Verify focused and full tests.

### Task 7: G07 mutation and topology ledgers

**Files:**
- Create: `boneweaver/core/mutation_ledger.py`
- Modify: `boneweaver/core/models.py`, `boneweaver/core/planner.py`, `boneweaver/core/apply_transaction.py`, `boneweaver/core/validation.py`, `boneweaver/core/serialization.py`
- Test: `tests/test_mutation_ledger.py`, `tests/test_apply_transaction.py`

- [ ] Add failing tests for proposal-backed records, branch side-root connect records, unexplained target changes, non-target changes, and complete topology accounting.
- [ ] Generate frozen `BoneMutationRecord` and `TopologyProjectionLedger` in the plan and validate actual field deltas exactly against them.
- [ ] Persist ledger data in snapshots and diagnostics; reject any unrecorded mutation.
- [ ] Verify focused and full tests.

### Task 8: G08 unified scan and memory metrics

**Files:**
- Modify: `boneweaver/core/mesh_scan_cache.py`, `boneweaver/core/fingerprint.py`, `boneweaver/core/planner.py`, `boneweaver/core/runtime_store.py`
- Test: `tests/test_mesh_scan_cache.py`, `tests/test_performance_contract.py`

- [ ] Add failing assertions for designed vertex/membership pass counts, compact arrays, streaming digests, no raw point clouds in serialized plans, and `to_mesh_clear()` cleanup.
- [ ] Route analyze and each pre-apply fingerprint through one cache per operation and record all requested timing/memory/size fields.
- [ ] Run synthetic 100k-vertex performance contract and scalable fixture generators for 500k/1M reporting when machine capacity permits.

### Task 9: G09 export readiness and manifest

**Files:**
- Create: `boneweaver/core/export_contract.py`, `boneweaver/operators/export_conversion.py`, `boneweaver/schemas/export-manifest.schema.json`
- Modify: `boneweaver/contracts.py`, `boneweaver/operators/__init__.py`, `boneweaver/registration.py`, `boneweaver/core/runtime_store.py`
- Test: `tests/test_export_contract.py`, `tests/test_schema_roundtrip.py`

- [ ] Add failing tests for every readiness rejection, successful readiness, parseable manifest, mutation count, source SHA/timestamp preservation, and Pack/Save not called on failure.
- [ ] Implement `ExportReadinessReport`, `assert_export_ready`, `conversion-audit.json`, and `BONEWEAVER_EXPORT_MANIFEST` with the required audit fields.
- [ ] Keep the export entry backend-only; do not add or rearrange ordinary user panel controls.
- [ ] Verify focused and full tests.

### Task 10: G10 independent reopen validation

**Files:**
- Create: `tools/export_and_reopen.py`, `tools/reopen_validate.py`, `boneweaver/core/reopen_validation.py`
- Test: `tests/test_reopen_validation.py`

- [ ] Add failing tests for missing snapshot/manifest, geometry/ledger/branch/connect/digest/resource mismatches, and a valid saved fixture.
- [ ] Implement the fixed Analyze-to-reopen pipeline using a second Blender process and a machine-readable diagnostic result; failed reopen marks export failed and preserves diagnostics.
- [ ] Verify with a temporary fixture blend before using the real asset.

### Task 11: schemas, docs, compatibility, and reports

**Files:**
- Modify: `boneweaver/schemas/*.schema.json`, `docs/algorithms.md`, `docs/architecture.md`, `docs/safety.md`, `docs/compatibility.md`, `README.md`, `README_zh.md`, `CHANGELOG.md`
- Create: `docs/branch-resolution.md`, `docs/validation-tolerance.md`, `docs/export-contract.md`, `artifacts/backend-hardening-test-report.md`, `artifacts/backend-hardening-performance-report.md`, `artifacts/backend-hardening-real-model-report.md`, `artifacts/backend-hardening-reopen-report.md`

- [ ] Upgrade algorithm version and schema version according to actual compatibility semantics; preserve old snapshot restoration with safe defaults.
- [ ] Extend closed schemas with optional backward-compatible fields or make the documented major bump when existing semantics require it.
- [ ] Document constants, gates, diagnostics, safety invariants, migration behavior, and reproducible commands.

### Task 12: final verification and real x1.blend regression

**Files:**
- Read-only source: `C:\Users\70560\Documents\Blender项目\x1.blend`
- Output: `test-output/backend-hardening-real-model/`

- [ ] Record source SHA-256/timestamp, copy or open read-only, run the complete pipeline for 85 secondary bones, and preserve all machine-readable logs.
- [ ] Verify both named branch proposals, terminal class counts, proposal/mutation/topology accounting, per-mesh tolerances, digests, non-target count, source-file invariance, manifest, and independent reopen.
- [ ] Run the complete Blender unittest suite, schema parse tests, forbidden-API scan, package/install test, and final `git diff --check`/`git status --short`.
- [ ] Report `Implemented` only if every requested completion condition has fresh evidence; otherwise report the exact partial or blocked state.
