# UE Chain Prep Backend Hardening Test Report

## Environment

- Blender 5.2.0 LTS RC, build `710df102694f`
- PowerShell 7.6.2
- Branch `feature/ue-chain-prep-v0.1.0`
- Automatic commit/push: none

## Automated Tests

Command:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --background --factory-startup `
  --python tests/run_blender_tests.py -- --verbose
```

Result: 121 run, 0 failures, 0 errors, 0 skipped.

Coverage includes production/strict/custom tolerance, object-local/world diagnostics, no-op/ULP/outliers, terminal fallback, candidate clustering, branch resolution/projection/apply, multi-Mesh direction compatibility, disconnected islands, override scope/upsert/migration, mutation/topology ledgers, compact scan cache, 100k/500k/1M scale contracts, export gate/manifest/source preservation, and independent reopen validation.

## Real Asset

Command:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  --factory-startup --background `
  'C:\Users\70560\Documents\Blender项目\x1.blend' `
  --python tools/run_backend_hardening_real.py
```

Result: PASS for 85 targets, 85 Proposals, 85 Mutation Records, zero blockers, zero non-target/digest changes, AUTO_PRODUCTION PASS, source unchanged, and independent reopen PASS.

## Package

- Build: `blender --factory-startup --command extension build --source-dir ue_chain_prep --output-dir dist` — PASS
- Archive: `dist/ue_chain_prep-0.1.0.zip`, 72,398 bytes
- Isolated install/register-unregister cycles: PASS (`UECP_ZIP_INSTALL_OK`)

## Safety Scans

- Runtime forbidden API scan: no matches
- Runtime NumPy scan: no matches
- `git diff --check`: PASS
- Original `x1.blend` SHA-256 after all runs: `998B92001E76A169E6E17D55F08E1CD606EDA8034D7EB95F7ACC57FC66464DA1`
