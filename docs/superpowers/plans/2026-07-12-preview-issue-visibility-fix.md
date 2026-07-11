# Preview and Issue Visibility Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Blender 5.2 preview overlay readable and make every issue row identify its affected bone in user-facing Chinese text.

**Architecture:** Preserve the existing frozen preview cache and controller ownership. Correct only the GPU viewport uniform at draw time, and isolate issue-label formatting in a pure presenter consumed by the UI list and details panel.

**Tech Stack:** Blender 5.2 Python, `bpy`, `gpu`, Blender-hosted `unittest`, Computer Use visual validation.

---

### Task 1: Correct polyline viewport dimensions

**Files:**
- Modify: `tests/test_preview.py`
- Modify: `ue_chain_prep/ui/draw.py`

- [ ] **Step 1: Write the failing viewport-uniform test**

Add a test that injects a fake `gpu` module whose state returns `(0, 0, 1920, 1080)`, injects a fake cached shader and batch, calls `_draw_callback()`, and asserts that the shader received `viewportSize == (1920.0, 1080.0)`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python tests\run_blender_tests.py -- --pattern test_preview.py --verbose
```

Expected: the new test fails because the current callback sends `(1.0, 1.0)`.

- [ ] **Step 3: Implement the minimal draw fix**

In `_draw_callback`, import `gpu`, read `viewport = gpu.state.viewport_get()`, derive `(float(max(1, viewport[2])), float(max(1, viewport[3])))`, and use that tuple for the shader uniform. Keep `_ensure_gpu_cache()` outside the line loop.

- [ ] **Step 4: Verify GREEN**

Run the same focused command and expect all `test_preview.py` tests to pass.

### Task 2: Present affected bones and friendly issue reasons

**Files:**
- Create: `ue_chain_prep/ui/issue_presenter.py`
- Modify: `ue_chain_prep/ui/lists.py`
- Modify: `ue_chain_prep/ui/panels/details.py`
- Modify: `tests/test_ui_refactor.py`

- [ ] **Step 1: Write failing issue-presentation tests**

Exercise `UECP_UL_issues.draw_item` with an item containing bone `hair_ribbon_l_06`, code/message `UECP_TERMINAL_CANDIDATE_AMBIGUOUS`, and assert the visible label is `hair_ribbon_l_06 · 末端方向存在歧义`. Also assert the details panel source supplies `text=f"定位：{view.selected_issue_bone}"` to the locate operator.

- [ ] **Step 2: Verify RED**

Run the Blender test runner with `--pattern test_ui_refactor.py --verbose` and expect the new display assertions to fail.

- [ ] **Step 3: Implement the pure presenter and consume it**

Create `issue_summary(code, message, bone_name)` with short Chinese mappings for terminal-candidate ambiguity, branch ambiguity, forward-axis ambiguity, low terminal score, and safe fallback. Preserve useful non-code messages. Prefix a non-empty bone name. Call it from the UI list, and add the selected bone to the locate-button text.

- [ ] **Step 4: Verify GREEN**

Re-run `test_ui_refactor.py` and expect all tests to pass.

### Task 3: Release 0.1.3 and verify end to end

**Files:**
- Modify: `tests/test_contracts.py`
- Modify: `tests/test_schema_roundtrip.py`
- Modify: `ue_chain_prep/contracts.py`
- Modify: `ue_chain_prep/blender_manifest.toml`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README_zh.md`
- Create: `artifacts/preview-issue-visibility-0.1.3-report.md`
- Create: `dist/ue_chain_prep-0.1.3.zip`

- [ ] **Step 1: Update version tests first and verify RED**

Change the two version assertions to `0.1.3`, run their focused Blender tests, and confirm they fail against production version `0.1.2`.

- [ ] **Step 2: Update release metadata and verify GREEN**

Change the contract and manifest to `0.1.3`, add the changelog entry, update installation paths in both READMEs, and re-run the focused tests.

- [ ] **Step 3: Run automated and real-model verification**

Run the full Blender unittest suite, the 85-bone `tools/run_backend_hardening_real.py` pipeline on the read-only `x1.blend`, build the extension ZIP, and install it through `tests/test_install_zip.py` in an isolated user directory.

- [ ] **Step 4: Run interactive visual verification**

Use Computer Use to operate interactive Blender with the built 0.1.3 extension: open `x1.blend`, execute the user-facing check-and-preview flow, load issue details, select an ambiguous issue, use the bone-specific locate action, and save before/after interaction screenshots under `test-output/visual-validation-0.1.3/`.

- [ ] **Step 5: Record evidence and commit**

Record test counts, source-file preservation, package size/hash, visual observations, and screenshot paths in the report. Commit only scoped source, tests, docs, report, and 0.1.3 archive changes.
