# Automatic skeleton preparation (0.6.0)

The main panel exposes four one-click actions and recovery. Debug, legacy
UEFormat/hybrid workflows and manual controls stay under **Advanced**.

| Mode | Changes |
|---|---|
| AUTO | Orient interior bones, connect aligned linear links, remove verified zero helper subtrees |
| REORIENT | Parent/child orientation only; no deletion or connectivity changes |
| CONNECT | Connect already aligned linear links only; never move bone heads/tails |
| CLEANUP | Remove verified zero helper subtrees only; keep surviving rest axes/connectivity |

## Selection and order

1. Freeze the original hierarchy and weight/reference evidence across every associated
   or parented mesh, including hidden LODs. Any positive weight protects a bone;
   envelopes count as potential deformation. No mesh evidence means no cleanup.
2. Preserve roots, IK, sockets, weapon/attachment nodes, controls and virtual bones.
   Protect semantic subtrees too. Names include UE IK chains, WeaponProp, CameraPosition,
   terminal Case markers and NekoBotHit. This classification is conservative evidence,
   not a universal dictionary of every game's gameplay nodes.
3. Preserve all ancestors needed by weighted/protected/referenced bones. References
   include Actions, drivers, constraints, bone parenting, Hook modifiers, custom-shape
   transforms and B-Bone handles. A zero-weight structural parent is not redundant.
4. Inspect candidates bottom-up. Only whole zero-weight helper subtrees with a weighted
   ancestor and no surviving child qualify. Evidence includes explicit helper metadata,
   end/tip/nub, sequential chain extensions, SR/ST and secondary/physics-chain markers.
   Unknown UE metadata leaves require a sole-child weighted parent. Unknown or ambiguous
   zero nodes remain. Coincident helpers and multiple auxiliary children are supported.
5. Orient original interior bones using eligible child heads. Prefer surviving children
   over removable corrective side branches. Root/leaf rest axes stay unchanged. Single
   noncoincident children give exact directions; genuine branches use the current-frame
   dominant signed axis and mean offset length. Cancelled directions remain unchanged.
   Preserve connected-child boundaries. Protected semantic children never steer axes.
6. Connect only geometrically aligned, unambiguous surviving linear links in AUTO/CONNECT.
   Apply the frozen deletion set deepest-first, verifying no unplanned child remains.
   Keep every weighted terminal, even if a prior automatic skinning pass assigned it weight.

All decisions are recorded in the snapshot. Zero weight alone never proves a bone is
useless. Only loaded assets/references are observable; external modular meshes, future
animations and proprietary gameplay metadata require their original skeleton copy.
Use original imported weights before automatic skinning; this does not repair bad weights.

## Preservation and recovery

The transaction edits a single-user copy and keeps the entire original Armature
datablock with a fake user. It records deletion/reorientation mutations, original
pose properties, custom shapes and metadata in a versioned Text snapshot. The
snapshot and backup survive saving and reopening. The recovery button resolves
the active armature rather than a global last-used rig.

Weights, vertex groups, mesh topology and Armature modifiers are unchanged.
Static pose channels are rebased to preserve `pose_matrix @ inverse(rest_matrix)`.
An unchanged-rest matrix round trip measures numerical baseline noise before
the real edit; per-mesh local-coordinate checks use the existing production
tolerance policy. Validation failure restores the original datablock and pose.
Recovery refuses later changes to bone data/settings, weights, pose, references,
or backup data. A repeated operation is a no-op and keeps its recovery point.

This new mode is intended **before animation and control-rig authoring**. Active
Actions, relevant inactive Actions and unsupported NLA/drivers/constraints are
not silently rewritten. Existing legacy animation-basis modes remain available
under Advanced. Their pose-matrix preservation is not a blanket guarantee of
identical skin deformation or interpolation; the new mode does not claim that.

## UEFormat upstream audit

Checked 2026-11-01 against upstream
[`h4lfheart/UEFormat` commit d858fe38b2b5b8c63ac4b7481b4386ebfabbf935](https://github.com/h4lfheart/UEFormat/tree/d858fe38b2b5b8c63ac4b7481b4386ebfabbf935).
Installed `importer/reorient_utils.py`, `utils.py`, skeleton/animation creation
and manifest match that commit ignoring line endings. The local source checkout
is at `8d803c19358a190dc769901a908bbe833af020bc`; its reorientation also matches.
The manifest reports **0.10.0**, while `bl_info` reports **1.0.0**; these are not
evidence of two different installed algorithms.

Upstream rotates local +Y to the dominant signed axis of the average child
`orig_loc`, using the mean child-offset magnitude (minimum 0.01) as length.
Roots with children participate. Leaves inherit the parent's direction through
the conjugated local quaternion. Zero offset resolves to +Z; allowed-child
filtering still divides by total child count. It does not identify unweighted
directional helpers. Animation import uses `orig_loc`, `orig_quat`, `post_quat`;
tracks whose bone was removed are skipped. BoneWeaver preserves surviving
metadata and updates cumulative basis corrections, but does not modify UEFormat.

The new mode deliberately differs: excludes roots/leaves from orientation,
uses current local coordinates, retains zero-sum branches, computes lengths
from participating children and explicitly selects deletion candidates.

## Verification

Run the full factory-startup Blender suite and `tests/test_install_zip.py`.
`tools/run_auto_cleanup_acceptance.py` verifies source hashes, real-mesh
deformation, idempotence and exact restoration, and saves a converted copy for
an independent `--restore` process. Original source assets are never saved over.


## Cross-game numerical evidence (0.6.0)

The CUE4Parse corpus has two characters per configured game installation (eight
characters across Wuthering Waves, Strinova and two Lovecraft versions). Raw
imports include sockets in addition to the reference skeleton.

On legacy Alet, R_Back_Thigh_STSocket retained identical head/tail coordinates.
The imported matrix had a 5.835e-5 orthogonality defect; after a parent basis
change Blender normalized it to 3.076e-7, with a maximum component change of
2.915e-5. An unchanged edit-mode round trip did not trigger this normalization.
Acceptance therefore checks protected EditBone head/tail/roll and connectivity,
and records derived matrix differences diagnostically instead of claiming
bit-identical imported matrices. On legacy Anya, M_EyesSocket retained exactly
the same head, tail and roll while its derived matrix differed by 1.130e-5.
Exact backup restoration and evaluated mesh checks remain separate requirements.
