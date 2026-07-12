# BoneX / Wiggle / ARP Manual Test

Record Blender/add-on versions, model hash, chain names, profile, Plan ID, Graph ID, Snapshot ID, and tester/date.

## Common geometry

- [ ] First bone is Anchor/Kinematic.
- [ ] Interior parent tail equals child head.
- [ ] Y axis follows the chain and X/Z do not flip unexpectedly.
- [ ] Virtual Tip did not create a real bone, group, object, or constraint.
- [ ] Weight/Base Mesh/Modifier digests and neutral mesh validation pass.

## BoneX Rotation Chain

- [ ] Create physics for a 4–6 section converted chain.
- [ ] Joint and rigid-body centers/orientation match the mesh region.
- [ ] First section remains stable during translation, rotation, and vertical motion.
- [ ] No dependency cycle; bake succeeds.

Result / evidence: ____________________

## Wiggle 2

- [ ] Rotation profile uses connected interior bones and does not stretch.
- [ ] Stretch profile remains geometrically continuous with `use_connect=False`.
- [ ] No proxy constraint bridge is present.

Result / evidence: ____________________

## ARP

- [ ] BONEWEAVER conversion occurred before ARP generation/matching.
- [ ] Main controls work and secondary chains are not constrained twice.
- [ ] BoneX/Wiggle acts only on intended deform chains; no dependency cycle.

Result / evidence: ____________________
