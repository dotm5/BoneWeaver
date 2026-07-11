# Branch Resolution Contract

The Physics Graph keeps every direct child. Blender projection selects at most one main child because a Bone has one tail. Side children keep their name, parent, and head and are forced disconnected.

`AUTO_MAIN_PATH` scores cumulative downstream path, subtree deform mass, incoming-direction continuity, branch depth, and weak naming continuity. Socket, IK/control, invalid, unweighted-when-alternatives-are-weighted, and tiny decorative branches receive explicit penalties. High and Medium selections are frozen in the Plan; ambiguous evidence blocks.

`LONGEST_PATH_ONLY`, `DIRECTION_CONTINUITY`, `MANUAL_ONLY`, and `KEEP_ORIGINAL` are stable backend modes. Manual selection must be scoped to Armature Data and structural fingerprint. Apply disconnects target direct children before moving the branch tail, then reconnects only the selected main child according to Profile.
