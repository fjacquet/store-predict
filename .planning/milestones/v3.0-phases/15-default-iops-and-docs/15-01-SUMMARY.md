---
phase: 15-default-iops-and-docs
plan: "01"
subsystem: pipeline/layout-models
tags: [iops, csv, configurable-defaults, layout-engine, REQ-014]
dependency_graph:
  requires: [14-02]
  provides: [configurable-iops-defaults]
  affects: [layout_engine, layout_models]
tech_stack:
  added: [csv (stdlib), pathlib (stdlib)]
  patterns: [package-data-csv, csv-with-hardcoded-fallback]
key_files:
  created:
    - src/store_predict/data/IOPS.csv
  modified:
    - src/store_predict/pipeline/layout_models.py
    - tests/test_layout_engine.py
decisions:
  - IOPS.csv stored in src/store_predict/data/ alongside DRR.csv (package data, not samples/) — samples/ is gitignored for customer data privacy
  - _DEFAULT_IOPS_HARDCODED retained as private fallback for resilience when CSV is missing or corrupt
  - stdlib csv.DictReader used (not pandas) to keep layout_models.py lightweight with zero extra dependencies
metrics:
  duration: 258s
  completed: 2026-02-21
  tasks_completed: 2
  files_changed: 3
---

# Phase 15 Plan 01: IOPS CSV Configurability Summary

IOPS defaults are now loaded from `src/store_predict/data/IOPS.csv` at module import time using a CSV-backed loader with a hardcoded fallback, matching the DRR.csv configuration pattern.

## What Was Built

### Task 1: Create IOPS.csv and refactor layout_models.py

Created `src/store_predict/data/IOPS.csv` with 8 workload categories in semicolon-delimited format, stored alongside `DRR.csv` in the package data directory. Refactored `layout_models.py` to:

- Rename existing dict to `_DEFAULT_IOPS_HARDCODED` (private fallback)
- Add `_IOPS_CSV_PATH` pointing to package data location
- Add `_load_iops_from_csv(path)` that reads the CSV, strips whitespace, skips bad rows, and falls back to hardcoded if missing/empty
- Replace module-level `DEFAULT_IOPS_BY_WORKLOAD = {...}` with `DEFAULT_IOPS_BY_WORKLOAD = _load_iops_from_csv()`

### Task 2: Add tests for CSV loader

Added `TestLoadIOPSFromCSV` class to `tests/test_layout_engine.py` with 5 tests covering:
- Real CSV loading returns 8+ entries with correct values
- Fallback when path doesn't exist
- Whitespace stripping on keys and values
- Skipping rows with non-numeric IOPS values
- Empty file (header-only) uses fallback

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] IOPS.csv path corrected from samples/ to src/store_predict/data/**

- **Found during:** Task 1 commit attempt
- **Issue:** Plan specified `samples/IOPS.csv` but the `samples/` directory is gitignored to protect customer data. DRR.csv (the established pattern) is stored at `src/store_predict/data/DRR.csv`, not in `samples/`.
- **Fix:** Created IOPS.csv at `src/store_predict/data/IOPS.csv` and updated `_IOPS_CSV_PATH` to use 2 `.parent` calls from `layout_models.py` to reach `store_predict/data/`.
- **Files modified:** `src/store_predict/pipeline/layout_models.py`
- **Commit:** `917928d`

## Verification

- `pytest tests/test_layout_engine.py -v` — 51 tests pass (46 existing + 5 new)
- `ruff check` — clean
- `mypy src/store_predict/pipeline/layout_models.py` — clean
- `python -c "from store_predict.pipeline.layout_models import DEFAULT_IOPS_BY_WORKLOAD; print(len(DEFAULT_IOPS_BY_WORKLOAD))"` — prints 8
- Full suite: 297 tests pass

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | `917928d` | feat(15-01): add IOPS.csv package data and CSV loader for configurable IOPS defaults |
| 2    | `799df68` | test(15-01): add TestLoadIOPSFromCSV tests for CSV loader, fallback, whitespace, bad rows |
