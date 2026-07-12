# BoneWeaver Final Review

## Outcome

Implemented With External Manual Validation Pending.

## Acceptance review

| # | Contract | Result |
|---:|---|---|
| 1–5 | Head/hierarchy Source Graph, immutable Physics Graph, one real node per bone, root kinematic | Pass |
| 6–8 | Interior projection, leaf Virtual Tip, no persistent virtual scene identity | Pass |
| 9–12 | Imported six axes, deterministic AUTO scoring, tie and low-confidence blockers | Pass |
| 13–16 | Branch preservation/no averaging, Minimal Twist default, opt-in transport, edge-direction agreement | Pass |
| 17–21 | Original bones only; no proxy, new constraints/drivers/empties, modifier rebuild, parenting ops, or pose-as-rest | Pass |
| 22–30 | Names/parents/heads/groups/weights/base mesh/modifiers/neutral mesh/Profile connect invariants | Pass in automated and real smoke |
| 31–33 | Diagnostic-only long sampling, deterministic Plan/Graph/Candidates, stale settings/algorithm detection | Pass |
| 34–37 | Automatic rollback, Snapshot Restore, conflict refusal, registration/handler cleanup | Pass |
| 38 | Headless tests | Pass: 61/61 |
| 39 | Installable ZIP | Pass in fresh isolated repository |
| 40 | Documentation | Pass |
| 41 | BoneX/Wiggle/ARP interactive smoke | BoneX UI draw hotfix Pass; physics/Bake plus Wiggle/ARP Manual Pending; no result fabricated |
| 42 | Unknown/unverified facts are explicit | Pass |

## Real validation metrics

- Weight digest changes: 0.
- Base Mesh digest changes: 0.
- Modifier digest changes: 0.
- Graph projection maximum error: 0.
- Non-target bone changes: 0.
- Maximum neutral evaluated mesh delta: `2.40994900310574e-7`.
- Scene scale: `2.08138446173036`.
- Explicit smoke epsilon factor: `1.2e-7`; allowed max `2.49766126495134e-7`.
- Default factor `1e-7` correctly rejected and rolled back the same real asset.

## Remaining external/administrative items

- Run and record interactive BoneX 1.2.6, Wiggle 2 RTX 2.2.5 and ARP 3.78.22 behavior.
- Run the compatibility matrix on actual Blender 4.2 and 5.1 executables.
- Replace placeholder maintainer and confirm the GPL-3.0-or-later manifest decision before public distribution.

These items do not have fabricated pass states.
