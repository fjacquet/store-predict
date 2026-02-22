---
phase: 20-grid-ux-vm-data-columns
plan: "01"
subsystem: pipeline/ui
tags: [row-identity, ag-grid, ingestion, parsers, bug-fix]
dependency_graph:
  requires: []
  provides: [stable-row-index, ag-grid-row-id]
  affects: [vm_table, review_page, all_parsers, ingestion]
tech_stack:
  added: []
  patterns: [two-step-placeholder-assignment, int-cast-safety]
key_files:
  created: []
  modified:
    - src/store_predict/pipeline/parsers/columns.py
    - src/store_predict/pipeline/parsers/rvtools.py
    - src/store_predict/pipeline/parsers/liveoptics.py
    - src/store_predict/pipeline/ingestion.py
    - src/store_predict/ui/components/vm_table.py
    - src/store_predict/ui/pages/review.py
decisions:
  - "Two-step placeholder approach: parsers set row_index=0, ingest_file overwrites with contiguous int after reset_index"
  - "String() wrapper in getRowId is explicit and safe for AG Grid row ID requirement"
  - "int() casts on both sides of comparisons to prevent float/int mismatch from JSON round-trips"
metrics:
  duration: "~3 minutes"
  completed: "2026-02-22"
  tasks_completed: 2
  files_modified: 6
---

# Phase 20 Plan 01: AG Grid Row Identity Fix (row_index) Summary

**One-liner:** Switched AG Grid getRowId from vm_name to a stable integer row_index column, eliminating row identity corruption for customer files with duplicate VM names (linked clones, template copies).

## What Was Done

Added a stable `row_index` column throughout the ingestion pipeline and updated the AG Grid component to use it as the row identity key instead of vm_name.

### Task 1: Register row_index in CANONICAL_COLUMNS and assign in ingestion

- Appended `"row_index"` to `CANONICAL_COLUMNS` list in `columns.py`
- Added `result["row_index"] = 0` placeholder in `rvtools.py` before `return result[CANONICAL_COLUMNS]`
- Added `result["row_index"] = 0` placeholder in both return paths in `liveoptics.py` (`_build_liveoptics_df` and `parse_liveoptics_xlsx`)
- Added `df["row_index"] = df.index.astype(int)` in `ingest_file` after template filtering and `reset_index`

**Commit:** 57c9de9

### Task 2: Switch getRowId and update both cell-change handlers atomically

- Changed `":getRowId"` in `vm_table.py` from `params.data.vm_name` to `String(params.data.row_index)`
- Updated `_handle_cell_change` drr branch: replaced `vm_name` equality check with `int(row_index)` comparison
- Updated `_handle_cell_change` workload_category branch: same row_index switch
- Updated `_handle_bulk_update`: replaced `selected_names` string set with `selected_ids` integer set
- No `vm_name` equality comparisons remain in row-lookup code paths

**Commit:** 29f0f4b

## Decisions Made

1. **Two-step placeholder approach** — Parsers set `row_index=0` as a placeholder so the `CANONICAL_COLUMNS` whitelist filter does not strip the column. The real contiguous 0..N-1 value is assigned in `ingest_file` after template filtering and `reset_index`. This guarantees contiguous unique values regardless of any internal filtering done by individual parsers.

2. **`String()` wrapper in getRowId** — AG Grid's getRowId callback must return a string. Integer row_index values would be coerced but `String()` makes it explicit and safe against edge cases.

3. **`int()` casts on both sides of comparisons** — JSON round-trips can produce float64 integers in Python dicts. Casting both sides prevents silent float/int mismatch bugs in row matching.

## Test Results

- 351 tests pass, 1 skipped
- 2 pre-existing failures in `test_llm_classifier.py` (unrelated to this plan, confirmed to fail on original code)
- All ingestion, parser, liveoptics performance, and UX tests pass

## Deviations from Plan

None — plan executed exactly as written. The two-step approach described in the plan was implemented as specified.

## Deferred Issues

**Pre-existing test failures (out of scope):**

- `tests/test_llm_classifier.py::test_llm_config_max_concurrent_default` — asserts `max_concurrent == 5`, actual value is `1` (LLM config default mismatch, pre-existed before this plan)
- `tests/test_llm_classifier.py::test_llm_config_timeout_default` — similar pre-existing assertion mismatch

These failures existed before this plan and are unrelated to row_index changes.

## Self-Check: PASSED

All key files found. All task commits verified:

- 57c9de9: Task 1 commit (columns, parsers, ingestion)
- 29f0f4b: Task 2 commit (vm_table, review)
