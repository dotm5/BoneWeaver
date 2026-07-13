# Algorithms

## One-click UE-style reorientation

Quick Reorient captures every EditBone into immutable local-coordinate state.
Importer original-transform metadata selects the same dominant local axis used
by UEFormat; otherwise the generic adapter derives stable joint directions from
the existing hierarchy. Eligible non-leaf bones point toward the normalized
average of eligible child Heads. Leaves use the transformed dominant axis and
retain their original length. Existing UEFormat-reoriented sources avoid
double-transforming their basis. Roll is updated through Blender `align_roll`
using a stable reference, minimizing twist.

Socket, control/IK/pole/helper, zero-length, and already-normalized bones are
conservatively skipped. The numeric A/B harness disables native connection
reconstruction to compare this direction stage independently against fixed
UEFormat commit `8da96d65f669ca688dbf7c0141f800605a6c16e6`.

The second stage decomposes the eligible hierarchy into deterministic maximal
linear components. Every internal single-child parent ends at the unchanged
child Head and the child receives `use_connect = True`. Component roots and all
children of a branch boundary stay disconnected. This is the minimum native
topology required for Blender Edit Mode `L` selection without changing parent
relationships or adding bones.

## Coordinates and evidence

Mesh points are transformed once with `armature.matrix_world.inverted_safe() @ mesh.matrix_world`. Each vertex and group membership is scanned once. Statistical weight is `q = area * max(weight-minimum,0)^gamma * exclusivity`; it is never written back.

The head-centered covariance `sum(q * (p-H)(p-H)^T) / sum(q)` is solved by a deterministic dependency-free Jacobi 3×3 eigensolver. Eigenvalue ratios classify LINEAR, PLANAR, ISOTROPIC, or INSUFFICIENT clouds.

## Graph and terminal

Every real bone maps to a node at its head. Selected parent→child heads define hierarchy edges. A resolved leaf receives a graph-only Virtual Tip. Candidates include imported Rest Matrix `±X/±Y/±Z`, principal axis, centroid, planar blend, parent tangent, and original display axis. Direction-specific evidence, continuity, shape suitability, imported-axis prior, and length plausibility produce a versioned score. Selection requires score, distinct-direction margin, and confidence thresholds.

Length uses positive projected weighted percentile when reliable, otherwise chain evidence. It never defaults to weighted mean Euclidean distance.

## Projection and roll

Each unique edge becomes one proposal: hierarchy edge child position or Virtual Tip position becomes the parent bone tail. Minimal Twist projects old local Z onto the plane normal to new local Y and uses stable fallbacks. Parallel Transport blends transported parent Z and projected old Z only when explicitly selected. Radial mode projects the outward reference vector for skirt chains.

Long-segment hints compare edge length with chain median and generate preview-only virtual samples; no deform bone is inserted.

## Production neutral tolerance

The default `AUTO_PRODUCTION` comparison uses evaluated mesh object-local coordinates independently for each Mesh. Two no-op dependency-graph evaluations estimate runtime noise. The soft limit is the maximum of the absolute floor, local mesh scale times `2.5e-7`, baseline maximum times `4`, and eight float32 ULPs at the mesh coordinate magnitude. The hard limit is four times the soft limit. World-space delta remains diagnostic only.

A result passes directly below the soft limit. A bounded sparse outlier passes with a numeric-noise warning only when maximum, RMS, and outlier-count gates all pass. Every failure reports a recommended absolute limit and relative factor; Apply never silently retries with a looser value. `STRICT_TEST` preserves the `1e-7` fixture gate, while `CUSTOM` uses the explicit relative factor.

## Terminal fallback and candidate clusters

Candidate directions merge within 7.5 degrees before Margin calculation. A cluster direction is the score-weighted normalized sum. Cluster score is the strongest member plus a support bonus of `0.04` per additional distinct evidence kind, capped at `0.12`.

When normal terminal selection is unresolved but the parent chain is safe, the leaf direction is `normalize(leaf.head-parent.head)` and length is the median of the nearest one to three valid upstream segments. It is classified `AUTO_SAFE_FALLBACK`, remains confirmation-worthy, and is never stored as a manual override.

## Branch continuation

For each direct child, the resolver calculates the maximum cumulative head-to-head path to a descendant leaf, depth, subtree deform-weight mass, weighted-vertex count, incoming direction continuity, weak naming continuity, and explicit penalties. Default score is:

```text
0.50 path + 0.20 weight + 0.15 direction + 0.10 depth + 0.05 naming - penalties
```

High requires score/margin `0.65/0.15`; Medium requires `0.55/0.08`. Lower or symmetric evidence blocks. Before either result can select a child, automatic modes require positive secondary-physics semantics and reject main-skeleton, control/IK, Socket, Twist, facial, and non-deform evidence. Names cannot override contradictory geometry, and uncertain semantics require a scoped manual override.

## Weight islands and scanning

Weight evidence is first separated by Mesh, then split into connected components on the induced base-mesh subgraph. `WeightIslandPolicy` is a fingerprinted stable setting: `DOMINANT_COMPONENT` is the safe default and accepts only a component carrying at least `0.70` of the Mesh weight; `REQUIRE_SINGLE_COMPONENT` rejects every multi-island Mesh; `ALL_COMPATIBLE_COMPONENTS` merges islands only when their directions are mutually compatible. Cross-mesh clouds combine only when directions are compatible; otherwise a single 70% dominant Mesh may win, or the evidence falls back safely. Multiple significant islands are never merged implicitly.

The one-operation Mesh scan builds a compact shared CSR adjacency index once per
Mesh. Per-bone island resolution traverses only the weighted induced subgraph;
it never rescans the complete edge list for every target Bone. The reported
temporary-memory estimate includes all concurrent weight builders and the CSR
construction workspace, while Analyze also records the process-level
`tracemalloc_peak`.

`MeshScanCache` performs one full vertex and one membership pass per Mesh for an Analyze operation. It streams digests and stores temporary indices/coordinates/weights in standard-library `array` buffers. Component discovery reuses the per-Bone index map rather than repeatedly materializing compact vertex and edge iterators. No NumPy is used.

Imported-axis evidence receives the normal prior only when importer metadata (`orig_loc`, `orig_quat`, or `post_quat`) is present. Without metadata the prior is reduced and contradictory geometry/weight evidence adds a penalty. Neutral validation baselines use flat `array('d')` buffers and streaming delta statistics.
