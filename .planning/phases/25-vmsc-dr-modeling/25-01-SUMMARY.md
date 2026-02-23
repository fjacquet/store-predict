---
phase: 25-vmsc-dr-modeling
plan: "01"
subsystem: pipeline/compute-sizing
tags: [compute, vmsc, dr, split-ratio, i18n, tests]
dependency_graph:
  requires: []
  provides:
    - compute_sizing() with vmsc_split_ratio and ap_active_ratio params
    - ComputeSizingResult.vmsc_site_a_hosts / vmsc_site_b_hosts fields
    - i18n keys for split ratio UI inputs
  affects:
    - src/store_predict/ui/pages/compute.py (UI references updated)
    - Phase 25-02 (UI will use new fields for controls)
tech_stack:
  added: []
  patterns:
    - Proportional per-site sizing using configurable split ratios
    - Clamped float parameters for robust pre-sales input handling
key_files:
  created: []
  modified:
    - src/store_predict/pipeline/compute_sizing.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - tests/test_compute_sizing.py
    - src/store_predict/ui/pages/compute.py
decisions:
  - "vmsc_split_ratio clamped to [0.01, 0.99] — never allows one site to carry 0% or 100% of load"
  - "ap_active_ratio clamped to [0.01, 1.0] — always produces at least a minimal primary sizing"
  - "ap_secondary remains at max(1, ceil(primary/2)) regardless of ap_active_ratio — cold standby convention"
  - "vmsc_hosts_per_site removed in favor of distinct vmsc_site_a_hosts/vmsc_site_b_hosts — enables asymmetric UI display"
  - "compute.py UI updated with minimal fix (zip loop) to avoid crash before 25-02 full UI overhaul"
metrics:
  duration: "~18 min"
  completed: "2026-02-23"
  tasks: 2
  files: 5
---

# Phase 25 Plan 01: vMSC & DR Modeling — Configurable Site Split Ratios

Configurable split-ratio support added to compute_sizing() via vmsc_split_ratio (vMSC per-site proportioning) and ap_active_ratio (AP primary load fraction), replacing the fixed 50/50 vMSC assumption and 100% AP primary assumption.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Extend compute_sizing() with configurable site ratios | 5835e10 | compute_sizing.py, test_compute_sizing.py, compute.py |
| 2 | Add i18n keys and tests for configurable ratios | 08ede5c | en.yaml, fr.yaml, test_compute_sizing.py |

## What Was Built

### compute_sizing.py

- `ComputeSizingResult` now has `vmsc_site_a_hosts: int` and `vmsc_site_b_hosts: int` (replaces removed `vmsc_hosts_per_site`)
- `compute_sizing()` gains two new parameters:
  - `vmsc_split_ratio: float = 0.5` — fraction of VM load on Site A; Site B receives `1 - ratio`; clamped to `[0.01, 0.99]`
  - `ap_active_ratio: float = 1.0` — fraction of VMs active on AP primary; clamped to `[0.01, 1.0]`
- vMSC per-site sizing computes separate vCPU and RAM proportions, then applies `max(_hosts_n1, _hosts_by_ram)` per site independently
- AP primary sizing applies `ap_active_ratio` to both vCPU and RAM totals before computing hosts; secondary remains `max(1, ceil(primary / 2))`
- All edge cases (empty df, no datacenter, all powered off, zero CPU+RAM) preserved

### i18n Keys Added

Both `en.yaml` and `fr.yaml` receive 6 new keys under `compute:`:
- `vmsc_split_ratio`, `vmsc_split_hint`, `vmsc_site_a`, `vmsc_site_b`
- `ap_active_ratio`, `ap_active_hint`

Tooltip keys `compute_vmsc` and `compute_ap` updated to remove hardcoded percentage references.

### Tests (56 total, 9 new)

**TestVMSCConfigurableSplit (5 tests):**
- 50/50 default produces symmetric site counts
- 60/40 split produces site_a >= site_b
- Ratio 0.0 clamped to 0.01 (no crash)
- Ratio 1.0 clamped to 0.99 (bounded)
- vmsc_enabled=False zeroes both site counts regardless of ratio

**TestAPActiveRatio (4 tests):**
- Default 1.0 ratio matches hosts_n1
- 0.8 ratio reduces primary vs full load
- 0.0 clamped to 0.01 (no crash, secondary >= 1)
- Secondary always equals max(1, ceil(primary/2)) for any ratio value

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated compute.py UI to use new field names**
- **Found during:** Task 1 — removing `vmsc_hosts_per_site` breaks `compute.py` line 209
- **Issue:** `result.vmsc_hosts_per_site` reference in UI would raise `AttributeError` at runtime
- **Fix:** Replaced with a `zip` loop over `vmsc_sites` and `[vmsc_site_a_hosts, vmsc_site_b_hosts]`
- **Files modified:** `src/store_predict/ui/pages/compute.py`
- **Commit:** 5835e10 (included in Task 1 commit)
- **Note:** 25-02 will fully overhaul this UI section with proper split ratio controls

## Self-Check

### Files Exist
- [x] `src/store_predict/pipeline/compute_sizing.py` — contains `vmsc_split_ratio`, `vmsc_site_a_hosts`, `vmsc_site_b_hosts`
- [x] `src/store_predict/i18n/locales/en.yaml` — contains `vmsc_split_ratio`, `vmsc_site_a`, `ap_active_ratio`
- [x] `src/store_predict/i18n/locales/fr.yaml` — contains `vmsc_split_ratio`, `vmsc_site_a`, `ap_active_ratio`
- [x] `tests/test_compute_sizing.py` — contains `TestVMSCConfigurableSplit` and `TestAPActiveRatio`

### Commits Exist
- [x] 5835e10 — Task 1 (compute_sizing.py, tests, compute.py UI fix)
- [x] 08ede5c — Task 2 (i18n keys, new test classes)

### Test Results
- 56 tests pass, 0 failures
- ruff: no issues
- mypy: no issues

## Self-Check: PASSED
