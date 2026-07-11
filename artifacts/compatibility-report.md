# Compatibility Report

| Version / target | Registration | Unit | Integration | ZIP install / smoke |
|---|---:|---:|---:|---:|
| Blender 5.2.0 LTS RC `710df102694f` | Pass | Pass | Pass | Pass |
| Blender 5.1 | Not available locally | Pending | Pending | Pending |
| Blender 4.2 | Manifest minimum | Pending | Pending | Pending |
| UEFormat 1.0.0 | Pass | N/A | Real import pass | Isolated package-copy pass |
| BoneX 1.2.6 | Installed | N/A | Manual Pending | Manual Pending |
| Wiggle 2 RTX 2.2.5 | Installed | N/A | Manual Pending | Manual Pending |
| Auto-Rig Pro 3.78.22 | Installed | N/A | Manual Pending | Manual Pending |

Blender 4.2 and 5.1 executables were not present under the checked Program Files and Steam roots. No result is inferred for unavailable versions. Feature detection covers Blender 5.2 `PoseBone.select`, legacy/layered Action access, and restricted extension-install registration context.

The installed third-party add-ons are not imported or mutated by UECP. Their actual simulation/rig behavior requires the interactive checklist in `docs/manual-test-bonex-wiggle.md` and remains external manual validation.
