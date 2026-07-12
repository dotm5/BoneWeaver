# Hierarchy Select & Inspect

Hierarchy Select & Inspect is a non-destructive way to identify UE bone chains
from parent/child relationships. It does not depend on Blender's Connected
selection propagation and does not write permanent Bone Colors.

## Workflow

1. Make one Armature bone active.
2. Choose a hierarchy selection mode and click **Inspect Scope**.
3. Review the colored viewport overlay. Inspect does not change selection.
4. Optionally click **Select Scope** to make the frozen names the Blender bone
   selection. The inspection root remains active and its parent context is not
   selected by default.
5. At an ambiguous branch, choose a branch bone and one of its direct children,
   then confirm the main continuation.
6. Click **Use for Conversion** to freeze the inspected bone-name set for the
   next Analyze operation.

Analyze rejects the frozen scope after a file-path change, Armature object/data
change, or structural-fingerprint change. Changing ordinary Blender selection
after freezing does not change that Analyze scope.

## Overlay roles

| Role | Default color |
| --- | --- |
| Parent context | Yellow |
| Active inspection root | Orange-red |
| Selected descendant | Cyan |
| Main continuation | Blue-green |
| Branch node | Purple |
| Side branch root | Gray dashed |
| Existing Tip Helper | Brown-orange |
| Excluded helper | Dark red |

All eight role colors can be adjusted in the add-on preferences without
writing Blender Bone Color data.

The overlay cache contains only frozen names, world-space head/tail geometry,
labels, colors, and widths. GPU callbacks draw this cache and never traverse
the Armature. Load, Undo, Redo, session reset, explicit Clear Inspection, and
add-on unregister all remove both handlers and discard the cache.
Armature object/data dependency-graph changes also invalidate the frozen cache
outside the draw callback and require a fresh inspection.

Existing Tip Helpers from a currently valid ConversionPlan remain visible in the
inspected scope. A reference-only Helper can be frozen for Analyze only when its
deform parent is also visibly included in the inspected set; otherwise Use is
rejected instead of silently expanding the scope. Semantic discovery supplies
category labels and Socket/IK/Control/Twist exclusions before Analyze, but it does
not guess Tip Helper identity from names alone.
