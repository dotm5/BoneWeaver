# BoneWeaver Backend Hardening Performance Report

## Real 85-Bone Run

- Meshes/vertices/memberships: 1 / 25,610 / 54,515
- Vertex passes: 1
- Membership passes: 1
- Mesh scan: 0.436817 s
- Weight cloud/connectivity: 0.864458 s
- Fingerprint composition: 0.003273 s
- Analyze: 1.346255 s
- Apply: 0.447153 s
- Post validation: 0.301781 s
- Peak compact temporary memory: 731,456 bytes
- Peak temporary weighted points: 1,076
- Serialized Plan size: 541,999 bytes

## Scale Contracts

Automated compact-buffer profiles cover 100 bones/100k vertices, 300 bones/500k vertices, and 500 bones/1M vertices. Indices use `array('I')`; coordinates and statistical weights use `array('d')`. The weighted point buffers use 36 bytes per selected vertex before topology edges, scale linearly, and do not allocate a Python Vector, tuple, or dataclass per vertex. No NumPy import exists in runtime source.

`MeshScanCache` combines base coordinates, vertex-group digest, membership collection, area/exclusivity evidence, topology input, and summary data in one full vertex/membership pass per Mesh. Apply-time source fingerprint uses one joint weight/base digest pass per Mesh.
