# Semantic Chain Discovery v0.1.1

## Product boundary

Semantic Chain Discovery is a read-only preprocessing stage between an imported
Armature and the existing Physics Graph analyzer. It narrows the user's scope;
it does not decide final geometry and never applies edits.

```text
Imported Armature
    -> Semantic Chain Discovery
    -> Candidate roots and candidate bone sets
    -> Physics Graph Analyze
    -> ConversionPlan
    -> explicit Apply transaction
```

The stage may emit candidate chains, roots, categories, projection need,
confidence, and reason codes. It must not rename or reparent bones, change heads,
tails, weights, constraints, drivers, or create helper objects. Selection changes
are isolated in `apply_discovery_to_selection()` and the selection operator.

## Architecture

- `semantic_names.py` performs deterministic normalization, side/sequence parsing,
  tokenization, and semantic-stem extraction. A lone `l` or `r` embedded in a word
  is never interpreted as a side marker.
- `semantic_rule_loader.py` validates and merges versioned JSON rule sets in the
  order default, importer, game, user. Later layers override token and category
  decisions without hiding the active rule-set IDs and versions.
- `semantic_models.py` owns frozen, slotted discovery models and stable enums.
- `semantic_discovery.py` builds a read-only armature snapshot, consumes the
  existing `MeshScanCache` when weight evidence is requested, scores each bone,
  groups hierarchy-continuous candidates, determines roots, and returns a
  deterministic `SemanticDiscoveryPlan` with no Blender RNA references.
- Three operators discover, select, and export. Discovery does not alter
  selection; selection only changes `Bone.select`; export serializes the stored
  immutable plan.

## Evidence and precedence

Each bone receives normalized scores in `[0, 1]` for semantics, hierarchy,
sequence, weights, geometry mismatch, and metadata, plus an exclusion penalty.
The v0.1.1 weighted score is:

```text
0.30 semantic + 0.25 hierarchy + 0.15 sequence + 0.15 weight
+ 0.10 geometry mismatch + 0.05 metadata - exclusion penalty
```

Hard exclusions have precedence over positive tokens. Main skeleton, socket,
IK/control, twist/roll/corrective, and facial categories are `EXCLUDE` even when
the bone has deform weights. `CHEST_SECONDARY` is capped at `SUGGEST_INCLUDE`.
Generic tokens such as `part`, `bone`, `joint`, and `extra` cannot independently
produce `AUTO_INCLUDE`.

`AUTO_INCLUDE` requires score at least `0.80`, a valid hierarchy chain, and no
hard exclusion. Scores from `0.55` are suggestions. Strong contradictory evidence
is ambiguous. The algorithm and thresholds are versioned so deterministic changes
are reviewable.

## Geometry projection need

For a bone with one effective child, discovery compares tail-to-child distance,
display direction to hierarchy direction, current length to parent-child distance,
and an armature-level uniform imported-display-length signal. Exact continuity is
`NOT_REQUIRED`; strong direction/length mismatch is `REQUIRED`; small deviations
are `RECOMMENDED`. Leaves remain candidates but defer tips to Terminal Solver.
Branches are marked and defer continuation to Branch Continuation Resolver.

Uniform imported display length is detected only when enough non-root bones form a
tight short-length cluster while their hierarchy-edge distances vary materially.
No tail is written during detection.

## Determinism and identity

Canonical sorted input includes armature fingerprint, algorithm version, rule-set
IDs and versions, relevant settings, manual include/exclude overrides, and selected
discovery classes. Chain IDs and ordering are derived from canonical values, never
from Blender collection iteration order. Reports contain no full vertex data.

## Safety and acceptance

Programmatic fixtures cover names, hierarchy, weights, geometry, rule precedence,
and determinism. The real `x1.blend` acceptance uses a copied file or direct
background read-only load, captures selected/head/tail/parent/weight fingerprints
before and after discovery, and reports baseline roots, discovered roots, TP/FP/FN,
ambiguous counts, class totals, and forbidden-category false positives. Precision
is prioritized over recall: target AUTO_INCLUDE precision is at least 95%, baseline
recall at least 85%, and main-skeleton/socket/IK/twist false positives are zero.
