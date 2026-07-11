# Algorithms

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

High requires score/margin `0.65/0.15`; Medium requires `0.55/0.08`. Lower or symmetric evidence blocks. Names cannot override contradictory geometry.

## Weight islands and scanning

Weight evidence is first separated by Mesh, then split into connected components on the induced base-mesh subgraph. A component is accepted only when its statistical-weight ratio is at least `0.70`. Cross-mesh clouds combine only when directions are compatible; otherwise a single 70% dominant Mesh may win, or the evidence falls back safely.

`MeshScanCache` performs one full vertex and one membership pass per Mesh for an Analyze operation. It streams digests and stores temporary indices/coordinates/weights in standard-library `array` buffers. No NumPy is used.

Imported-axis evidence receives the normal prior only when importer metadata (`orig_loc`, `orig_quat`, or `post_quat`) is present. Without metadata the prior is reduced and contradictory geometry/weight evidence adds a penalty. Neutral validation baselines use flat `array('d')` buffers and streaming delta statistics.
