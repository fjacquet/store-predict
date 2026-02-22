# Phase 21 Research: Health Check Module & Concerns Page

**Phase:** 21
**Date:** 2026-02-22
**Status:** Complete

## Problem

Pre-sales engineers presenting storage sizing to customers can be blindsided by
data quality issues, inflated estimates from unclassified VMs, or VMware
environment problems that affect migration feasibility. Surfacing these findings
early — from the same static export already uploaded — allows engineers to
address them before the customer meeting.

## Key Findings

### Columns Requiring Parser Extension

`hw_version` (VMware hardware version integer) and `tools_status` (VMware Tools
state string) are present in RVTools vInfo tab but were not yet in
`CANONICAL_COLUMNS`. LiveOptics exports lack these columns entirely.

**Resolution:**

- Added to `CANONICAL_COLUMNS` and `RVTOOLS_ALIASES` in `columns.py`
- RVTools parser reads both with graceful fallback (`0` / `""`)
- LiveOptics parser sets sentinel values (`hw_version=0`, `tools_status=""`)

### Sentinel Zero Guard

`hw_version=0` means "data not available" (LiveOptics or RVTools without the HW
version column). The guard `hw_version > 0` must precede **all** hardware
version comparisons. Without this guard, all LiveOptics VMs would be falsely
flagged as having very old hardware (`0 < 14` is True).

### Session Integrity Constraint

Health checks must call `load_session_data()` — not `classify_dataframe()`. The
session DataFrame may contain user-edited `workload_category` values from the
Review grid. Re-classifying from scratch discards those edits and produces stale
findings. See ADR-061.

### Test Strategy

- No `unittest.mock` — project convention; health check functions are pure
  DataFrame transformations testable with synthetic DataFrames
- `_make_active_df(**overrides)` helper provides healthy defaults; individual
  fields are overridden per test
- Assertions check `check_id` and `severity` — not `title` strings (i18n keys)

## Health Check Inventory

| Check ID | Severity | Trigger |
|----------|----------|---------|
| `data_quality.missing_os` | Warning | `os_name == ""` |
| `data_quality.zero_provisioned` | Warning | `provisioned_mib == 0` |
| `data_quality.missing_cpu` | Info | `num_cpus == 0` |
| `data_quality.missing_ram` | Info | `memory_mib == 0` |
| `data_quality.high_powered_off_ratio` | Info | >30% powered-off |
| `sizing_risk.high_unknown_ratio` | Warning | >25% Unknown active VMs |
| `sizing_risk.large_unknown_vms` | Warning | Unknown + provisioned ≥ 1 TiB |
| `sizing_risk.iops_budget_exceeded` | Warning | `peak_iops > 100 000` |
| `best_practice.no_cluster` | Warning | `cluster == ""` |
| `best_practice.old_hw_version` | Warning | `14 ≤ hw_version < 17` |
| `best_practice.very_old_hw_version` | Critical | `0 < hw_version < 14` |
| `best_practice.tools_not_installed` | Critical | `tools_status == "toolsNotInstalled"` |
| `best_practice.tools_not_running` | Warning | `tools_status == "toolsNotRunning"` |

## Implementation Notes

- Single `health_checks.py` file (~300 lines) — not split model+engine (too small
  to justify two files at current size)
- `HealthFinding` and `HealthCheckResult` are `frozen=True` dataclasses, matching
  the `DatastoreRecommendation` pattern from `layout_models.py`
- `affected_vms` tuple contains raw VM names for UI display **only** — never log
  them via Python's `logging` module (CLAUDE.md security rule)
- Powered-off VMs and templates are filtered to an `active` sub-DataFrame before
  any best-practice check is evaluated
