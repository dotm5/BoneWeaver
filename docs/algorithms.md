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
