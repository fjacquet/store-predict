---
phase: 16-layout-page-ui
plan: "01"
subsystem: ui
tags: [nicegui, layout-page, comparison-view, settings-panel, i18n, navigation]
dependency_graph:
  requires:
    - phase-14-layout-engine-core  # layout_engine.py + layout_models.py
    - phase-15-default-iops-and-docs  # IOPS defaults, pipeline complete
  provides:
    - /layout route registered
    - 3-strategy comparison view
    - advanced settings panel (5 controls)
    - reactive layout re-generation
    - navigation bar Layout link
  affects:
    - src/store_predict/ui/layout.py  # nav bar updated
    - src/store_predict/main.py  # route registered
    - src/store_predict/i18n/locales/en.yaml  # 40 new keys
    - src/store_predict/i18n/locales/fr.yaml  # 40 new keys
tech_stack:
  added: []
  patterns:
    - ui.page decorator for route registration
    - ui.expansion for collapsible settings panel
    - ui.table for comparison grid (not ui.aggrid)
    - ui.slider with bind_text_from for live value display
    - ui.select with dict options for capacity dropdown
    - app.storage.tab for session state persistence
    - container.clear() + rebuild pattern for reactive updates
key_files:
  created:
    - src/store_predict/ui/pages/layout_page.py
  modified:
    - src/store_predict/ui/layout.py
    - src/store_predict/main.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
decisions:
  - Settings panel built before results_container in code but rendered after (container reference passed as closure)
  - tb_options (lowercase) used for DS capacity dict (ruff N806 compliance)
  - Slider on("change") event used instead of on_change parameter for correct NiceGUI event wiring
  - Recommended strategy: isolation_score > 0.5 -> performance; single workload -> consolidation; else -> uniform
  - SIM117 auto-fixed: ui.expansion + ui.column combined in single with statement
metrics:
  duration_seconds: 284
  completed_date: "2026-02-21"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 4
---

# Phase 16 Plan 01: Layout Page UI — Comparison View and Settings Panel

NiceGUI /layout page with 3-strategy comparison table, green-badged recommended strategy indicator, 5-control Advanced Settings panel, reactive re-generation via container.clear() + rebuild, and nav bar integration.

## What Was Built

### layout_page.py (src/store_predict/ui/pages/layout_page.py)

New NiceGUI page module (448 lines) implementing:

- `@ui.page("/layout")` async function with `await ui.context.client.connected()`
- Empty-state guard: checks `app.storage.tab.get("vm_data")` — shows `grid_view` icon card with upload redirect if None
- `_load_constraints()` / `_save_constraints()` helpers reading 5 keys from `app.storage.tab`
- `_build_settings_panel()`: `ui.expansion` with 5 controls:
  - `ui.select` for Max DS Capacity (2/4/8/16/32/64 TB options)
  - `ui.slider` (5-50) for Max VMs/DS with live label bound via `bind_text_from`
  - `ui.number` for IOPS Budget per DS
  - `ui.slider` (0-30%) for Snapshot Reserve
  - `ui.slider` (0-40%) for Growth Margin
- `_build_comparison_table()`: strategy summary cards (3-col grid) with green badge for recommended, plus full `ui.table` with 15 metric rows
- `_recommend_strategy()`: isolation_score > 0.5 → performance; single workload → consolidation; else → uniform
- `_rebuild_layout()`: recalculates from tab vm_data + saves constraints → clears container → re-renders
- Results container pattern: `ui.column` held as closure reference, passed to settings panel callbacks

### Navigation and Route Registration

- `src/store_predict/ui/layout.py`: Added `ui.link(t("layout.layout"), "/layout")` after Report link
- `src/store_predict/main.py`: Added `import store_predict.ui.pages.layout_page` for route registration

### i18n Keys (40 new keys)

Added to both `en.yaml` and `fr.yaml`:
- `layout.layout` — nav link label
- `layout_page.*` — 12 page-level keys (title, no_data, settings panel, controls, metric column header, recommended badge, headings)
- `strategy.*` — 6 keys (consolidation, performance, uniform + _desc variants)
- `metrics.*` — 15 keys (all LayoutMetrics fields)
- `ds.*` — 8 keys (for detail table in plan 16-02)

## Verification Results

| Check | Result |
|-------|--------|
| `ruff check src/` | 0 issues |
| `mypy src/` | 0 issues (45 files) |
| `pytest tests/` | 297 passed, 1 skipped |
| Nav link in layout.py | `t("layout.layout")` -> `/layout` |
| Route in main.py | `import store_predict.ui.pages.layout_page` |
| i18n keys en.yaml | 40 keys added |
| i18n keys fr.yaml | 40 keys added (French translations) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] N806: TB_OPTIONS renamed to tb_options**
- **Found during:** Task 1 verification (ruff check)
- **Issue:** Variable `TB_OPTIONS` in function violates PEP 8 lowercase convention for local variables
- **Fix:** Renamed to `tb_options` (lowercase)
- **Files modified:** src/store_predict/ui/pages/layout_page.py
- **Commit:** 590ec00

**2. [Rule 1 - Lint] SIM117: Nested with statements combined**
- **Found during:** Task 1 verification (ruff check)
- **Issue:** `with ui.expansion(...): with ui.column():` is two nested contexts that can be one
- **Fix:** Auto-fixed by `ruff --fix` to single `with ... , ...:` statement
- **Files modified:** src/store_predict/ui/pages/layout_page.py
- **Commit:** 590ec00

**3. [Rule 1 - Lint] RUF100: Unused noqa directive removed**
- **Found during:** Task 1 verification (ruff check)
- **Issue:** `# noqa: F401` on layout_page import was unnecessary (import IS used for side effects via module-level `@ui.page` decorator)
- **Fix:** Removed the noqa comment; ruff correctly determined the import is not "unused" in the F401 sense
- **Files modified:** src/store_predict/main.py
- **Commit:** 590ec00

**4. [Rule 1 - Lint] I001: Import block re-sorted**
- **Found during:** Task 1 verification (ruff check)
- **Issue:** Import ordering violated isort conventions
- **Fix:** Auto-fixed by `ruff --fix`
- **Files modified:** src/store_predict/ui/pages/layout_page.py
- **Commit:** 590ec00

## Decisions Made

1. **Settings panel built before results_container in code flow, but receives container as closure parameter.** The results_container is created first in the page function, then passed to `_build_settings_panel()`. This ensures the reactive re-generation target exists when callbacks are registered.

2. **Slider `on("change")` event wiring.** Used `.on("change", handler)` instead of `on_change=handler` parameter to match how NiceGUI events work for sliders (fires on release, not every pixel during drag).

3. **Recommended strategy heuristic.** The plan specified: isolation_score > 0.5 → performance; single workload → consolidation; else → uniform. Implemented exactly as specified — this provides a defensible recommendation for pre-sales engineers.

4. **ds.* i18n keys added now.** Although `ds.*` keys are primarily used in plan 16-02 (Detail View), they were added here alongside the other i18n sections to keep translation work in one commit.

## Self-Check: PASSED

- FOUND: src/store_predict/ui/pages/layout_page.py (436 lines, min 150 required)
- FOUND: src/store_predict/ui/layout.py (with Layout nav link)
- FOUND: src/store_predict/main.py (with layout_page import)
- FOUND commit: 590ec00 (feat(16-01): create /layout page)
- All tests: 297 passed, 1 skipped, 0 failures
- Ruff: 0 issues
- Mypy: 0 issues (45 files)
