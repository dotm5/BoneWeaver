# Compatibility

| Target | Status |
|---|---|
| Blender 5.2.0 LTS RC `710df102694f` | Automated registration, unit, integration, transaction, restore, real-asset and ZIP smoke target |
| Blender 4.2 | Manifest minimum; executable unavailable locally, external validation pending |
| Blender 5.1 | Executable unavailable locally, external validation pending |
| UEFormat 1.0.0 | Factory-startup isolated-copy import verified |
| BoneX 1.2.6 | Blender 5.2 draw-context fault reproduced and reversible local hotfix verified; physics behavior remains manual |
| Wiggle 2 RTX 2.2.5 | Installed locally; manual physics behavior must be recorded separately |
| Auto-Rig Pro 3.78.22 | Installed locally; post-conversion rig workflow remains manual |

Compatibility code uses feature detection for Action APIs and Blender 5.2's `PoseBone.select` migration rather than relying only on version comparisons.

UECP runtime does not mutate BoneX state. The separately invoked support tool and rollback procedure are documented in [BoneX 1.2.6 draw-context hotfix](bonex-1.2.6-draw-context-hotfix.md).

Schema 3.1 adds optional branch, tolerance, mutation, topology, and export records. Schema 3.0 readers may ignore these additions. Old snapshots remain restorable because restore continues to require only the original pre-state and digest fields; new readers use safe defaults when hardening fields are absent. Interaction hardening and metadata-aware Imported Axis behavior are versioned as `uecp-physics-graph-v3-interaction-hardening`, so settings or version changes stale older Plans.
