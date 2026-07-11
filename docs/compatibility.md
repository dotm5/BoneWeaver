# Compatibility

| Target | Status |
|---|---|
| Blender 5.2.0 LTS RC `710df102694f` | Automated registration, unit, integration, transaction, restore, real-asset and ZIP smoke target |
| Blender 4.2 | Manifest minimum; executable unavailable locally, external validation pending |
| Blender 5.1 | Executable unavailable locally, external validation pending |
| UEFormat 1.0.0 | Factory-startup isolated-copy import verified |
| BoneX 1.2.6 | Installed locally; manual physics behavior must be recorded separately |
| Wiggle 2 RTX 2.2.5 | Installed locally; manual physics behavior must be recorded separately |
| Auto-Rig Pro 3.78.22 | Installed locally; post-conversion rig workflow remains manual |

Compatibility code uses feature detection for Action APIs and Blender 5.2's `PoseBone.select` migration rather than relying only on version comparisons.
