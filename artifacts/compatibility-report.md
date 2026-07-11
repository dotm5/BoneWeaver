# Compatibility Report

| Version / target | Registration | Unit | Integration | ZIP install / smoke |
|---|---:|---:|---:|---:|
| Blender 5.2.0 LTS RC `710df102694f` | Pass | Pass | Pass | Pass |
| Blender 5.1 | Not available locally | Pending | Pending | Pending |
| Blender 4.2 | Manifest minimum | Pending | Pending | Pending |
| UEFormat 1.0.0 | Pass | N/A | Real import pass | Isolated package-copy pass |
| BoneX 1.2.6 | Installed; local hotfix guarded | 3 support-tool tests pass | Real UI draw pass | Physics/Bake Manual Pending |
| Wiggle 2 RTX 2.2.5 | Installed | N/A | Manual Pending | Manual Pending |
| Auto-Rig Pro 3.78.22 | Installed | N/A | Manual Pending | Manual Pending |

Blender 4.2 and 5.1 executables were not present under the checked Program Files and Steam roots. No result is inferred for unavailable versions. Feature detection covers Blender 5.2 `PoseBone.select`, legacy/layered Action access, and restricted extension-install registration context.

UECP runtime does not import or mutate the installed third-party add-ons. BoneX 1.2.6 had an independent Blender 5.2 UI-context fault: its getter initialized ID properties from panel `draw()`. The separately invoked reversible support tool changed that getter to read-only after an exact version/source check. Both isolated-copy and installed-copy real-window probes passed after patching. Actual simulation/rig behavior still requires `docs/manual-test-bonex-wiggle.md` and remains external manual validation.
