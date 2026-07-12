# G01 / G02 Completion Audit

Date: 2026-07-12
Branch: `feature/g01-g02-completion`
Base: `3c41c709cdae80c370dd0c9c176fb5526b478fcf`
Release candidate: `0.2.0`, Schema `4.0.0`

## Final gates

| Gate | Evidence | Result |
| --- | --- | --- |
| Blender-hosted regression suite | 206 tests, 0 failures, 0 errors, 0 skipped | PASS |
| Real UEFormat asset | `SK_HuiXing_Lobby_S111.uemodel`, 157 bones, 25,610 vertices | PASS |
| Analyze / Apply | `hair_l_01..04`, 4 proposals and 4 mutation records | PASS |
| Export / independent reopen | conversion copy, packed image, topology/digest checks | PASS |
| Source preservation | source `.blend` signature unchanged | PASS |
| Interactive Blender validation | Computer Use, real Blender 5.2 window, finger/spine/semantic flows | PASS |
| Package build/install | `ue_chain_prep-0.2.0.zip`, isolated install and three register cycles | PASS |
| Final code review | No Critical or Important findings; branch declared merge-ready | PASS |

## G01 result

All task-book work packages are implemented and covered: production/strict
tolerances, Tip Helper classification and opt-in terminal use, safe leaf
fallback, direction clustering, secondary-only branch gates, per-mesh weight
island policies, Armature-scoped overrides, mutation/topology ledgers, guarded
Apply/Restore, conversion-copy export, and independent reopen validation.

The real asset completed Analyze, Apply, export, and reopen with maximum mesh
delta `1.38388392485728e-07`, RMS delta `9.6581166636274e-09`, no digest changes,
one packed image retained, and the original source file unchanged.
The acceptance ledger records 4 target bones, 4 mutation targets, 1 safe
ordinary-leaf fallback, 0 manual terminal overrides, 0 branch resolutions,
4 proposals, 4 mutation records, and 0 non-target changes.

## G02 result

All five hierarchy modes, deterministic hierarchy index, explicit branch
continuation, immutable local overlay cache, frozen Analyze scopes, layered
semantic rules, explicit semantic confirmation, and opt-in visual cleanup are
implemented and tested.

Semantic weight-cloud reuse additionally requires complete Armature coverage;
a local Analyze scope cannot be reused by full-Armature Discovery, while a
complete cache remains reusable until a source/weight digest changes.

Interactive acceptance confirmed:

- `Bip001-L-Finger0 -> Finger01 -> Finger02` is one selectable chain;
- `Bip001-L-Hand` is yellow, the active root is orange-red, descendants are cyan;
- selection count changes from 1 to 3 after **Select Scope**;
- `Bip001-Spine` stops at its first branch and presents `Bip001-Spine1` and
  `NekoBotHit` for explicit continuation;
- choosing `Bip001-Spine1`, freezing the scope, and running Analyze records the
  continuation as `MANUAL` in the conversion plan;
- semantic discovery returns 22 candidates, starts with 0 confirmed, and only
  changes to 1 after an explicit confirmation click;
- no main-skeleton chain is classified AUTO/SUGGEST.

Required detailed evidence is in `artifacts/backend-hardening-test-report.md`,
`artifacts/real-asset-regression.md`, `artifacts/reopen-validation.md`, and
`artifacts/manual-selection-smoke.md`.
