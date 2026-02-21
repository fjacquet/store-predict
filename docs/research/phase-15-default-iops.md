# Phase 15: Default IOPS Estimates

**Researched:** 2026-02-21
**Domain:** Layout engine — IOPS estimation for RVTools imports

---

## Problem Statement

RVTools `.xlsx` exports contain disk provisioning and in-use data but no
performance metrics. When the layout engine processes an RVTools import, every
`VMCalculation` starts with `peak_iops=0`. Without IOPS estimates, the
datastore IOPS budget constraint (default: 100,000 IOPS/DS) is permanently
inactive — every VM "fits" any datastore on the IOPS dimension, producing
placements that ignore I/O contention entirely.

Pre-sales sizing must account for IOPS even when measured data is unavailable.
The solution is to inject conservative, workload-based IOPS estimates before
layout placement when `CalculationSummary.has_performance_data` is `False`.

---

## IOPS Values by Workload

| Workload | Default IOPS | Source | Notes |
|----------|-------------|--------|-------|
| Database/Microsoft SQL | 500 | Dell PowerStore VMware Best Practices (H18264) | Steady-state OLTP, 8K random I/O |
| Database/Oracle | 800 | Dell PowerStore Oracle Best Practices | OLTP including redo log I/O overhead |
| Database/SAP HANA(S4) | 1,000 | SAP HANA Hardware Directory sizing criteria | In-memory but persistent log I/O |
| VDI/Full Clone / MCS (Citrix) | 30 | VMware Horizon 8 Reference Architecture | Boot storm excluded; steady state only |
| VDI/Linked Clone / PVS (Citrix) | 50 | VMware Horizon sizing guide | Higher due to replica disk writes |
| Virtual Machines (generic) | 50 | Dell conservative estimate | No OS/workload signal available |
| File/General Purpose | 100 | Dell PowerStore file services best practices | NFS/SMB mixed I/O profile |
| Unknown (Reducible) | 50 | Conservative fallback | Applied when workload is unclassifiable |

All values are **peak IOPS** estimates. See the "Why Peak IOPS" section below.

---

## Why Peak IOPS, Not Average

The layout engine evaluates datastore IOPS budgets to decide how many VMs can
share a single datastore. The binding constraint is **peak** load, not average.

If average IOPS were used, an OLTP SQL server that peaks at 2,000 IOPS could
be placed alongside many other "average 500 IOPS" servers. All would appear
within budget until the peak hit simultaneously — exactly the scenario
pre-sales must protect against.

**Pre-sales sizing rule:** Use peak IOPS for capacity planning. Average IOPS
is used only for reporting (throughput summaries, utilization metrics).

The layout engine estimates `avg_iops = 0.70 × peak_iops`. The 70% ratio
reflects industry observation that busy systems sustain 60–75% of peak in
steady operation. This ratio applies to reporting only; the IOPS budget
constraint always uses `peak_iops`.

---

## Conservative Bias

All IOPS estimates use the **lower bound** of published ranges:

- Microsoft SQL: 500 IOPS (range: 500–1,500/core for moderate OLTP)
- Oracle: 800 IOPS (range: 800–1,200 for moderate databases)
- SAP HANA: 1,000 IOPS (minimum required by SAP certification criteria)
- Generic VMs: 50 IOPS (covers mixed general-purpose workloads)

Pre-sales sizing must not under-provision. A customer who buys hardware sized
for 800 IOPS/Oracle VM and finds the system saturated at 600 IOPS will lose
trust in the pre-sales recommendation. The conservative choice is to err
toward more datastores with lower VM density.

---

## CSV Configurability

IOPS defaults are loaded from `src/store_predict/data/IOPS.csv` (semicolon-delimited),
following the same pattern as `samples/DRR.csv`. Pre-sales engineers can
adjust estimates without code changes:

```csv
Workload Category;IOPS Estimate
Database/Microsoft SQL;500
Database/Oracle;800
Database/SAP HANA(S4);1000
VDI/Full Clone / MCS (Citrix);30
VDI/Linked Clone / PVS (Citrix);50
Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email;50
File/General Purpose;100
Unknown (Reducible)/Unknown (Reducible);50
```

**Operator workflow:** Edit `src/store_predict/data/IOPS.csv` and restart the application.
The loader strips whitespace and skips invalid rows. If the file is missing,
the hardcoded constants take effect — unit tests remain independent.

**Key-matching requirement:** Column one must exactly match the
`workload_category` strings produced by the classification engine (format:
`Category/Subcategory`). A mismatch silently falls back to the 50 IOPS
constant. Operators can verify key alignment by inspecting the VM review page
workload category labels.

---

## Known Limitation: Linux vs. Windows IOPS

REQ-014 specifies separate IOPS estimates for Linux VMs (40 IOPS) and Windows
VMs (50 IOPS). This split is **not implemented**.

The `workload_category` field — the only lookup key available at layout time —
does not distinguish OS for generic VMs. Both Linux and Windows VMs that are
unclassified as database/VDI/file share the single category:

```
Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email
```

Splitting by OS would require a sub-classification pass on the `os` column
from the canonical DataFrame, which would mean the layout engine must accept
the raw DataFrame in addition to the `CalculationSummary`. This is a data
model change that is out of scope for Phase 15.

**Resolution:** 50 IOPS for all generic VMs (the more conservative value,
aligned with Windows). Documented in ADR-059 as a known limitation.

---

## PowerStore IOPS Architecture Context

PowerStore NVMe arrays (T model) claim up to 7 million IOPS at the array
level. Per-datastore IOPS is bounded by software QoS policies (optional) or
by pool saturation. The layout engine's default `iops_budget_per_ds = 100,000`
is a conservative planning value that:

- Leaves headroom for peak spikes above the default estimates
- Aligns with Dell H18264 recommendations for mixed workload datastores
- Allows approximately 200 generic VMs (50 IOPS each) per datastore before
  hitting the budget — consistent with the 25 VMs/DS VM count default

When a customer provides LiveOptics data with measured IOPS, the default
injection is skipped (`has_performance_data=True`) and real values are used.

---

## References

| Source | Description |
|--------|-------------|
| Dell PowerStore VMware Best Practices (H18264) | IOPS planning values for mixed workloads on PowerStore |
| Dell EMC PowerStore and Oracle RAC Best Practices | Oracle OLTP IOPS sizing at 8K block size |
| Dell EMC PowerStore and SAP HANA Best Practices | SAP HANA log I/O requirements and sizing guidance |
| VMware Horizon 8 Reference Architecture | VDI IOPS benchmarks — steady state and boot storm values |
| SAP HANA Hardware Directory | Minimum IOPS certification criteria for HANA-certified storage |
| Microsoft SQL Server Storage Guidance | IOPS per core recommendations for OLTP workloads |
