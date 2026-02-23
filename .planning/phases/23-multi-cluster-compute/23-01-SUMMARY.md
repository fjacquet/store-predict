---
phase: 23-multi-cluster-compute
plan: "01"
subsystem: pipeline
tags: [compute-sizing, health-checks, i18n, cluster, dataclass]
dependency_graph:
  requires: []
  provides:
    - ClusterSizingRow dataclass in compute_sizing.py
    - compute_cluster_breakdown() function
    - cluster field on HealthFinding
    - _check_hw_version_per_cluster() function
    - _check_small_cluster_ha() function
    - fr.yaml and en.yaml cluster i18n keys
  affects:
    - Plan 23-02 (UI — depends on stable pipeline functions)
tech_stack:
  added: []
  patterns:
    - groupby sort=True for alphabetical cluster iteration
    - sentinel __no_cluster__ for ungrouped VMs in compute; (No Cluster) label in health checks
    - frozen dataclass with optional default field (cluster: str = "")
key_files:
  created: []
  modified:
    - src/store_predict/pipeline/compute_sizing.py
    - src/store_predict/pipeline/health_checks.py
    - src/store_predict/i18n/locales/fr.yaml
    - src/store_predict/i18n/locales/en.yaml
    - tests/test_compute_sizing.py
    - tests/test_health_checks.py
decisions:
  - "Sentinel __no_cluster__ used in compute_cluster_breakdown() for groupby key; UI translation is Plan 02's concern"
  - "Per-cluster HW version check replaces global check in run_health_checks(); old _check_hw_version() kept as private helper"
  - "_check_small_cluster_ha() skips (No Cluster) group — standalone hosts have no HA context"
  - "cluster field placed last on HealthFinding to maintain backward compatibility (fields with defaults must be last)"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-23"
  tasks_completed: 3
  files_modified: 6
---

# Phase 23 Plan 01: Multi-Cluster Compute Pipeline Summary

**One-liner:** Per-cluster compute sizing via ClusterSizingRow/compute_cluster_breakdown() plus cluster-scoped health findings with HealthFinding.cluster field and two new check functions.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | ClusterSizingRow + compute_cluster_breakdown() | 7dd8d03 | compute_sizing.py |
| 2 | cluster field on HealthFinding + per-cluster checks | 94f53be | health_checks.py |
| 3 | i18n keys + tests | 29bea05 | fr.yaml, en.yaml, test_compute_sizing.py, test_health_checks.py |

## What Was Built

### Task 1: compute_sizing.py

Added `ClusterSizingRow` frozen dataclass:
```python
@dataclass(frozen=True)
class ClusterSizingRow:
    cluster_name: str
    vm_count: int
    total_vcpus: int
    total_ram_gib: float
    hosts_needed: int
```

Added `compute_cluster_breakdown(df, host_config, overcommit_ratio=4.0) -> list[ClusterSizingRow]`:
- Filters to active non-template VMs before groupby
- Normalizes cluster column; empty/null -> sentinel `__no_cluster__`
- Iterates `groupby("cluster_norm", sort=True)` for alphabetical output
- `hosts_needed = max(_hosts_n1(...), _hosts_by_ram(...))`
- Returns `[]` for None/empty df or all-excluded VMs

### Task 2: health_checks.py

- Added `cluster: str = ""` as last field on `HealthFinding` (backward-compatible)
- Replaced `_check_hw_version(active)` call with `_check_hw_version_per_cluster(active)`
- Added `_check_hw_version_per_cluster()`: groups by cluster, emits one finding per affected cluster with `cluster=str(cluster_name)`
- Added `_check_small_cluster_ha()`: flags named clusters with fewer than 3 VMs; skips `(No Cluster)` sentinel
- Both new functions added to `run_health_checks()` call chain

### Task 3: i18n + Tests

**fr.yaml** — 10 new keys under `compute:` (cluster_breakdown_heading, cluster_col, etc.) and `health.small_cluster_ha` title/detail.

**en.yaml** — Same 10 compute keys in English + `health.small_cluster_ha` title/detail.

**Tests added:**
- `test_compute_sizing.py`: 8 new tests in `TestClusterBreakdown` class
- `test_health_checks.py`: 8 new tests in `TestPerClusterHealthChecks` class

## Verification

- Full test suite: **455 passed, 2 pre-existing failures** (test_llm_classifier — out of scope, pre-existed before this plan)
- ruff check: **No issues**
- mypy: **Success: no issues found in 49 source files**
- New tests: 16 new tests all pass

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Files created/modified:
- [x] `src/store_predict/pipeline/compute_sizing.py` — ClusterSizingRow + compute_cluster_breakdown
- [x] `src/store_predict/pipeline/health_checks.py` — cluster field + per-cluster checks
- [x] `src/store_predict/i18n/locales/fr.yaml` — cluster_breakdown_heading present
- [x] `src/store_predict/i18n/locales/en.yaml` — cluster_breakdown_heading present
- [x] `tests/test_compute_sizing.py` — TestClusterBreakdown class
- [x] `tests/test_health_checks.py` — TestPerClusterHealthChecks class

Commits:
- [x] 7dd8d03 — feat(23-01): ClusterSizingRow and compute_cluster_breakdown()
- [x] 94f53be — feat(23-01): cluster field on HealthFinding and per-cluster checks
- [x] 29bea05 — feat(23-01): i18n keys and tests

## Self-Check: PASSED
