---
phase: 22-compute-sizing-module-page
plan: "01"
subsystem: pipeline
tags: [compute-sizing, host-config, dell-presets, vmsc, active-passive, n1-ha]
dependency_graph:
  requires: []
  provides:
    - "HostConfig frozen dataclass for physical host specification"
    - "ComputeSizingResult frozen dataclass with all N+1/vMSC/AP fields"
    - "DELL_POWEREDGE_PRESETS list of 9 verified server configs"
    - "compute_sizing() entry point for ESXi host count calculation"
  affects:
    - "src/store_predict/pipeline/__init__.py (new export)"
    - "Phase 22-02 UI page will import from this module"
tech_stack:
  added: []
  patterns:
    - "Frozen dataclass pair (HostConfig + ComputeSizingResult)"
    - "Pure pipeline module with zero UI imports"
    - "Overcommit ratio clamped to [0.5, 20.0] for safety"
    - "pd.to_numeric(..., errors='coerce').fillna(0) for session round-trip safety"
key_files:
  created:
    - src/store_predict/pipeline/compute_sizing.py
    - tests/test_compute_sizing.py
  modified: []
decisions:
  - "ComputeSizingResult fields include both hosts_by_vcpu and hosts_by_ram for UI binding indicator"
  - "vmsc_hosts_per_site=0 (not None) when vMSC unavailable/disabled — avoids Optional in downstream UI code"
  - "Overcommit clamp range [0.5, 20.0] (not [1.0, 10.0]) to support edge case sizing scenarios"
  - "ap_secondary_hosts = max(1, ceil(primary/2)) — minimum 1 even for single-host primary"
metrics:
  duration_seconds: 256
  completed_date: "2026-02-22"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 39
---

# Phase 22 Plan 01: Compute Sizing Pipeline Module Summary

Pure pipeline module `compute_sizing.py` with frozen dataclasses, 9 Dell PowerEdge presets, N+1 HA formula, vMSC stretch cluster support, and Active/Passive DR sizing — accompanied by 39 comprehensive tests with 100% module coverage and no unittest.mock.

## What Was Built

### `src/store_predict/pipeline/compute_sizing.py`

**Exports (`__all__`):**
- `DELL_POWEREDGE_PRESETS` — list of 9 HostConfig presets
- `ComputeSizingResult` — frozen dataclass with all sizing outputs
- `HostConfig` — frozen dataclass for physical host specification
- `compute_sizing()` — entry point function

**DELL_POWEREDGE_PRESETS (9 entries):**
1. `R760 (2x28c / 512 GiB)` — Intel Xeon 5th Gen, 28 cores/socket, 2 sockets, 512 GiB RAM
2. `R760 (2x32c / 512 GiB)` — Intel Xeon 5th Gen, 32 cores/socket, 2 sockets, 512 GiB RAM
3. `R770 (2x48c / 1024 GiB)` — Intel Xeon 6 P-core, 48 cores/socket, 2 sockets, 1024 GiB RAM
4. `R770 (2x64c / 1536 GiB)` — Intel Xeon 6 P-core, 64 cores/socket, 2 sockets, 1536 GiB RAM
5. `R860 (4x32c / 1024 GiB)` — Intel Xeon 4-socket, 32 cores/socket, 4 sockets, 1024 GiB RAM
6. `R960 (4x32c / 1536 GiB)` — Intel Xeon 4-socket, 32 cores/socket, 4 sockets, 1536 GiB RAM
7. `R7725 (2x96c / 1536 GiB)` — AMD EPYC 9005, 96 cores/socket, 2 sockets, 1536 GiB RAM
8. `XE7745 (2x64c / 1152 GiB)` — AMD EPYC 9005 AI/GPU, 64 cores/socket, 2 sockets, 1152 GiB RAM
9. `Custom` — defaults to 28 cores/socket, 2 sockets, 512 GiB RAM

**ComputeSizingResult fields:**
- `has_data: bool` — False when df is None/empty or all VMs excluded
- `total_active_vcpus: int` — sum of num_cpus for active non-template VMs
- `total_active_ram_gib: float` — sum of memory_mib / 1024 for active VMs
- `excluded_vm_count: int` — count of powered-off + template VMs
- `hosts_by_vcpu: int` — N+1 hosts driven by vCPU constraint
- `hosts_by_ram: int` — N+1 hosts driven by RAM constraint
- `hosts_n1: int` — max(hosts_by_vcpu, hosts_by_ram)
- `vmsc_available: bool` — True when >= 2 distinct non-empty datacenter values
- `vmsc_sites: tuple[str, ...]` — distinct datacenter names
- `vmsc_hosts_per_site: int` — per-site N+1 host count (0 if unavailable/disabled)
- `ap_primary_hosts: int` — same as hosts_n1
- `ap_secondary_hosts: int` — ceil(hosts_n1 / 2), minimum 1
- `host_config: HostConfig` — the config used for this result
- `overcommit_ratio: float` — clamped value [0.5, 20.0] actually used

### `tests/test_compute_sizing.py`

**39 tests across 7 test classes:**
- `TestEdgeCases` (6 tests) — None df, empty df, zero CPU+RAM, all powered-off, template excluded, combined count
- `TestN1Formula` (4 tests) — basic formula, large workload, minimum 2 hosts, max constraint
- `TestRAMConstraint` (2 tests) — RAM binding, vCPU binding
- `TestOvercommitClamping` (6 tests) — clamp below, clamp above, negative, in-bounds, boundary values
- `TestVMSC` (6 tests) — single datacenter, empty datacenter, no column, two datacenters, disabled/enabled
- `TestActivePassive` (4 tests) — half of primary, round-up, minimum 1, primary equals hosts_n1
- `TestPresets` (5 tests) — count, R7725/not-R7275, Custom last, total_cores property, total_ram_mib property
- `TestMemoryMibSessionRoundTrip` (3 tests) — None memory, mixed None/float, None CPU

**Coverage:** 100% on `compute_sizing.py`

## Decisions Made

1. **ComputeSizingResult field naming**: Used `hosts_by_vcpu/hosts_by_ram/hosts_n1` (not `SiteResult`) to make downstream UI code direct — the UI page reads individual fields without nested objects.

2. **vmsc_hosts_per_site = 0 when disabled**: Chose integer 0 over Optional[int] to simplify downstream UI code that needs to check and display the value.

3. **Overcommit range [0.5, 20.0]**: The plan specified [0.5, 20.0]. The research mentioned [1.0, 10.0] as a separate recommendation. The plan takes precedence; [0.5, 20.0] allows more edge case sizing.

4. **No `SiteResult` dataclass**: The prompt specified a `SiteResult` dataclass but the test spec uses flat fields on `ComputeSizingResult`. Went with the test spec's field names for direct compatibility.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Linting] Ruff import order and __all__ sorting**
- **Found during:** Task 1 verification
- **Issue:** Import block ordering (stdlib before third-party required) and `__all__` not sorted alphabetically
- **Fix:** Applied `ruff --fix` to auto-fix import sorting and `__all__` ordering
- **Files modified:** `compute_sizing.py`, `test_compute_sizing.py`
- **Commit:** included in main commit `ceedbdc`

**2. [Rule 2 - Linting] SIM108 ternary operator**
- **Found during:** Task 2 verification
- **Issue:** if/else block in test helper should be ternary per ruff SIM108
- **Fix:** Converted to ternary `vcpus = 1 if target_hosts_n1 == 1 else ...`
- **Files modified:** `test_compute_sizing.py`
- **Commit:** included in main commit `ceedbdc`

### Out-of-Scope Pre-existing Failure

**test_llm_classifier.py::test_llm_config_max_concurrent_default** — pre-existing failure asserting `max_concurrent == 5` when actual value is `1`. Not caused by this plan. Logged to deferred items.

## Self-Check

- [x] `src/store_predict/pipeline/compute_sizing.py` exists
- [x] `tests/test_compute_sizing.py` exists
- [x] Commit `ceedbdc` exists
- [x] 39 tests pass, 0 failures in test_compute_sizing.py
- [x] 100% coverage on compute_sizing.py
- [x] mypy passes with 0 errors
- [x] ruff check passes, ruff format passes

## Self-Check: PASSED
