# ADR-056: Three fixed layout strategies with tunable parameters

**Date:** 2026-02-21
**Status:** Accepted

## Context

Pre-sales engineers need datastore layout recommendations but have different
priorities depending on the customer conversation:

- Some customers prioritize **cost** (fewest datastores, lowest management overhead)
- Some prioritize **performance** (workload isolation, latency guarantees)
- Some prioritize **operational simplicity** (uniform sizing, predictable management)

A single "best" layout cannot satisfy all three goals simultaneously.

## Decision

Generate **three alternative layouts** in parallel, each optimized for a different
priority. The user sees a side-by-side comparison and picks the one that fits their
customer's priorities.

### Strategy 1: Consolidation
- **Goal**: Minimize datastore count
- **Algorithm**: Multi-dimensional BFD packing VMs as tightly as possible
- **Trade-off**: Higher contention risk, coarser snapshot granularity

### Strategy 2: Performance
- **Goal**: Maximize workload isolation and minimize I/O contention
- **Algorithm**: Two-phase placement — classify VMs into Hot/Warm/Cold tiers,
  then BFD each tier separately with tier-specific constraints
- **Rules**: Hot tier (databases, >500 IOPS) limited to 15 VMs/DS; anti-affinity
  prevents co-locating Database and VDI workloads
- **Trade-off**: More datastores, lower capacity utilization

### Strategy 3: Uniform
- **Goal**: All datastores same size, balanced utilization
- **Algorithm**: LPT (Longest Processing Time) balanced assignment across a
  pre-computed number of equal-sized datastores
- **Trade-off**: Doesn't adapt to workload skew, may waste space on light DS

### Tunable parameters (Advanced Settings panel)
All three strategies share the same configurable constraints:
- Max datastore capacity (default: 4 TB — Dell best practice sweet spot)
- Max VMs per datastore (default: 25 — Dell recommendation)
- IOPS budget per datastore (default: 100,000)
- Snapshot reserve % (default: 15%)
- Growth margin % (default: 20%)

## Consequences

- The user always sees three options — no single "magic answer" that may be wrong
  for their specific customer context.
- Comparison metrics (DS count, utilization, isolation score, snapshot granularity)
  help the user explain the trade-offs to customers.
- Default values are sourced from Dell's VMware vSphere Best Practices (H18116)
  and validated by domain research. Pre-sales engineers can override via the
  Advanced Settings panel.
- Adding a fourth strategy in future is straightforward: implement a new function
  and add it to `generate_all_proposals()`.
