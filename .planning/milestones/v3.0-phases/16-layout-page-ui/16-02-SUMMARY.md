---
phase: 16-layout-page-ui
plan: "02"
subsystem: ui
tags: [nicegui, layout-page, detail-tabs, expandable-table, quasar-slots, vm-drilldown, i18n]
dependency_graph:
  requires:
    - phase: 16-01
      provides: /layout page with comparison table, _render_results() function, i18n ds.* keys
    - phase: 14-layout-engine-core
      provides: DatastoreRecommendation, LayoutProposal, assigned_vms
  provides:
    - Strategy detail tabs (Consolidation/Performance/Uniform) below comparison table
    - Expandable datastore rows with VM drill-down via props.expand
    - Utilization % color-coding (green/yellow/red) using Vue ternary class binding
    - Reactive rebuild covers both comparison and detail tabs
  affects:
    - src/store_predict/ui/pages/layout_page.py

tech-stack:
  added: []
  patterns:
    - ui.table with add_slot('header') and add_slot('body') for custom Quasar row rendering
    - props.expand for expandable rows (no ui.teleport, no ui.aggrid)
    - Raw strings r'''...''' for ALL Vue template content (avoids f-string/Vue {{ }} conflict)
    - Tab variables named tab_consol/tab_perf/tab_unif (avoids shadowing t() i18n import)
    - ui.tabs + ui.tab_panels + ui.tab_panel for strategy navigation

key-files:
  created: []
  modified:
    - src/store_predict/ui/pages/layout_page.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml

key-decisions:
  - "props.expand pattern used for expandable rows — not ui.teleport (DOM rebuilding issues) and not ui.aggrid (enterprise-only master-detail)"
  - "Utilization color logic embedded in full body slot template as ternary :class binding — no separate body-cell slot (would conflict with full body slot)"
  - "Tab variables named tab_consol/tab_perf/tab_unif to avoid shadowing the t() i18n import"
  - "detail_tabs_heading added as new i18n key (no interpolation) rather than reusing detail_heading which requires %{strategy} param"
  - "DatastoreRecommendation imported from layout_models for type annotation on _build_datastore_table()"

patterns-established:
  - "Quasar slot pattern: add_slot('header', r'''...''') adds expand-column header; add_slot('body', r'''...''') adds expand button + expanded VM list row"
  - "Raw string rule: ALL Vue template content in r'''...''' raw strings, never f-strings"
  - "Tab naming rule: never use variable t for loop variables in pages that import t() from i18n"

requirements-completed:
  - REQ-009

duration: 15min
completed: "2026-02-21"
---

# Phase 16 Plan 02: Layout Page UI — Strategy Detail Tabs Summary

**Three-tab detail view with ui.table + Quasar slots for expandable datastore rows, VM drill-down via props.expand, and utilization color-coding using Vue ternary class binding in body slot**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-21T00:00:00Z
- **Completed:** 2026-02-21T00:15:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Added `_build_datastore_table()` with custom Quasar `header` and `body` slots using raw strings; expandable rows via `props.expand`; utilization color-coding embedded directly in the body slot
- Added `_build_strategy_detail()` showing strategy description, 3 summary stat badges (DS count, total capacity, avg utilization), and the expandable datastore table (or "no datastores" message for empty proposals)
- Added `_build_strategy_tabs()` with Consolidation/Performance/Uniform tabs using tab variables `tab_consol`, `tab_perf`, `tab_unif` (avoiding `t` shadowing)
- Updated `_render_results()` to call `_build_strategy_tabs(proposals)` after comparison table — reactive rebuild now covers both views
- Added `detail_tabs_heading` i18n key to `en.yaml` and `fr.yaml`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add strategy tabs with expandable datastore tables and VM drill-down** - `62cec82` (feat)

## Files Created/Modified

- `src/store_predict/ui/pages/layout_page.py` — Added 4 new functions (~154 lines): `_build_datastore_table`, `_build_strategy_detail`, `_build_strategy_tabs`; updated `_render_results`; added `DatastoreRecommendation` import
- `src/store_predict/i18n/locales/en.yaml` — Added `layout_page.detail_tabs_heading: Strategy Detail`
- `src/store_predict/i18n/locales/fr.yaml` — Added `layout_page.detail_tabs_heading: Détail des stratégies`

## Decisions Made

1. **props.expand pattern for expandable rows.** Used `props.expand = !props.expand` in the Quasar body slot instead of `ui.teleport` (DOM rebuilding issues) or `ui.aggrid` master-detail (enterprise-only). The body slot pattern is the canonical NiceGUI/Quasar approach.

2. **Utilization color logic in body slot, not separate body-cell slot.** Since a full `body` slot is defined (for expand functionality), a separate `body-cell-util_pct` slot cannot be used — it would be overridden. The ternary `:class` binding handles green/yellow/red coloring within the same body slot template.

3. **Tab variable names: tab_consol, tab_perf, tab_unif.** The i18n import uses `t` as the function name. Any loop or tab variable named `t` would shadow it. Per project convention and plan specification, descriptive names are required.

4. **detail_tabs_heading as new i18n key.** The existing `detail_heading` key uses `%{strategy}` interpolation. Rather than calling `t()` with an argument or using a format string, a simpler static key was added for the section heading above the tabs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added DatastoreRecommendation to imports**
- **Found during:** Task 1 implementation
- **Issue:** `_build_datastore_table()` type annotation uses `DatastoreRecommendation` but it was not imported from `layout_models`
- **Fix:** Added `DatastoreRecommendation` to the import line alongside `LayoutProposal` and `PlacementConstraints`
- **Files modified:** `src/store_predict/ui/pages/layout_page.py`
- **Verification:** `mypy src/` — 0 issues
- **Committed in:** `62cec82` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added detail_tabs_heading i18n key**
- **Found during:** Task 1 implementation (heading above tabs required non-interpolated key)
- **Issue:** Plan referenced `layout_page.detail_heading` which uses `%{strategy}` interpolation — unsuitable for a static section heading
- **Fix:** Added `layout_page.detail_tabs_heading` as a new static key in both en.yaml and fr.yaml
- **Files modified:** `src/store_predict/i18n/locales/en.yaml`, `src/store_predict/i18n/locales/fr.yaml`
- **Verification:** `ruff check src/` — 0 issues; app uses the key correctly
- **Committed in:** `62cec82` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both missing critical for type correctness and i18n completeness)
**Impact on plan:** Both fixes required for correct operation. No scope creep.

## Issues Encountered

None — plan executed cleanly once the DatastoreRecommendation import and i18n key corrections were applied.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 16 complete: /layout page delivers REQ-007 through REQ-010 with full comparison + detail view
- Phase 17 (PDF export) can access layout data via `app.storage.tab` and `generate_all_proposals()`
- Phase 18 (i18n & Polish) can add tooltips; all page strings already go through `t()`

---

## Self-Check

**File existence:**

- FOUND: src/store_predict/ui/pages/layout_page.py (588 lines, min 250 required per plan)
- FOUND: 62cec82 commit (feat(16-02): add strategy detail tabs...)

**Structural verifications:**

- FOUND: `ui.tabs` in layout_page.py (line 382)
- FOUND: `props.expand` in layout_page.py (lines 304, 305, 323)
- FOUND: `vm_names` in layout_page.py (lines 279, 328)
- FOUND: `_build_strategy_tabs` function defined and called from `_render_results`

**Test results:** 297 passed, 1 skipped, 0 failures
**Ruff:** 0 issues
**Mypy:** 0 issues (45 source files)

## Self-Check: PASSED

*Phase: 16-layout-page-ui*
*Completed: 2026-02-21*
