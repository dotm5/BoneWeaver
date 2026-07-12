# Semantic Chain Discovery v0.2.0

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
tails, weights, constraints, drivers, create helper objects, or change selection.
The later selection operator owns any explicit selection-only bridge.

## Architecture

- `semantic_names.py` performs deterministic normalization, side/sequence parsing,
  tokenization, and semantic-stem extraction. A lone `l` or `r` embedded in a word
  is never interpreted as a side marker.
- `semantic_rule_loader.py` validates and merges versioned JSON rule sets in the
  order default, importer, game, user. Later layers override token and category
  decisions without hiding the active rule-set IDs and versions.
- `semantic_models.py` owns frozen, slotted discovery models and stable enums.
- `semantic_discovery.py` builds a read-only armature snapshot, consumes the
  caller-supplied weight summaries when available, scores each bone, groups
  hierarchy-continuous candidates, determines roots, and returns a deterministic
  `SemanticDiscoveryPlan` with no Blender RNA references.
- `semantic_serialization.py` performs strict closed-field JSON roundtrips and
  rejects missing or unknown plan, chain, and evidence fields.
- `controllers/semantic_discovery.py`, the semantic operators, and the panel own
  explicit discovery, confirmation, frozen-scope, export, and lifecycle bridges.
  Discovery itself remains read-only; only the named Select operator changes
  Blender selection.

The public core entry point is:

```python
build_semantic_discovery_plan(
    bone_states,
    armature_object_name="Rig",
    armature_fingerprint="...",
    merged_rules=rules,
    weight_summaries=optional_weight_clouds,
    metadata_by_bone=optional_adapter_metadata,
)
```

If the caller omits an Armature fingerprint, the core derives one canonically
from the immutable BoneState tuple. It never reads Blender RNA itself.
`semantic_discovery_plan_to_json()` emits sorted-key JSON;
`semantic_discovery_plan_from_json()` rebuilds the frozen model and rejects
unknown fields or unsupported kind/schema/algorithm constants.

## Evidence and precedence

Each bone receives normalized component scores in `[0, 1]` for semantics,
hierarchy, sequence, weights, geometry mismatch, and metadata, plus an exclusion
penalty and a separately serialized `discovery_score`. The v0.2.0 weighted score is:

```text
0.30 semantic + 0.25 hierarchy + 0.15 sequence + 0.15 weight
+ 0.10 geometry mismatch + 0.05 metadata - exclusion penalty
```

Absent optional weight summaries are explicit unavailable evidence: they never
count as positive support, emit `UECP_SEMANTIC_WEIGHT_EVIDENCE_UNAVAILABLE`, and
prevent automatic acceptance. The candidate may still be emitted for user
review. Absent optional importer metadata remains neutral rather than positive
evidence. Hard exclusions have
precedence over positive tokens. Main skeleton, socket,
IK/control, twist/roll/corrective, and facial categories are `EXCLUDE` even when
the bone has deform weights. `CHEST_SECONDARY` is capped at `SUGGEST_INCLUDE`.
Generic tokens such as `part`, `bone`, `joint`, and `extra` cannot independently
produce `AUTO_INCLUDE`.

`AUTO_INCLUDE` requires score at least `0.80`, a valid hierarchy chain, and no
hard exclusion. Scores from `0.55` are suggestions. Strong contradictory evidence
is ambiguous. The algorithm and thresholds are versioned so deterministic changes
are reviewable.

The emitted v0.2 taxonomy is `HAIR`, `RIBBON`, `SKIRT`, `CLOAK`, `CAPE`,
`TAIL`, `EARRING`, `STRAP`, `BELT`, `SCARF`, `TASSEL`, `ACCESSORY`, `BAG`,
`CHEST_SECONDARY`, `UNKNOWN_SECONDARY`, `MAIN_SKELETON`, `SOCKET`,
`IK_CONTROL`, `TWIST_DEFORM`, and `FACIAL`. Legacy enum identifiers
`BAG_OR_STRAP`, `CLOTH`, and `PHYSICS_EXPLICIT` remain parseable for layered
rule compatibility but the packaged v0.2 default does not emit them.

## Chain grouping

Candidate bones group only across real parent-child edges whose normalized stem,
side, and category are compatible. Sequence gaps remain in the same explicit
hierarchy component but add a stable review reason. Ordering is canonical by
bone name and root identity. Every `discovery_id` hashes the algorithm version,
Armature fingerprint, active rule-set IDs, root, complete bone set, category,
and discovery class.

Branches retain every compatible child in the discovered component. Discovery
never chooses a main continuation; a branched AUTO candidate is capped at
`SUGGEST_INCLUDE` with `UECP_SEMANTIC_BRANCH_REVIEW_REQUIRED`.

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

Schema `2.0.0` requires per-bone `discovery_class` and `discovery_score`. The
closed schema enumerates categories/classes/geometry states and forbids unknown
fields at the plan, chain, and evidence levels.

## Integration boundary

The Blender adapter reads every Armature `BoneState` without changing selection.
At runtime it loads rule files in strict default, Source Adapter, game, user
precedence from the three Advanced settings paths; later layers override earlier
decisions and any unreadable or invalid configured layer fails discovery
explicitly.
It reuses `WeightCloudStats` only from the current in-memory Analyze plan after
settings, Armature identity, and captured bone-state checks succeed. It never
rescans meshes merely to run discovery; without a reusable plan the classifier
uses hierarchy, names, and importer metadata, but records weight evidence as
unavailable and will not classify such a candidate as `AUTO_INCLUDE`.

The immutable `SemanticDiscoveryPlan`, its source-file/Armature fingerprint, and
confirmed discovery IDs live only in the module runtime store. Load, undo, reset,
unregister, and successful Apply clear that state. Every select, freeze, export,
Analyze, and Apply bridge revalidates file, Armature identity, full semantic
BoneState fingerprint, and discovery-plan identity.

`Discover Secondary Chains` is read-only. `Confirm and Select Discovered Chain`
is the only selection-changing bridge and selects the complete candidate, never a
guessed main branch. `Use Confirmed Discovered Chains` freezes confirmed bone-name
tuples for the next Analyze but does not run Analyze. AUTO candidates require the
same explicit confirmation as suggestions. Hierarchy and semantic frozen scopes
are mutually exclusive; `UECP_SCOPE_SOURCE_CONFLICT` rejects simultaneous use.
Strict JSON export serializes the immutable plan.

The panel displays category, discovery class, score, branch count, and reason
codes. A current semantic plan also supplies `semantic_categories` to hierarchy
inspection. Socket, IK/Control, and Twist helpers render as `EXCLUDED_HELPER` and
are removed from hierarchy selection/frozen scope. Main-skeleton and facial bones
remain explicitly selectable for user-directed hierarchy inspection, while still
remaining excluded from automatic semantic inclusion. Semantic categories never
reclassify a bone as a G01 Tip Helper: that identity comes only from a validated
ConversionPlan or later explicit evidence.

## Safety and acceptance

Acceptance must cover names, hierarchy, weights, geometry, rule precedence, and
determinism with programmatic fixtures. The real `x1.blend` acceptance uses a copied file or direct
background read-only load, captures selected/head/tail/parent/weight fingerprints
before and after discovery, and reports baseline roots, discovered roots, TP/FP/FN,
ambiguous counts, class totals, and forbidden-category false positives. Precision
is prioritized over recall: target AUTO_INCLUDE precision is at least 95%, baseline
recall at least 85%, and main-skeleton/socket/IK/twist false positives are zero.
