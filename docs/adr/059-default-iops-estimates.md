# ADR-059: Workload-based IOPS defaults for RVTools sizing

**Date:** 2026-02-21
**Status:** Accepted

## Context

RVTools exports do not include performance data (IOPS, throughput). When the
layout engine processes an RVTools import, every `VMCalculation` object has
`peak_iops=0` and `avg_iops=0`. Without IOPS estimates, the datastore IOPS
budget constraint (default: 100,000 IOPS/DS) becomes inactive, producing
layouts that ignore I/O contention entirely. Pre-sales sizing requires
defensible IOPS estimates even without measured performance data.

The layout engine already evaluates three placement strategies
(Consolidation/Performance/Uniform) against per-datastore IOPS budgets. If
all VMs report 0 IOPS, every VM fits any datastore and the IOPS constraint
never triggers — resulting in unrealistic proposals that would be repudiated
during a customer proof-of-concept.

## Decision

When `CalculationSummary.has_performance_data` is `False`, apply
workload-based IOPS estimates via `_apply_default_iops()` before layout
placement. The estimates are loaded from `src/store_predict/data/IOPS.csv`
(semicolon-delimited), falling back to hardcoded constants if the file is
missing. This follows the same pattern established by `samples/DRR.csv` for
DRR configuration.

**Default values (all conservative — peak IOPS, not average):**

| Workload | Default IOPS |
|----------|-------------|
| Database/Microsoft SQL | 500 |
| Database/Oracle | 800 |
| Database/SAP HANA(S4) | 1,000 |
| VDI/Full Clone / MCS (Citrix) | 30 |
| VDI/Linked Clone / PVS (Citrix) | 50 |
| Virtual Machines (generic) | 50 |
| File/General Purpose | 100 |
| Unknown (Reducible) | 50 |

`avg_iops` is estimated as 70% of peak. The 70% ratio is used only for
reporting metrics; constraint evaluation always uses `peak_iops`.

**Known limitation — Linux vs. Windows IOPS split:** REQ-014 specifies
separate IOPS values for Linux (40) and Windows (50) generic VMs. This split
is **not implemented**. The `workload_category` field does not distinguish OS
at the generic VM level — both Linux and Windows VMs map to the single
`Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email`
category string from `DRR.csv`. Implementing the split would require a
sub-classification pass on the OS field, which is out of scope. The
conservative value of 50 IOPS is applied to all generic VMs.

## Consequences

**Positive:**

- RVTools imports produce realistic datastore layout proposals — IOPS budget
  constraints are active and reflect expected workload patterns.
- Pre-sales engineers can adjust IOPS estimates without code changes by editing
  `src/store_predict/data/IOPS.csv` — same operator workflow as adjusting DRR values.
- Conservative (peak) values prevent under-provisioning in pre-sales quotes.
- Hardcoded fallback keeps unit tests independent of the CSV file.

**Negative:**

- Estimated IOPS may over-provision for genuinely low-I/O workloads (e.g.,
  archival databases classified as SQL at 500 IOPS may need only 50).
- No OS-level IOPS differentiation is possible without a data model change;
  Linux and Windows generic VMs receive the same 50 IOPS estimate.
- If a customer's `IOPS.csv` keys drift from `DRR.csv` workload_category
  strings, the lookup silently falls back to the 50 IOPS constant; operators
  must keep key names in sync.
