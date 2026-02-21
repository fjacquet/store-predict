# ADR-057: VMFS datastore layout, not vVol

**Date:** 2026-02-21
**Status:** Accepted

## Context

Dell PowerStore supports two VMware storage paradigms:

| Feature | VMFS Datastores | vVol Datastores |
|---------|----------------|-----------------|
| Snapshot granularity | Volume-level (all VMs) | Per-VM via VASA |
| QoS | Per-volume | Per-VM (SPBM) |
| Operational maturity | Very mature | Newer, fewer admins |
| Backup tool support | Universal | Growing but incomplete |
| Dell recommendation | Supported | Preferred for new deployments |

Dell's own documentation recommends vVols for new deployments. However, the
practical reality for migration projects is different: most customers migrating
from legacy arrays (VNX2, SC Series, Unity) have VMFS datastores today and will
continue using VMFS on PowerStore.

## Decision

The layout engine generates **VMFS datastore recommendations only**. vVol layout
is out of scope.

Rationale:

1. **Migration continuity**: Customers moving from legacy → PowerStore keep VMFS.
   Proposing vVol adds a second migration dimension (storage paradigm change)
   that complicates the project.
2. **Snapshot/backup implications matter**: VMFS volume-level snapshots make
   datastore layout directly impactful for RPO/RTO. With vVols, per-VM snapshots
   make layout less critical — the engine's value proposition is weaker.
3. **SDRS/SIOC deprecation**: VMware deprecated SDRS I/O balancing and SIOC in
   vSphere 8.0 U3 (June 2024). This means VMFS layouts can no longer rely on
   automatic I/O rebalancing, making manual layout planning (what our engine does)
   more valuable than ever.
4. **Pre-sales reality**: The target user is proposing a migration, not a greenfield
   deployment. VMFS is what they'll present to the customer.

## Consequences

- The layout engine operates in terms of VMFS datastores (volumes), not vVol
  storage containers.
- Snapshot granularity ratings in comparison metrics are meaningful because VMFS
  snapshots are volume-scoped.
- A future version could add vVol recommendations as a fourth strategy or a
  separate mode, but this is deferred.
