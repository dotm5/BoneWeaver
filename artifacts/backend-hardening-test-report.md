# UE Chain Prep 0.2.0 Backend Hardening Test Report

Date: 2026-07-12
Branch: `feature/g01-g02-completion`
Blender: 5.2.0 LTS Release Candidate, build `710df102694f`

## Automated suite

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests\run_blender_tests.py
```

Result: **206 run, 0 failures, 0 errors, 0 skipped**.

Coverage includes Schema 4 contracts, production/strict/custom tolerance,
Tip Helpers, terminal fallback, direction clustering, branch resolution,
secondary-only main-skeleton gate, cross-mesh weight islands, CSR scan cache,
scoped overrides, mutation/topology ledgers, Edit Mode flush/stale checks,
Apply/Restore, export gates, independent reopen, hierarchy modes, overlay cache,
semantic rules/discovery/confirmation, lifecycle invalidation, and visual cleanup.
The semantic cache tests also cover partial-Analyze rejection, complete-cache
reuse, and digest-driven invalidation after weight edits.

## Real asset and package

- Real acceptance: PASS; see `real-asset-regression.md`.
- Independent reopen: PASS; see `reopen-validation.md`.
- Interactive Computer Use smoke: PASS; see `manual-selection-smoke.md`.
- Package: `dist/ue_chain_prep-0.2.0.zip`.
- Size: 157,446 bytes.
- SHA-256: `EB237324480BBD43B8C38AA2EAA4120E477EF2E699ACC13A6631FD2E932D53E7`.
- Isolated install: PASS (`UECP_ZIP_INSTALL_OK`).
- Three unregister/register cycles: PASS.

No automatic commit, push, merge, or modification of the user's installed
0.1.2 extension was performed.
