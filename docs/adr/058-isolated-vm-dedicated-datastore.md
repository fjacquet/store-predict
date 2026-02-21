# ADR-058: Dedicated datastore for mission-critical VMs

**Date:** 2026-02-21
**Status:** Accepted

## Context

The Performance strategy uses BFD to pack VMs into datastores with tier-specific
density caps (10–25 VMs/DS). However, certain mission-critical workloads should
**never share a datastore** with other VMs:

- **SAP HANA**: Multi-TB memory footprint, extreme IOPS, requires dedicated
  snapshot/backup windows. Best practice is separate volumes for data/log/shared.
- **Exchange**: Latency-sensitive mailbox I/O, large databases, requires isolated
  backup granularity for DAG recovery.
- **Large Oracle RAC**: Similar profile — dedicated QoS, independent snapshot scope.

Placing a SAP HANA VM alongside 9 other VMs on a "Hot tier" datastore defeats
the purpose of workload isolation:
- PowerStore volume-level snapshots would capture all 10 VMs, not just HANA
- QoS policy applies to the shared volume, not just HANA
- Restore requires mounting the entire 10-VM volume

## Decision

Add a **Phase 0 isolation pass** to the Performance strategy: before BFD
placement begins, extract VMs that match isolation criteria and assign each to
a dedicated 1:1 datastore. Remaining VMs proceed through normal Hot/Warm/Cold
tiered BFD.

Isolation triggers (any one is sufficient):
1. Workload category contains "SAP HANA" or "Exchange"
2. VM provisioned capacity exceeds 2 TB
3. VM IOPS exceeds 5,000

These thresholds are configurable via the Advanced Settings panel. The isolation
list can be extended by adding workload category patterns.

Isolated datastores are sized to the individual VM (with growth margin and
snapshot reserve applied), not to the global max datastore size. A 3 TB HANA VM
gets a ~4.6 TB datastore (3 TB / 0.65 usable ratio), not a 4 TB standard DS.

## Consequences

- The Performance strategy now has three phases: isolate → classify tiers → BFD
  per tier. This matches how storage architects actually design layouts.
- Isolated VMs contribute to total datastore count and raw capacity metrics but
  have utilization close to 100% and isolation score = 1.0.
- The Consolidation and Uniform strategies do **not** apply isolation — by design,
  they prioritize density and balance respectively. A user who wants isolation
  should choose the Performance strategy.
- The comparison table naturally shows the impact: Performance strategy will have
  more datastores but better isolation score and finer snapshot granularity.
