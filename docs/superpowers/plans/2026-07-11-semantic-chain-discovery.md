# Semantic Chain Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, read-only semantic preprocessing stage that discovers likely UE secondary-physics chains and produces selectable candidate scopes without applying geometry changes.

**Architecture:** Pure name/rule/model modules feed a read-only discovery engine over immutable bone snapshots and the existing `MeshScanCache`. Blender operators are thin shells around discovery, selection-only scope application, and JSON report export; Physics Graph, Branch Resolver, and Terminal Solver remain geometry authorities.

**Tech Stack:** Blender 4.2+/5.2 Python, standard library JSON/dataclasses/enums, `bpy`, `mathutils`, JSON Schema, `unittest` through the existing background Blender runner.

---

### Task 1: Name semantics

**Files:**
- Create: `ue_chain_prep/core/semantic_names.py`
- Create: `tests/test_semantic_names.py`

- [ ] Write failing tests for namespace stripping, delimiter/case normalization,
  safe side parsing, numeric and alpha-branch sequences, and stable stems.
- [ ] Run `blender.exe --background --factory-startup --python tests/run_blender_tests.py -- --pattern test_semantic_names.py --verbose` and confirm imports/functions fail for the expected missing-feature reason.
- [ ] Implement `normalize_bone_name`, `tokenize_bone_name`, `extract_side_marker`,
  `extract_sequence_index`, and `extract_semantic_stem` with parsed token roles.
- [ ] Re-run the focused test and retain deterministic expected values such as
  `Character:Hair_F_L_01 -> stem hair_f, side LEFT, sequence 1`.

### Task 2: Versioned rules and immutable models

**Files:**
- Create: `ue_chain_prep/core/semantic_models.py`
- Create: `ue_chain_prep/core/semantic_rule_loader.py`
- Create: `ue_chain_prep/rules/default-ue-secondary.json`
- Create: `ue_chain_prep/schemas/semantic-rule-set.schema.json`
- Create: `ue_chain_prep/schemas/semantic-discovery-plan.schema.json`
- Create: `tests/test_semantic_rules.py`

- [ ] Write failing tests for required fields, stable enums, built-in loading,
  default/importer/game/user precedence, token removal/override, and invalid input.
- [ ] Run the focused test and confirm the missing loader/model failure.
- [ ] Implement frozen rule models, JSON validation without external dependencies,
  deterministic merge semantics, packaged default loading, and stable enums.
- [ ] Add schemas with `additionalProperties: false` for discovery output and rule
  records, then re-run focused rule and schema tests.

### Task 3: Geometry mismatch classification

**Files:**
- Create: `tests/test_semantic_geometry_mismatch.py`
- Modify: `ue_chain_prep/core/semantic_discovery.py` (created in this task)

- [ ] Write failing pure tests for continuous, fixed-short, reversed, short-aligned,
  slight-error, leaf, and branch geometry plus uniform display-length detection.
- [ ] Run the focused test and confirm missing functions fail.
- [ ] Implement vector-safe angle/distance/ratio evidence and
  `detect_uniform_imported_display_length()` without editing Blender data.
- [ ] Re-run focused tests and preserve explicit `GeometryProjectionNeed` results.

### Task 4: Discovery scoring and chain grouping

**Files:**
- Create: `tests/test_semantic_discovery.py`
- Modify: `ue_chain_prep/core/semantic_discovery.py`
- Modify: `tests/fixture_builders.py` only for new reusable Blender fixtures.

- [ ] Write failing fixtures/tests for the required include/exclude names, isolated
  positives, continuous and missing-number chains, branches, mirrored chains,
  multi-mesh weights, noise weights, metadata, generic tokens, and determinism.
- [ ] Run the focused suite and confirm discovery API failures.
- [ ] Implement evidence scoring, hard-exclusion precedence, category caps,
  candidate-root grouping, reason codes, canonical chain ordering, and IDs.
- [ ] Consume a supplied `MeshScanCache`; never initiate a second mesh scan when a
  compatible cache is passed.
- [ ] Re-run focused discovery tests, then run all semantic tests together.

### Task 5: Scope bridge and operators

**Files:**
- Create: `ue_chain_prep/operators/discover_secondary_chains.py`
- Create: `ue_chain_prep/operators/select_discovered_chains.py`
- Create: `ue_chain_prep/operators/export_discovery_report.py`
- Modify: `ue_chain_prep/core/runtime_store.py`
- Modify: `ue_chain_prep/operators/__init__.py`
- Modify: `ue_chain_prep/contracts.py`
- Modify: `tests/test_registration.py`
- Create: `tests/test_semantic_operators.py`

- [ ] Write failing tests proving discover is selection-neutral, select changes only
  selection for requested classes, ambiguous is not selected by default, export is
  deterministic, and all classes register/unregister.
- [ ] Run operator/registration tests and confirm missing classes/IDs fail.
- [ ] Implement `discover_secondary_chains`, `build_scope_from_discovery`, and
  `apply_discovery_to_selection`, then thin operators and runtime plan storage.
- [ ] Re-run operator/registration tests and verify armature geometry fingerprints
  remain byte-for-byte equivalent around discovery and selection.

### Task 6: Real asset harness and documentation

**Files:**
- Create: `tools/run_semantic_discovery_real.py`
- Create: `artifacts/semantic-discovery-x1-report.md`
- Modify: `README.md`
- Modify: `README_zh.md`

- [ ] Add a read-only harness that opens `x1.blend`, inventories armatures, captures
  pre/post fingerprints, discovers candidates, and writes metrics and chain tables.
- [ ] Run it with `E:\SteamLibrary\steamapps\common\Blender\blender.exe` against
  `C:\Users\70560\Documents\Blender项目\x1.blend` without saving the blend file.
- [ ] Compare discovered roots against selected/manual roots encoded in the sample
  or an explicit checked-in baseline derived from its existing selection state.
- [ ] Tune only evidence weights/rules justified by fixtures and report remaining
  false negatives as suggestions/ambiguous rather than weakening exclusions.

### Task 7: Full verification and boundary audit

**Files:**
- Modify: `artifacts/semantic-discovery-x1-report.md`

- [ ] Run all Blender unit tests fresh and record run/failure/error/skip counts.
- [ ] Validate both JSON schemas and packaged default JSON through tests.
- [ ] Re-run the real sample harness and confirm before/after geometry, hierarchy,
  vertex-group, and weight fingerprints match.
- [ ] Inspect `git diff --name-status` and separate pre-existing dirty baseline files
  from this branch's semantic-discovery files; do not stage or commit unrelated work.
- [ ] Check every completion condition and record any unmet metric honestly.
