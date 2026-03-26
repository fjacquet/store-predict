# ADR-077: Composite (category, drr) Groupby Key for WorkloadGroupResult

**Status:** Accepted
**Date:** 2026-03-26
**Milestone:** v8.0 Reporting Fidelity

## Context

`calculation.py` previously used `vm.workload_category` (string) as the key when grouping VMs into `WorkloadGroupResult` rows. This caused all VMs with the same workload category to collapse into a single row even when they had different DRR values — e.g., SQL Server uncompressed (DRR=5.0) and SQL Server encrypted (DRR=1.0) merged into one "Database / Microsoft SQL" row. The merged row's `avg_drr` was a weighted average of the two DRR values, which was inaccurate and misleading for pre-sales sizing (Issue #5).

## Decision

Change the groupby key from `vm.workload_category: str` to the composite tuple `(vm.workload_category, vm.drr): tuple[str, float]`.

Each unique `(category, drr)` pair now produces a separate `WorkloadGroupResult` row. A `drr: float = 0.0` field is added to `WorkloadGroupResult` to carry the per-group DRR value.

## Consequences

**Positive:**
- PDF, Excel, and web UI workload breakdown tables now show one row per `(category, drr)` pair — accurate and honest for pre-sales proposals
- The ECharts Sankey requires unique node names; a Counter-based `_node_name()` helper appends the DRR suffix only when the same category appears with multiple DRR values (avoids cluttering the common single-DRR case)
- `drr: float = 0.0` default on the frozen dataclass preserves backward compatibility with 30+ existing test call sites that construct `WorkloadGroupResult` without the `drr` argument

**Negative:**
- A customer with many DRR variants per category will see more rows in the breakdown table; this is intentional and correct, but could surprise users expecting one row per workload type

**Neutral:**
- PDF and Excel report code was untouched — both already iterate `workload_groups` verbatim, so the split rows propagate automatically
