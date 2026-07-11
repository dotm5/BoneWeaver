# UE Chain Prep Test Report

Date: 2026-07-11

## Automated results

| Layer | Command | Result |
|---|---|---|
| Python syntax | `python -m compileall -q ue_chain_prep tests tools` | Pass |
| L0/L1/L2 | Blender 5.2 RC `--background --factory-startup --python tests/run_blender_tests.py` | 61 run, 0 failures, 0 errors, 0 skipped |
| BoneX original UI draw repro | Factory-startup real window, audited BoneX 1.2.6 getter in Header draw | Expected failure reproduced with the user's exact AttributeError class/message |
| BoneX patched UI draw repro | Same real-window probe against isolated and installed copies | Pass; getter returned empty data without writing an ID property |
| BoneX read/write separation | Background Armature: getter, setter, getter | Pass; read path remained pure and operator/setter path persisted one connection |
| Extension build | Blender `--factory-startup --command extension build --source-dir ue_chain_prep --output-dir dist` | Pass |
| Isolated ZIP install | `tests/test_install_zip.py` in fresh `BLENDER_USER_RESOURCES` | Pass; install plus three register/unregister cycles |
| UEFormat isolated import | `tools/probe_ueformat.py` on `SK_HuiXing_Lobby_S111.uemodel` | Pass; 1 Armature / 157 bones / 1 Mesh |
| Real default-safety smoke | Four-section earring chain, default `position_epsilon_factor=1e-7` | Correct rollback: max neutral delta `2.409949e-7` exceeded allowed `2.081384e-7` |
| Real scale-aware smoke | Same chain, explicit factor `1.2e-7` | Analyze, Apply, internal validation, Validate and Restore pass |

## Covered behavior

- Contract enums, operators, error codes, Manifest and schemas.
- Three-cycle registration/unregistration and Preview handler cleanup.
- Scope, Context guard, Mesh/Modifier resolution, strict animation/constraint/pose/preflight blockers.
- Immutable head/hierarchy graph, branch and coincident handling, canonical Graph/Plan IDs.
- One-pass memberships, area/exclusivity weights, dependency-free eigen solver, cloud classes.
- Six-axis, manual, direct-child, weight and tangent evidence; stable tie handling.
- Virtual Tip non-persistence, graph projection, Profiles, Minimal Twist, Parallel Transport, Radial and Swing math.
- Stale Plan rejection, persistent snapshot, atomic Apply, forced-failure rollback, Restore conflict protection.
- Weight/Base Mesh/Modifier digests, graph projection, evaluated neutral mesh, report export and Plan JSON round-trip.
- BoneX 1.2.6 exact-source transformation, version guard, idempotent backup/restore workflow, CLI output and true Blender draw-context regression.

## Final package

- File: `dist/ue_chain_prep-0.1.0.zip`
- Bytes: 47,874
- SHA-256: `6A9BD38F4F6DE2DE98D1B21C863B7A3BAF72AAB91FB50FAC142680DD22B8E336`

No test was deleted, skipped, or weakened to obtain the result.
