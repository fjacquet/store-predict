# ADR-055: Multi-dimensional BFD heuristic for datastore layout engine

**Date:** 2026-02-21
**Status:** Accepted

## Context

StorePredict v3.0 adds a datastore layout recommendation engine. Given classified
VMs with capacity, IOPS, and workload data, the engine must assign VMs to datastores
while respecting three simultaneous constraints: capacity, IOPS budget, and VM count
per datastore. This is a **multi-dimensional bin packing** problem (NP-hard).

Two families of approaches were considered:

| Approach | Pros | Cons |
|----------|------|------|
| **ILP solver** (PuLP, OR-Tools) | Provably optimal | Heavy dependency (50+ MB), slow for >500 VMs, complex to maintain |
| **BFD heuristic** (Best Fit Decreasing) | Pure Python, fast (<2s for 1,000 VMs), within 10-15% of optimal | Not provably optimal |

## Decision

Use **multi-dimensional Best Fit Decreasing (BFD)** with normalized scoring as the
placement algorithm for all three strategies (Consolidation, Performance, Uniform).

The algorithm:
1. Normalize each VM as `max(capacity_ratio, iops_ratio)` where ratios are relative
   to per-datastore limits
2. Sort VMs descending by this score (largest/most-demanding first)
3. For each VM, place in the datastore with the **least remaining capacity** that
   still satisfies all three constraints (capacity + IOPS + VM count)
4. When no datastore fits, create a new one

For the **Uniform strategy**, a variant (LPT — Longest Processing Time) is used
instead: pre-compute the number of datastores, then assign each VM to the
least-loaded datastore for balanced utilization.

## Consequences

- **No new dependencies**: Pure Python dataclasses + list operations. No numpy,
  PuLP, or OR-Tools. Keeps Docker image small and CI fast.
- **Performance**: O(n × m) where n = VMs and m = datastores. For 1,000 VMs and
  ~40 datastores, this is ~40,000 comparisons — trivial.
- **Quality**: BFD is well-studied and consistently produces solutions within
  11/9 × OPT for single-dimension packing. Multi-dimensional quality is typically
  within 10-15% of ILP optimal for real-world VM distributions.
- **Extensibility**: Adding a fourth strategy (e.g., workload-segregated with
  affinity rules) only requires a new function that calls the same `_bfd_place()`
  core with different constraints.
- **Trade-off accepted**: We sacrifice provably optimal packing for zero-dependency
  simplicity and sub-second execution. For pre-sales sizing (not production
  automation), 10-15% suboptimality is acceptable.
