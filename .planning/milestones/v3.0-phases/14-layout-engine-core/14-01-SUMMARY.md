---
phase: 14-layout-engine-core
plan: "01"
subsystem: pipeline/layout-engine
tags:
  - layout-engine
  - bfd
  - dataclasses
  - consolidation
dependency_graph:
  requires:
    - src/store_predict/pipeline/calculation.py
  provides:
    - src/store_predict/pipeline/layout_models.py
    - src/store_predict/pipeline/layout_engine.py
    - tests/test_layout_engine.py
  affects:
    - Plan 14-02 (adds Performance and Uniform strategies on top)
tech_stack:
  added: []
  patterns:
    - frozen dataclasses with TYPE_CHECKING imports
    - mutable builder + frozen output pattern (BFD)
    - dataclasses.replace() for frozen dataclass modification
key_files:
  created:
    - src/store_predict/pipeline/layout_models.py
    - src/store_predict/pipeline/layout_engine.py
    - tests/test_layout_engine.py
  modified: []
decisions:
  - Moved VMCalculation import to TYPE_CHECKING block (ruff TC001 — unsafe fix applied)
  - Used dataclasses.replace() for _apply_default_iops instead of manual constructor
  - Oversized VMs detected before BFD loop and placed in dedicated _OVER_ datastores
  - OVER datastores are skipped during BFD bin selection loop
metrics:
  duration_minutes: 5
  completed_date: "2026-02-21"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
  tests_added: 25
  tests_total: 271
---

# Phase 14 Plan 01: Layout Engine Data Models and Consolidation Strategy Summary

**One-liner:** Frozen dataclasses (PlacementConstraints, DatastoreRecommendation, LayoutMetrics, LayoutProposal) plus multi-dimensional BFD consolidation strategy with oversized VM handling and default IOPS injection.

## What Was Built

Two new pipeline modules implementing the foundational layout engine components:

**`src/store_predict/pipeline/layout_models.py`** — 4 frozen dataclasses:
- `PlacementConstraints`: 4 TiB DS size, 25 VMs/DS, 100K IOPS/DS defaults with computed `usable_ratio` and `usable_capacity_mib` properties
- `DatastoreRecommendation`: immutable DS snapshot with assigned VMs as `tuple`, workload types as `frozenset`
- `LayoutMetrics`: 15-field aggregate metrics including isolation score, snapshot granularity rating, oversized VM count
- `LayoutProposal`: strategy name + datastores + metrics
- `DEFAULT_IOPS_BY_WORKLOAD` dict and `_DEFAULT_IOPS_FALLBACK = 50.0`

**`src/store_predict/pipeline/layout_engine.py`** — Core engine:
- `_DatastoreBuilder`: mutable accumulator during BFD, converts to frozen `DatastoreRecommendation` via `to_recommendation()`
- `_bfd_place()`: multi-dimensional BFD with oversized VM pre-separation (`_OVER_` datastores)
- `_apply_default_iops()`: workload-based IOPS injection using `dataclasses.replace()`
- `_compute_metrics()`: isolation score, snapshot granularity rating, oversized VM count
- `_consolidation_strategy()`: BFD-based DS minimization
- `generate_all_proposals()`: public entry point (consolidation only for now; Performance/Uniform in 14-02)

**`tests/test_layout_engine.py`** — 25 unit tests:
- `TestPlacementConstraints`: usable ratio/capacity, custom values
- `TestBFDPlace`: single VM, packing, capacity/IOPS/count overflow, oversized VM, empty list
- `TestConsolidationStrategy`: basic packing, DS_CONSOL_NN naming, LayoutProposal type check
- `TestComputeMetrics`: utilization, isolation score, snapshot granularity, empty list
- `TestDefaultIOPS`: SQL/Oracle/fallback/preserved IOPS, avg = 70% of peak

## Verification Results

- `ruff check` — clean (0 issues)
- `mypy` — clean (0 issues)
- `pytest tests/test_layout_engine.py` — 25 passed
- `pytest` (full suite) — 271 passed, 1 skipped, no regressions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed vm_count attribute reference in test**
- **Found during:** Task 2 test run
- **Issue:** `_DatastoreBuilder` has no `vm_count` attribute; must use `len(assigned_vms)`
- **Fix:** Changed `bins[0].vm_count == 1` to `len(bins[0].assigned_vms) == 1`
- **Files modified:** tests/test_layout_engine.py
- **Commit:** 1ba1834

**2. [Rule 2 - Lint] Applied ruff unsafe fix for TC001**
- **Found during:** Task 1 ruff check
- **Issue:** `VMCalculation` and `CalculationSummary` imports flagged as move-to-TYPE_CHECKING
- **Fix:** Applied `--unsafe-fixes` to move to TYPE_CHECKING blocks (safe because `from __future__ import annotations` makes all annotations lazy)
- **Files modified:** layout_models.py, layout_engine.py
- **Commit:** bc6850a

**3. [Rule 1 - Fix] Plan's expected usable_capacity_mib value was wrong**
- **Found during:** Task 1 import verification
- **Issue:** Plan stated "2,785,280 MiB" but formula (1-0.15) * (1-0.20) * 4 TiB = 2,852,127 MiB
- **Fix:** Implementation uses the correct formula per research Pattern 1; plan had a rounding/calculation error
- **No code change needed** — implementation is correct

## Decisions Made

- Used `TYPE_CHECKING` guard for `VMCalculation`/`CalculationSummary` imports — safe with `from __future__ import annotations`, avoids circular import risk
- Oversized VM datastores use `_OVER_` in name as the distinguishing marker (checked in both `_bfd_place` bin-skip logic and `_compute_metrics` oversized count)
- `generate_all_proposals()` currently returns only consolidation proposal; Performance and Uniform are scaffolded in Plan 14-02

## Self-Check: PASSED

Files created:
- FOUND: src/store_predict/pipeline/layout_models.py
- FOUND: src/store_predict/pipeline/layout_engine.py
- FOUND: tests/test_layout_engine.py

Commits:
- FOUND: bc6850a (feat(14-01): data models and consolidation strategy with BFD core)
- FOUND: 1ba1834 (test(14-01): unit tests for layout engine models, consolidation, metrics, IOPS)
