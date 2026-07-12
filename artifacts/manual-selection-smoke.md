# Manual Selection and Viewport Smoke

Date: 2026-07-12
Method: Computer Use against a real Blender 5.2.0 LTS RC process opened on the
disposable acceptance copy. The installed 0.1.2 extension was disabled only in
that process, source version 0.2.0 was registered for the disposable session,
and Blender preferences were not saved. The user's installed extension and two
open Blender projects were not changed.

## Finger chain

1. Activated `Bip001-L-Finger0` in Pose Mode.
2. Opened **UE Chain Prep > Hierarchy Chain Inspection**.
3. Clicked **Inspect Scope** with `Linear Chain`.
4. The panel reported parent `Bip001-L-Hand`, 2 descendants, and 0 branches.
5. The viewport showed only the local context: parent in yellow, active root in
   orange-red, and `Finger01`/`Finger02` in cyan, with readable names drawn over
   the mesh.
6. Clicked **Select Scope**; the actual Blender selection count changed from 1
   to 3 and all three finger bones were selected.

Result: **PASS**. This specifically regresses the earlier unreadable full-rig
line explosion and the Pose Mode selection-cache failure found during this run.

## Spine branch

1. Activated `Bip001-Spine` and clicked **Inspect Scope**.
2. Linear inspection stopped at the first branch.
3. The panel reported 1 branch and exposed explicit continuation buttons for
   `Bip001-Spine1` and `NekoBotHit`.
4. Clicked `Bip001-Spine1`, then **Use for Conversion** and **Analyze**.
5. The resulting conversion plan contained
   `Bip001-Spine -> Bip001-Spine1`, result `MANUAL`; the next unresolved branch
   at `Bip001-Spine2` remained blocked instead of being guessed.

Result: **PASS**.

## Semantic discovery

1. Clicked **Discover Secondary Chains (read-only)**.
2. The panel reported 22 candidates and 0 confirmed chains.
3. The UI warned that even AUTO candidates require an explicit click.
4. Clicked **Confirm and Select This Chain** on one candidate; confirmed count
   changed to 1 and only that chain became selected.

Result: **PASS**. Discovery did not start Analyze or Apply automatically.

## Visual cleanup boundary

`VISUAL_CHAIN_CLEANUP` remains an explicit profile and was not activated during
inspection/discovery. Its mutation boundary is covered by the Blender-hosted
visual-cleanup regression tests.
