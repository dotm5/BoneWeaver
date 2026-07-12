# Branch Resolution Contract

The Physics Graph keeps every direct child. Blender projection selects at most one main child because a Bone has one tail. Side children keep their name, parent, and head and are forced disconnected.

`AUTO_MAIN_PATH` scores cumulative downstream path, subtree deform mass, incoming-direction continuity, branch depth, and weak naming continuity. Automatic modes run only after an explicit secondary-physics eligibility gate. Main-skeleton, IK/control, Socket, Twist, facial/non-deform, or otherwise semantically uncertain branches receive no automatic main child. Stable blocker codes distinguish each excluded role; geometric symmetry still produces `BONEWEAVER_BRANCH_AMBIGUOUS`.

The eligibility blocker codes are `BONEWEAVER_BRANCH_AUTO_MAIN_SKELETON_FORBIDDEN`, `BONEWEAVER_BRANCH_AUTO_CONTROL_FORBIDDEN`, `BONEWEAVER_BRANCH_AUTO_SOCKET_FORBIDDEN`, `BONEWEAVER_BRANCH_AUTO_TWIST_FORBIDDEN`, and `BONEWEAVER_BRANCH_AUTO_SECONDARY_SEMANTICS_REQUIRED`.

`LONGEST_PATH_ONLY`, `DIRECTION_CONTINUITY`, `MANUAL_ONLY`, and `KEEP_ORIGINAL` are stable backend modes. The secondary-physics gate also applies to the two automatic single-evidence modes. Manual selection must be scoped to Armature Data and structural fingerprint. Apply disconnects target direct children before moving the branch tail, then reconnects only the selected main child according to Profile.
