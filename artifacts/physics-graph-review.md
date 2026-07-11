# Physics Graph Reference Review

Reference: Kawaii Physics commit `e29e078f49526ce721125468657043ecf5c9ae1f`.

| Architecture question | UECP result |
|---|---|
| Are real nodes joint origins? | Yes; every `REAL_BONE.joint_position` is the frozen Bone head. |
| Do hierarchy edges depend on imported tails? | No; tests mutate every tail without changing edge vectors or Graph ID. |
| Is the root kinematic? | Yes; every maximal linear chain root is marked kinematic/Anchor. |
| How is a leaf represented? | An accepted solution creates a graph-only `VIRTUAL_TIP` and `VIRTUAL_TIP_SEGMENT`. |
| Are forward axes configurable? | Yes; imported Rest Matrix `±X/±Y/±Z`, with explicit axis filtering and validation. |
| Are branches averaged? | No; graph edges remain, branch parent gets no unique Blender proposal, child chains restart. |
| Is twist arbitrary? | No; default Minimal Twist projects old Z, with explicit Parallel Transport/Radial modes. |
| Are inter-bone dummies persisted? | No; long-segment hints and preview points do not create deform bones. |

No Kawaii Physics C++ solver, collision, XPBD/Verlet hot path, Unreal API, or binary dependency is included. The reference informs data ordering and Swing/Virtual Tip architecture only.

## Real graph evidence

Asset SHA-256: `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940`.

- Chain: `earring_l_01` through `earring_l_04`.
- Plan ID: `f3ed1504187826b72f19e26b5a7f750b5bdf0e56879d933842e2e025aa43d3c1`.
- Graph ID: `e196d4dc3f071e906c875248566a1085e6a5ff709a47d2d90cfcbf837534a518`.
- Real nodes: 4; Virtual tips: 1; hierarchy edges: 3.
- Unique unselected direct child supplied the authoritative tip.
- Object/Bone counts were unchanged after Analyze and after Apply→Restore.
- Default rollback evidence SHA-256: `D99A1B7AF499EF4259F9C7CC6F6732D5BF061227038156385B30319B812DDF04`.
- Successful Apply/Validate/Restore evidence SHA-256: `1C7C233665B5805D35A32821239874DAB52E43FAF53861B2319199B3935CBCE8`.
