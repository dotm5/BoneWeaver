# BoneWeaver Repository and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atomically rename the complete Blender extension and repository identity to BoneWeaver, prepare public GitHub documentation, merge the validated G01/G02 work to `main`, and publish the verified `v0.2.0` release to `dotm5/BoneWeaver`.

**Architecture:** Treat identity as a closed cross-layer contract spanning the source directory, Python imports, Blender manifest, operator/RNA identifiers, diagnostics, schema URIs, serialized kinds, UI labels, tests, and release artifacts. Preserve the already validated conversion algorithms while applying a deterministic mechanical rename, then verify the renamed feature branch and merged `main` independently before tagging or publishing.

**Tech Stack:** Blender 5.2 Python, PowerShell 7, Git worktrees, GitHub CLI, JSON Schema, Markdown, Blender extension builder.

---

### Task 1: Freeze and commit the validated G01/G02 baseline

**Files:**
- Commit: all current G01/G02 source, tests, docs, reports, and `dist/ue_chain_prep-0.2.0.zip`
- Exclude: ignored `test-output/` runtime evidence

- [ ] **Step 1: Verify the pre-rename baseline**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py
git diff --check
```

Expected: `UECP_TEST_RESULT run=206 failures=0 errors=0 skipped=0`; `git diff --check` exits 0.

- [ ] **Step 2: Stage only the G01/G02 baseline**

Run:

```powershell
git add --all
git diff --cached --stat
```

Expected: G01/G02 source, tests, docs, reports, the implementation plan, and the 0.2.0 archive are staged.

- [ ] **Step 3: Commit the baseline**

Run:

```powershell
git commit -m "feat: complete G01 G02 hardening and chain workflows"
```

Expected: one feature commit on `feature/g01-g02-completion`.

### Task 2: Add a failing closed-world identity contract

**Files:**
- Create: `tests/test_brand_identity.py`

- [ ] **Step 1: Add the failing identity test**

Create the following Blender-hosted unittest:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path

import bpy
import boneweaver


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "boneweaver"


class BoneWeaverIdentityTests(unittest.TestCase):
    def test_public_and_runtime_identity_is_closed(self) -> None:
        self.assertEqual(boneweaver.bl_info["name"], "BoneWeaver")
        self.assertEqual(boneweaver.bl_info["version"], (0, 2, 0))
        self.assertTrue(PACKAGE.is_dir())
        self.assertFalse((ROOT / "ue_chain_prep").exists())
        manifest = (PACKAGE / "blender_manifest.toml").read_text("utf-8")
        self.assertIn('id = "boneweaver"', manifest)
        self.assertIn('name = "BoneWeaver"', manifest)
        self.assertTrue(hasattr(bpy.types.Scene, "boneweaver_settings"))
        self.assertFalse(hasattr(bpy.types.Scene, "uecp_settings"))

    def test_schema_and_rule_identity_is_boneweaver(self) -> None:
        payloads = [
            json.loads(path.read_text("utf-8"))
            for path in sorted((PACKAGE / "schemas").glob("*.json"))
        ]
        self.assertTrue(payloads)
        self.assertTrue(all("uecp" not in json.dumps(item).lower() for item in payloads))
        rules = json.loads((PACKAGE / "rules" / "default-ue-secondary.json").read_text("utf-8"))
        self.assertNotIn("uecp", json.dumps(rules).lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails before the rename**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py -- `
  --pattern test_brand_identity.py --verbose
```

Expected: import or assertion failure because `boneweaver` does not exist yet.

### Task 3: Atomically rename the extension directory and internal identity

**Files:**
- Rename: `ue_chain_prep/` → `boneweaver/`
- Rename: `docs/superpowers/plans/2026-07-11-uecp-backend-hardening.md` → `docs/superpowers/plans/2026-07-11-boneweaver-backend-hardening.md`
- Modify: all text source, tests, docs, schemas, rules, tools, and reports containing the old identity

- [ ] **Step 1: Rename tracked paths**

Run:

```powershell
git mv ue_chain_prep boneweaver
git mv docs/superpowers/plans/2026-07-11-uecp-backend-hardening.md `
  docs/superpowers/plans/2026-07-11-boneweaver-backend-hardening.md
```

Expected: Git records both directory/file renames without deleting content.

- [ ] **Step 2: Apply deterministic textual identity replacements**

Apply these ordered replacements to UTF-8 text files outside `.git`, `.worktrees`, `test-output`, and `dist`:

```text
UE Chain Prep        -> BoneWeaver
ue_chain_prep        -> boneweaver
UECP                 -> BONEWEAVER
uecp                 -> boneweaver
ue-chain-prep        -> boneweaver
UE 骨链准备           -> BoneWeaver
```

Use byte-preserving UTF-8 reads/writes and include `.py`, `.md`, `.json`, `.toml`, and `.txt` files. Do not alter the approved design/implementation plans where the old identity is intentionally documented as migration history.

- [ ] **Step 3: Update the algorithm identity explicitly**

In `boneweaver/contracts.py`, set:

```python
ADDON_VERSION = "0.2.0"
SCHEMA_VERSION = "4.0.0"
ALGORITHM_VERSION = "boneweaver-physics-graph-v4-tip-helper-branch-island-visual-cleanup"
```

- [ ] **Step 4: Update manifest and package metadata**

In `boneweaver/blender_manifest.toml`, require:

```toml
schema_version = "1.0.0"
id = "boneweaver"
version = "0.2.0"
name = "BoneWeaver"
tagline = "Prepare Unreal bone hierarchies for Blender physics chains"
maintainer = "dotm5"
type = "add-on"
blender_version_min = "4.2.0"
license = ["SPDX:GPL-3.0-or-later"]
tags = ["Rigging", "Animation"]
```

- [ ] **Step 5: Run the focused identity and registration tests**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py -- `
  --pattern test_brand_identity.py --verbose
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py -- `
  --pattern test_registration.py --verbose
```

Expected: both focused suites pass.

### Task 4: Build the public repository documentation

**Files:**
- Rewrite: `README.md`
- Rewrite: `README_zh.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/pull_request_template.md`
- Create: `docs/releases/v0.2.0.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Rewrite the English README**

Use this section order:

```markdown
# BoneWeaver
[Chinese README](README_zh.md)

Safety-first Blender tooling for turning Unreal Engine bone hierarchies into
reviewable, physics-ready chains for BoneX and Wiggle.

## Highlights
## Safety contract
## Requirements
## Installation
## Quick start
## Hierarchy inspection and semantic discovery
## Validation and recovery
## Tested release
## Known limitations
## Documentation
## Development
## License
```

Include exact release facts: Blender 4.2+, tested Blender 5.2 build
`710df102694f`, 208 Blender-hosted tests, real UE asset with 157 bones and 25,610
vertices, and independent reopen validation.

- [ ] **Step 2: Rewrite the Chinese README with equivalent facts**

Use the same section order and link back to `[English](README.md)`. Keep product
terms such as Analyze, Apply, Snapshot, Physics Graph, BoneX, and Wiggle where
they correspond to UI or contract terminology.

- [ ] **Step 3: Add repository policy files**

Add the complete GPL-3.0 license text to `LICENSE`. In `CONTRIBUTING.md`, require
the Blender-hosted full suite, `git diff --check`, extension build, and isolated
install. In `SECURITY.md`, direct private reports to the repository's GitHub
Security Advisory page and prohibit public vulnerability issues.

- [ ] **Step 4: Add GitHub templates**

The bug form must collect Blender version, BoneWeaver version, reproduction
steps, expected/actual behavior, and whether the source `.blend` can be shared.
The feature form must collect workflow, safety impact, and alternatives. The PR
template must include test evidence, safety-contract impact, schema/version
impact, and release-note impact.

- [ ] **Step 5: Add canonical v0.2.0 release notes**

`docs/releases/v0.2.0.md` must contain:

```markdown
# BoneWeaver v0.2.0 — Initial Public Preview

## Highlights
## Safety and data integrity
## Installation
## Validation evidence
## Known limitations
## Artifact
```

Leave the archive size and SHA-256 fields in a machine-updated form only until
the final archive exists; replace them before the release commit.

### Task 5: Verify the renamed feature branch and build the final archive

**Files:**
- Create: `dist/boneweaver-0.2.0.zip`
- Remove: `dist/ue_chain_prep-0.2.0.zip`
- Update: `README.md`, `README_zh.md`, `docs/releases/v0.2.0.md`, validation reports

- [ ] **Step 1: Scan for stale runtime identity**

Run:

```powershell
rg -n "ue_chain_prep|UECP|uecp|UE Chain Prep" `
  boneweaver tests tools README.md README_zh.md .github CONTRIBUTING.md SECURITY.md
```

Expected: no matches.

- [ ] **Step 2: Run the complete Blender suite**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py
```

Expected: all discovered tests pass with zero failures/errors.

- [ ] **Step 3: Run real UE asset acceptance**

Run the renamed `tools/run_g01_g02_real_acceptance.py` against
`D:\项目复现\BoneWeaver\test\SK_HuiXing_Lobby_S111.uemodel`, the isolated
UEFormat module, and a fresh BoneWeaver output directory.

Expected: `BONEWEAVER_G01_G02_REAL_RESULT PASS`, source unchanged, Apply/export
finished, independent reopen success, and one packed image reopened.

- [ ] **Step 4: Build and install the renamed archive**

Run:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --factory-startup --command extension build `
  --source-dir boneweaver --output-dir dist
$env:BLENDER_USER_RESOURCES = 'D:\项目复现\BoneWeaver\.worktrees\g01-g02-completion\test-output\isolated-install-boneweaver-v0.2.0'
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\test_install_zip.py -- `
  --zip dist\boneweaver-0.2.0.zip
```

Expected: `BONEWEAVER_ZIP_INSTALL_OK` and three clean unregister/register cycles.

- [ ] **Step 5: Inject final archive evidence**

Compute size and SHA-256 with:

```powershell
$archive = Get-Item -LiteralPath dist\boneweaver-0.2.0.zip
$hash = Get-FileHash -LiteralPath $archive.FullName -Algorithm SHA256
```

Replace archive facts in both READMEs, `docs/releases/v0.2.0.md`, and the final
test report. Verify all four sources match the computed values.

- [ ] **Step 6: Commit the rename and public-release metadata**

Run:

```powershell
git add --all
git diff --cached --check
git commit -m "chore: rename project to BoneWeaver and prepare v0.2.0"
```

Expected: a second release-facing commit after the G01/G02 feature commit.

### Task 6: Merge and verify `main`

**Files:**
- Merge in: `D:\项目复现\BoneWeaver\.worktrees\main-release-0.1.2`

- [ ] **Step 1: Configure and verify the SSH remote**

Run:

```powershell
git remote add origin git@github.com:dotm5/BoneWeaver.git
git ls-remote origin
```

Expected: exit 0; an empty repository may print no refs.

- [ ] **Step 2: Merge with an explicit release merge commit**

Run from the clean `main` worktree:

```powershell
git merge --no-ff feature/g01-g02-completion `
  -m "merge: release BoneWeaver v0.2.0"
```

Expected: merge succeeds without modifying the dirty root worktree.

- [ ] **Step 3: Rerun merged verification**

Run the complete Blender test suite, `git diff --check`, JSON parse, extension
build comparison, and isolated ZIP install from merged `main`.

Expected: all gates pass and `git status --short` is empty.

- [ ] **Step 4: Create the annotated release tag**

Run:

```powershell
git tag -a v0.2.0 -m "BoneWeaver v0.2.0 — Initial Public Preview"
git show --no-patch --decorate v0.2.0
```

Expected: `v0.2.0` points to the verified merge commit.

### Task 7: Push and publish GitHub Release

**Files:**
- Publish: branch `main`
- Publish: tag `v0.2.0`
- Attach: `dist/boneweaver-0.2.0.zip`
- Body: `docs/releases/v0.2.0.md`

- [ ] **Step 1: Push main and the feature branch**

Run:

```powershell
git push -u origin main
git push -u origin feature/g01-g02-completion
git push origin v0.2.0
```

Expected: all refs are present in `dotm5/BoneWeaver`.

- [ ] **Step 2: Configure repository metadata**

Run:

```powershell
gh repo edit dotm5/BoneWeaver `
  --description "A safety-first Blender extension for inspecting, validating, and converting Unreal Engine bone hierarchies into physics-ready chains for BoneX and Wiggle." `
  --add-topic blender `
  --add-topic blender-addon `
  --add-topic unreal-engine `
  --add-topic rigging `
  --add-topic bones `
  --add-topic animation `
  --add-topic physics `
  --add-topic bonex `
  --add-topic wiggle
```

Expected: repository About metadata matches the approved design.

- [ ] **Step 3: Create the public release**

Run:

```powershell
gh release create v0.2.0 `
  dist/boneweaver-0.2.0.zip `
  --repo dotm5/BoneWeaver `
  --title "BoneWeaver v0.2.0 — Initial Public Preview" `
  --notes-file docs/releases/v0.2.0.md
```

Expected: a published GitHub Release URL and one attached archive.

- [ ] **Step 4: Verify remote state**

Run:

```powershell
git ls-remote --heads --tags origin
gh repo view dotm5/BoneWeaver --json name,description,url,defaultBranchRef,repositoryTopics
gh release view v0.2.0 --repo dotm5/BoneWeaver --json name,tagName,url,isDraft,isPrerelease,assets
```

Expected: `main`, feature branch, `v0.2.0`, metadata, release title, and
`boneweaver-0.2.0.zip` are all present and public.

### Task 8: Clean merged worktrees without touching user work

**Files:**
- Preserve: `D:\项目复现\BoneWeaver` dirty root worktree
- Preserve: clean `main` worktree
- Remove after proof: merged G01/G02 worktree and already-merged auxiliary worktrees

- [ ] **Step 1: Prove branch ancestry**

Run:

```powershell
git merge-base --is-ancestor feature/g01-g02-completion main
git merge-base --is-ancestor feature/interaction-refactor main
git merge-base --is-ancestor fix/preview-issue-visibility main
```

Expected: all exit 0.

- [ ] **Step 2: Preserve the dirty root branch**

Record `git status --short --branch` from `D:\项目复现\BoneWeaver`; do not run
reset, clean, checkout, add, stash, or commit there.

- [ ] **Step 3: Remove only clean, merged auxiliary worktrees**

From the main worktree, remove the G01/G02, interaction-refactor, and preview-fix
worktrees only after confirming each target path is under
`D:\项目复现\BoneWeaver\.worktrees\` and each worktree reports no tracked or
untracked release work that is absent from `main`. Run `git worktree prune`
afterward and delete the merged local branches with `git branch -d`.

- [ ] **Step 4: Report final branch/worktree state**

Run:

```powershell
git branch -vv
git worktree list
git status --short --branch
```

Expected: `main` is tagged and tracks `origin/main`; the dirty root semantic
branch remains untouched; no obsolete clean auxiliary worktrees remain.
