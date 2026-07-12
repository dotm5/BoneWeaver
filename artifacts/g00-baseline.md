# G00 Baseline and Environment

Date: 2026-07-11 (Asia/Shanghai)

## Repository

- Repository initialized locally at `D:\项目复现\BoneWeaver`.
- Baseline branch: `main`.
- Development branch: `feature/boneweaver-v0.1.0`.
- Baseline commit: `4808465 chore: establish project baseline`.
- No remote is configured or required.
- Real `.uemodel` fixtures and generated `.blend`/runtime output are ignored.

## Toolchain

- PowerShell: 7.6.2.
- Blender executable: `E:\SteamLibrary\steamapps\common\Blender\blender.exe`.
- Blender: 5.2.0 LTS Release Candidate, build hash `710df102694f`, build date 2026-07-11.
- No separate Blender 4.2 or 5.1 executable was found under the standard Program Files or current Steam installation roots.
- Python dependencies for production code are restricted to Blender Python, `bpy`, `mathutils`, and the standard library.

## UEFormat Isolation Proof

- Installed extension: `io_scene_ueformat` 1.0.0, minimum Blender 4.2.0.
- Installed module: `bl_ext.user_default.io_scene_ueformat`.
- Import operator: `bpy.ops.uf.import_uemodel`.
- The operator consumes `directory` plus `files`; passing only `filepath` returns `FINISHED` without importing because its file loop is empty.
- A copy of the extension was loaded from the ignored project path `test-output/ueformat-isolated/user_default/io_scene_ueformat` under `--factory-startup`.
- The isolated copy registered successfully and imported `SK_HuiXing_Lobby_S111.uemodel` without loading the user's other enabled add-ons.
- Probe result: 1 Armature, 157 bones, 1 root; 1 Mesh, 25,610 vertices, 35,790 polygons, 122 vertex groups, 1 Armature modifier.
- Generated snapshot: `artifacts/runtime/SK_HuiXing_Lobby_S111.isolated.snapshot.json` (ignored).
- Snapshot SHA-256: `3BCB1DA459AB9829CA3763454DCF625578098B82617F2BFC6E285436208510AC`.

## Available Third-party Manual-test Targets

- BoneX 1.2.6 is installed in the Blender 5.2 extension repository.
- Wiggle 2: RTX Edition 2.2.5 is installed.
- Auto-Rig Pro 3.78.22 is installed.
- Their presence does not count as validation. G09 must record real manual/smoke evidence or mark the corresponding row Pending.

## Fixed References

- Product contract: `plan.md`, version 3.0.0.
- Kawaii Physics fixed reference: <https://github.com/pafuhana1213/KawaiiPhysics/tree/e29e078f49526ce721125468657043ecf5c9ae1f>.
- Blender EditBone API: <https://docs.blender.org/api/current/bpy.types.EditBone.html>.
- Blender SpaceView3D draw handler API: <https://docs.blender.org/api/current/bpy.types.SpaceView3D.html>.
- Blender extension getting started: <https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html>.

Kawaii Physics is architectural reference material only. No C++ runtime solver, collision code, XPBD/Verlet loop, or third-party API is copied into BoneWeaver.

## Local Fixture Inventory

| File | Bytes | SHA-256 |
|---|---:|---|
| `NHT1FuluoluoLifu.uemodel` | 9,041,375 | `63A432C35A78A69EAC010476D100A0B37640ED833141BD6BCDDB9DA9F6C7EC0D` |
| `NHT1Xiaoxiakong.uemodel` | 3,012,141 | `4AABB840D191C0B8F2F6C18B4A8FF5AFCA2E058CB3D3B57CE849F0A4622106AF` |
| `R2T1AnkeMd10011.uemodel` | 4,288,899 | `DDCFC4C23645DB8B455F71F3797D6D9F766A8B37CDABABA2C25F5414C1032FDD` |
| `R2T1FeiBiMd10011.uemodel` | 6,294,151 | `A9E41C89D0FF4F1E6EA7A4A41B9E9658D5BE2B17D3B7E7704636DA8F66AEC219` |
| `R2T1JinxiMd10011.uemodel` | 5,818,094 | `43EAFC5B772FAF343C961197F004B89252A3BB9774BDD0BCA785F7AD4E0E891F` |
| `R2T1MicaiMd10011.uemodel` | 4,411,134 | `02D8004EEC2CD774ECADA1504549B9EFE9D2D5CD29D9962DB9AEEF5CF5C541DE` |
| `SK_Aika_Lobby_S109.uemodel` | 3,971,106 | `01705D0AE95750096EEE8134970967453B108B45853DAB9952B90D3F77DEE89B` |
| `SK_HuiXing_Lobby_S111.uemodel` | 2,771,405 | `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940` |
| `SK_Kanami_Lobby_S103.uemodel` | 3,894,367 | `BF6C1804D88C6E7DF5D9F94E2B71D8662E17CA123B3D2A0FBDC88FA08335D7E6` |
| `SK_Yvette_Lobby_S114.uemodel` | 3,245,200 | `73228753FEA57EBA04E474EB40DF18377C4E3C41FCB8ED6B815C9AF51F20DAE1` |

## Initial Risks and Controls

| Risk | Control |
|---|---|
| Only Blender 5.2 RC is locally executable | Validate 5.2 completely; report 4.2/5.1 as unavailable unless executables become available. |
| Blender can print a Python traceback yet exit with code 0 | Project runners must catch failures and force a non-zero process exit; callers also validate expected result artifacts. |
| UEFormat's operator ignores `filepath` in its execute path | Always pass `directory` and `files`; retain the real-asset probe as regression evidence. |
| Real game assets may not be redistributable | Keep all `.uemodel` files ignored and commit only hashes/statistics. |
| Imported rigs may contain branches, coincident helpers, animation, constraints, drivers, or unsupported modifiers | Strict Preflight blocks rather than guesses or rewrites relationships. |
| Rest geometry changes may alter evaluated neutral mesh | Capture pre/post evaluated world-space vertices and roll back on threshold failure. |
| Candidate evidence may be ambiguous | Stable scoring, minimum score/margin/confidence, and explicit blockers prevent silent selection. |
| BoneX/Wiggle/ARP may create dependency graph side effects | BONEWEAVER never imports their APIs; preflight blocks existing generated dependencies and G09 uses explicit smoke records. |
| Project manifest license has no prior repository decision | Use the contract's GPL-3.0-or-later placeholder and flag maintainer/license confirmation in the final report. |

## G00 Gate Result

The local Git baseline, executable Blender environment, isolated UEFormat load, and one real imported skeleton snapshot are reproducible. Implementation may proceed on the feature branch.
