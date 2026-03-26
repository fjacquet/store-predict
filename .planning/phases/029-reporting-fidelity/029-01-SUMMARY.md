---
phase: 029-reporting-fidelity
plan: 01
subsystem: calculation
tags: [drr, groupby, calculation, echarts, sankey, reporting]

# Dependency graph
requires: []
provides:
  - WorkloadGroupResult.drr field (default=0.0, backward compat)
  - calculate() groups by (category, drr) tuple
  - ECharts Sankey unique node names with DRR suffix on collision
affects:
  - pdf_report (iterates workload_groups verbatim)
  - excel_report (iterates workload_groups verbatim)
  - charts (echart_sankey_options)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Group by (category, drr) tuple to produce separate rows for same-category different-DRR VMs"
    - "Collision-safe Sankey nodes: append (X.Xx) DRR suffix only when category appears multiple times"

key-files:
  created:
    - tests/test_calculation.py (TestDRRSplit class added)
  modified:
    - src/store_predict/pipeline/calculation.py
    - src/store_predict/services/charts.py

key-decisions:
  - "Group key changed from category string to (category, drr) tuple — uniform DRR within each group enables avg_drr == drr_val"
  - "WorkloadGroupResult.drr uses default=0.0 so all existing 7 call sites in tests work unchanged"
  - "Sankey node names: DRR suffix only on collision, bare category names otherwise (no visual clutter for common case)"

patterns-established:
  - "Pattern 1: (category, drr) groupby key — future callers should use grp.drr not grp.avg_drr for DRR value"
  - "Pattern 2: Counter-based collision detection for Sankey nodes"

requirements-completed: [DRR-01, DRR-02, DRR-03]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 29 Plan 01: DRR Category Split Summary

**(category, drr) groupby key in calculate() produces separate WorkloadGroupResult rows per DRR variant, with collision-safe ECharts Sankey node names**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T13:00:35Z
- **Completed:** 2026-03-26T13:05:47Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- WorkloadGroupResult now carries a `drr: float = 0.0` field with backward compatibility
- calculate() groups by `(category, drr)` tuple so same-category VMs with different DRR values appear as separate rows in all report surfaces (web UI table, PDF, Excel)
- ECharts Sankey uses `_node_name()` helper that appends `(X.Xx)` DRR suffix only when the same category appears with different DRR values, avoiding node collisions without adding visual clutter in the common case
- TDD: RED commit (4 failing tests) followed by GREEN commit (all 16 tests pass)

## Task Commits

Each task was committed atomically:

1. **TDD RED: failing TestDRRSplit tests** - `1648fa9` (test)
2. **Task 1: drr field + groupby key fix** - `ad7d3c7` (feat)
3. **Task 2: ECharts Sankey collision fix** - `09b4581` (feat)

_Note: TDD task has separate test commit (RED) and implementation commit (GREEN)_

## Files Created/Modified
- `src/store_predict/pipeline/calculation.py` - Added `drr: float = 0.0` to WorkloadGroupResult; changed groupby key from `category` to `(category, drr)` tuple
- `src/store_predict/services/charts.py` - Added Counter-based collision detection and `_node_name()` helper for unique Sankey node names
- `tests/test_calculation.py` - Added TestDRRSplit class with 4 tests proving split behavior and backward compat

## Decisions Made
- Group key `(category, drr)` tuple rather than category alone — within each group all VMs share the same DRR, making `avg_drr == drr_val` by construction
- `drr` field appended at end of WorkloadGroupResult (after `total_required_mib`) with default=0.0 to avoid breaking 7 existing test call sites that use keyword args
- Sankey node name collision guard: DRR suffix only on collision prevents label noise for the common single-DRR-per-category case

## Deviations from Plan

None - plan executed exactly as written.

Pre-existing failure noted: `tests/test_pdf_charts.py::TestSankeyImageFlowable::test_sankey_dpi_300` was already failing before this plan's changes (confirmed by git stash test). Out of scope per deviation scope boundary rule; logged here for visibility.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DRR groupby fix is complete; plans 029-02 and 029-03 can build on the updated WorkloadGroupResult
- PDF and Excel reports will automatically show separate rows for each DRR variant since they iterate `workload_groups` verbatim
- The pre-existing `test_sankey_dpi_300` failure should be addressed in a separate remediation

## Self-Check: PASSED

All files present:
- FOUND: src/store_predict/pipeline/calculation.py
- FOUND: src/store_predict/services/charts.py
- FOUND: tests/test_calculation.py
- FOUND: .planning/phases/029-reporting-fidelity/029-01-SUMMARY.md

All commits present:
- FOUND: 1648fa9 (TDD RED)
- FOUND: ad7d3c7 (Task 1 GREEN)
- FOUND: 09b4581 (Task 2)

---
*Phase: 029-reporting-fidelity*
*Completed: 2026-03-26*
