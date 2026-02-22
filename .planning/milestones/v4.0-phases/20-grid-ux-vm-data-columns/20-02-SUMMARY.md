---
phase: 20-grid-ux-vm-data-columns
plan: "02"
subsystem: ui/components
tags: [ag-grid, quick-filter, column-toggle, i18n, nicegui, ux]
dependency_graph:
  requires: [20-01]
  provides: [quick-filter-search, column-visibility-toggle, hidden-vm-columns]
  affects: [vm_table, review_page, en_yaml, fr_yaml]
tech_stack:
  added: []
  patterns: [ag-grid-setGridOption, ag-grid-setColumnsVisible, nicegui-expansion, default-closure-capture]
key_files:
  created: []
  modified:
    - src/store_predict/ui/components/vm_table.py
    - src/store_predict/ui/pages/review.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
decisions:
  - "Toolbar placed after grid assignment so closures reference valid variable name (Python captures name, not value)"
  - "hide:True used instead of initialHide:True for reliable toggling with setColumnsVisible"
  - "toggleable_columns named in lowercase to satisfy ruff N806 (not a module-level constant)"
  - "AG Grid sidebar skipped as Enterprise-only — custom NiceGUI checkbox expansion used instead"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-22"
  tasks_completed: 2
  files_modified: 4
---

# Phase 20 Plan 02: Quick-Filter Search Box and Column Visibility Toggle Summary

**One-liner:** Added AG Grid quickFilterText search input and custom NiceGUI column-toggle expansion panel above the VM review grid, with four hidden column defs (num_cpus, memory_mib, avg_iops, peak_iops) and full French/English i18n coverage.

## What Was Done

Extended the VM review page with two UX features that allow pre-sales engineers to quickly search large VM lists (100-400+ VMs) and optionally reveal CPU/RAM/IOPS hardware metrics on demand.

### Task 1: Hidden column defs for CPU/RAM/IOPS in vm_table.py

- Appended four hidden column definitions to `column_defs` in `create_vm_table`:
  - `num_cpus` — vCPU count, `hide: True`, `agNumberColumnFilter`, em-dash null formatter
  - `memory_mib` — RAM in MiB, `hide: True`, `agNumberColumnFilter`, rounded formatter
  - `avg_iops` — Average IOPS, `hide: True`, `agNumberColumnFilter`, rounded formatter
  - `peak_iops` — Peak IOPS, `hide: True`, `agNumberColumnFilter`, rounded formatter
- No `sideBar` key added (Enterprise-only feature omitted per research findings)
- `hide: True` chosen over `initialHide: True` for reliable state management with `setColumnsVisible`

**Commit:** d4dedbf

### Task 2: Quick-filter input, column-toggle panel, and i18n keys

**i18n (en.yaml and fr.yaml):**

- Added `columns.num_cpus`, `columns.memory_mib`, `columns.avg_iops` to both locale files
- Added `review.search_placeholder`, `review.column_panel_title`, `review.column_panel_tip` to both locale files
- Added `tooltip.quick_filter` to both locale files
- `columns.peak_iops` already existed — not duplicated

**review.py:**

- Added `_on_quick_filter(e, grid)` async function at module level, calling `run_grid_method("setGridOption", "quickFilterText", ...)`
- Added toolbar `ui.row` with:
  - `ui.input` with clearable/dense/outlined style, search icon, and tooltip
  - `ui.expansion` collapsible panel with four `ui.checkbox` items for toggling `num_cpus`, `memory_mib`, `avg_iops`, `peak_iops` visibility via `run_grid_method("setColumnsVisible", [field], bool)`
- Toolbar placed after `grid = create_vm_table(...)` so variable is in scope for closures
- Default capture `f: str = _field` in inner async function prevents loop variable aliasing

**Deviation auto-fixed (Rule 3):** Ruff N806 error — renamed `TOGGLEABLE_COLUMNS` to `toggleable_columns` (local variable must not use uppercase constant naming convention).

**Commit:** 33be046

## Decisions Made

1. **Toolbar placed after grid assignment** — NiceGUI renders elements in declaration order but fires callbacks after full page build. Python lambdas and nested functions capture the variable name (not its value), so placing the toolbar after `grid = create_vm_table(...)` ensures the variable is in scope by the time any callback executes.

2. **`hide: True` vs `initialHide: True`** — Research from 20-RESEARCH.md confirms `hide: True` is reliable for both initial hidden state and subsequent `setColumnsVisible` toggling. `initialHide: True` only affects initial render.

3. **`toggleable_columns` lowercase** — Ruff enforces N806 (variable in function must not be uppercase). Renamed from `TOGGLEABLE_COLUMNS` to `toggleable_columns` to satisfy linter without disabling rules.

4. **Custom expansion panel over AG Grid sidebar** — AG Grid column sidebar is Enterprise-only (confirmed in research). Custom `ui.expansion` with `ui.checkbox` items is the correct Community-edition approach.

## Test Results

- 351 tests pass, 1 skipped
- 2 pre-existing failures in `test_llm_classifier.py` (unrelated to this plan, pre-existed before Phase 20)
- mypy: no issues found in 45 source files
- ruff: all checks passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff N806 uppercase variable name in function**

- **Found during:** Task 2 verification
- **Issue:** `TOGGLEABLE_COLUMNS: list[tuple[str, str]] = [...]` inside `review_page()` triggered ruff N806 (variable in function must not be named as if it were a module-level constant)
- **Fix:** Renamed to `toggleable_columns` (lowercase)
- **Files modified:** `src/store_predict/ui/pages/review.py`
- **Commit:** 33be046 (included in same commit)

## Self-Check: PASSED

All key files verified:

- `src/store_predict/ui/components/vm_table.py` — exists, contains 4 `"hide": True` entries
- `src/store_predict/ui/pages/review.py` — exists, contains `setGridOption` and `setColumnsVisible`
- `src/store_predict/i18n/locales/en.yaml` — exists, contains `search_placeholder`
- `src/store_predict/i18n/locales/fr.yaml` — exists, contains `search_placeholder`

Task commits verified:

- d4dedbf: Task 1 commit (vm_table.py hidden columns)
- 33be046: Task 2 commit (review.py toolbar + i18n keys)
