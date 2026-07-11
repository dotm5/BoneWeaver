# Architecture

UE Chain Prep separates stable source truth, immutable reasoning, and Blender mutation:

```text
Armature Bone Head + Parent Hierarchy + Rest Axes + Weight Evidence
  -> immutable PhysicsNode / PhysicsEdge / PhysicsChain
  -> terminal candidates and optional Virtual Tip nodes
  -> immutable BoneProposal
  -> snapshot-backed EditBone transaction
  -> post validation or rollback
```

`Analyze` reads Blender RNA and freezes ordinary Python dataclasses. `_PLAN_STORE` holds no Blender RNA references. `Apply` accepts one exact `plan_id`, recomputes source and settings fingerprints, creates `UECP_SNAPSHOT::<sha256>`, modifies only allowed EditBone fields, then validates. UI lists and viewport caches are views, never transaction inputs.

Branches remain graph facts. Because one Blender bone has one tail, a branch parent receives no automatic proposal and child bones start new chains. Virtual tips have no Bone/Object/Vertex Group/Constraint identity.
