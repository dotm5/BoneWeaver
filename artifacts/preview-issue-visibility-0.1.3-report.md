# BoneWeaver 0.1.3 Preview/Issue Visibility Release Report

Date: 2026-07-12 (Asia/Shanghai)

## Release identity

- Add-on version: `0.1.3`
- Schema version: `3.1.0`
- Algorithm version: `boneweaver-physics-graph-v3-interaction-hardening`
- Blender: 5.2.0 LTS Release Candidate, hash `710df102694f`
- Release scope: use the actual GPU viewport dimensions for preview-line `viewportSize`, and make issue rows/location actions identify the affected bone.

## TDD version-contract evidence

The production version was still `0.1.2` when the assertions were first changed to `0.1.3`.

- RED — `test_contracts.py`: 5 run, 1 expected failure, exit 1. `ADDON_VERSION` was `0.1.2`, expected `0.1.3`.
- RED — `test_schema_roundtrip.py`: 3 run, 1 expected failure, exit 1. Manifest version was `0.1.2`, expected `0.1.3`.
- GREEN — `test_contracts.py`: 5 run, 0 failures, 0 errors, 0 skipped, exit 0.
- GREEN — `test_schema_roundtrip.py`: 3 run, 0 failures, 0 errors, 0 skipped, exit 0.

Focused command shape:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python tests/run_blender_tests.py -- --pattern test_contracts.py --verbose
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python tests/run_blender_tests.py -- --pattern test_schema_roundtrip.py --verbose
```

## Full Blender suite

Command:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python tests/run_blender_tests.py
```

Result: `BONEWEAVER_TEST_RESULT run=170 failures=0 errors=0 skipped=0`, exit 0.

## Real model read-only verification

Command:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup 'C:\Users\70560\Documents\Blender项目\x1.blend' --python tools/run_backend_hardening_real.py
```

Result: `BONEWEAVER_REAL_BACKEND_RESULT PASS`, exit 0.

- Target bones: 85
- Proposals: 85
- Blockers: 0
- Apply: `FINISHED`
- Conversion export: `FINISHED`
- Independent reopen validation: success
- Exported add-on version: `0.1.3`
- Source size before/after: 18,394,498 bytes
- Source modification time before/after: `2026-07-11T12:59:45.0238745Z`
- Source SHA-256 before/after: `998b92001e76a169e6e17d55f08e1cd606eda8034d7eb95f7acc57fc66464da1`
- Source unchanged: true

## Package verification

Build command:

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --factory-startup --command extension build --source-dir boneweaver --output-dir dist
```

- Archive: `dist/boneweaver-0.1.3.zip`
- Size: 98,848 bytes
- SHA-256: `9f7ce99b44baa5a0ebe715d5f84b0eb15b62ddb4df2944de6ff258cb515b9d04`
- Build exit: 0
- Fresh isolated `BLENDER_USER_RESOURCES` install: `BONEWEAVER_ZIP_INSTALL_OK`, exit 0
- Three register/unregister cycles after installation: passed with no leaked `Scene.boneweaver_settings` RNA property.

The immutable 0.1.2 archive remains present and unchanged:

- Archive: `dist/boneweaver-0.1.2.zip`
- Size before/after: 97,807 bytes
- SHA-256 before/after: `968fe9885e11d6c5e47ccf89e48d916d513df733cff6e365e82d501bf7b326aa`

## Pending visual validation

Interactive Computer Use validation is intentionally **PENDING**. The root task will install and visually validate the packaged 0.1.3 extension after this CLI/release handoff. No interactive Computer Use was performed in this task.
