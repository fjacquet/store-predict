---
phase: 05-calculation-pdf-report
plan: 01
subsystem: pipeline
tags: [dataclasses, calculation, drr, sizing]

requires:
  - phase: 03-classification
    provides: classified VM row dicts with workload_category and drr fields
provides:
  - CalculationSummary with per-VM required capacity, workload group subtotals, grand totals
  - calculate() function consuming row dicts from session state
affects: [05-02, 05-03, ui-review-page]

tech-stack:
  added: []
  patterns: [frozen dataclasses for immutable results, defaultdict grouping, weighted average DRR]

key-files:
  created:
    - src/store_predict/pipeline/calculation.py
    - tests/test_calculation.py
  modified:
    - src/store_predict/pipeline/__init__.py

key-decisions:
  - "DRR guard uses max(drr, 0.1) to prevent division by zero while preserving near-zero intent"
  - "Weighted avg DRR = total_provisioned / total_required (not simple average of per-VM DRRs)"
  - "Missing fields use .get() defaults: provisioned=0, in_use=0, drr=5.0, category=Unknown (Reducible)"

patterns-established:
  - "Frozen dataclasses for calculation results (immutable, safe to share)"
  - "Pure function calculate() with no side effects or UI imports"

requirements-completed: [FR-5.1, FR-5.2, FR-5.3]

duration: 3min
completed: 2026-02-19
---

# Phase 5 Plan 1: Calculation Service Summary

**Pure calculation service with frozen dataclasses computing per-VM required capacity, workload group subtotals, and weighted average DRR**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T05:15:22Z
- **Completed:** 2026-02-19T05:18:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 12 TDD tests covering single VM, multiple VMs, weighted avg, grouping, edge cases (zero/negative DRR, empty data, missing fields, 5000 VMs)
- Calculation service with 3 frozen dataclasses (VMCalculation, WorkloadGroupResult, CalculationSummary)
- 100% code coverage on calculation.py, ruff clean, mypy clean
- Zero UI imports -- pure pipeline module

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- Write failing tests** - `76b2d66` (test)
2. **Task 2: GREEN -- Implement calculation service** - `c2c03ae` (feat)

## Files Created/Modified
- `src/store_predict/pipeline/calculation.py` - Calculation service with dataclasses and calculate()
- `tests/test_calculation.py` - 12 test cases for all edge cases
- `src/store_predict/pipeline/__init__.py` - Re-exports calculation symbols

## Decisions Made
- DRR guard uses max(drr, 0.1) -- prevents ZeroDivisionError while keeping near-zero behavior visible
- Weighted avg DRR computed as total_provisioned / total_required (physically meaningful ratio)
- Missing field defaults match session state conventions (drr=5.0 = Unknown Reducible default)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- calculate() ready for integration with review page UI
- CalculationSummary provides all data needed for PDF report generation (Plan 05-02, 05-03)
- 94 total tests pass with no regressions

---
*Phase: 05-calculation-pdf-report*
*Completed: 2026-02-19*
