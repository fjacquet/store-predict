---
phase: 19-batch-llm-classification
plan: 02
subsystem: testing, docs
tags: [i18n, performance-test, layout-engine, tech-debt]

# Dependency graph
requires:
  - phase: 18-i18n-and-polish
    provides: tooltip i18n keys that were orphaned (iops_headroom, snapshot_rating)
  - phase: 15-default-iops-and-docs
    provides: IOPS.csv path references in docs (already corrected by prior commit)
  - phase: 14-layout-engine-core
    provides: generate_all_proposals() function benchmarked by NFR-001 test
provides:
  - Cleaned tooltip i18n keys (no orphaned entries in en.yaml/fr.yaml)
  - NFR-001 layout engine benchmark test (1000 VMs under 2s)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Performance benchmark pattern: build row_data dicts, calculate(), then time generate_all_proposals()"

key-files:
  created: []
  modified:
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - tests/test_ux_polish.py
    - tests/test_performance.py

key-decisions:
  - "IOPS.csv path fixes already applied in prior commit 02609f6 -- no docs changes needed"
  - "Orphaned tooltip keys deleted rather than wired -- ui.table limitation makes per-cell tooltips impossible"

patterns-established:
  - "Layout engine benchmarks use calculate() to build CalculationSummary from synthetic row_data"

requirements-completed: [TD-A, TD-B, TD-C]

# Metrics
duration: 22min
completed: 2026-02-21
---

# Phase 19 Plan 02: Tech Debt Cleanup Summary

**Deleted orphaned tooltip.iops_headroom and tooltip.snapshot_rating i18n keys; added NFR-001 layout engine benchmark test (1000 VMs, 3 strategies, under 2s)**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-21T11:41:35Z
- **Completed:** 2026-02-21T12:03:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Removed orphaned tooltip.iops_headroom and tooltip.snapshot_rating from en.yaml, fr.yaml, and test_ux_polish.py
- Added TestLayoutEnginePerformance class with NFR-001 benchmark (1000 VMs across 8 workload categories)
- Confirmed IOPS.csv doc path fixes were already applied in prior commit 02609f6

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix stale IOPS.csv paths and delete orphaned i18n keys** - `9863db7` (fix)
2. **Task 2: Add NFR-001 layout engine benchmark test** - `5899228` (test)

## Files Created/Modified
- `src/store_predict/i18n/locales/en.yaml` - Removed orphaned tooltip.iops_headroom and tooltip.snapshot_rating
- `src/store_predict/i18n/locales/fr.yaml` - Removed orphaned tooltip.iops_headroom and tooltip.snapshot_rating
- `tests/test_ux_polish.py` - Removed deleted keys from PHASE_18_KEYS parametrized list
- `tests/test_performance.py` - Added TestLayoutEnginePerformance with NFR-001 benchmark

## Decisions Made
- IOPS.csv path fixes were already applied by commit 02609f6 (fix(docs): correct IOPS.csv path from samples/ to src/store_predict/data/), so no doc changes were needed in this plan
- Orphaned tooltip keys deleted (not wired) because ui.table does not support per-cell tooltips -- these metrics appear as table rows, not standalone UI controls

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] IOPS.csv paths already fixed -- skipped TD-A doc edits**
- **Found during:** Task 1 (IOPS.csv path verification)
- **Issue:** Plan expected 4 docs files to contain stale `samples/IOPS.csv` paths, but commit 02609f6 already corrected them
- **Fix:** Verified all 4 files already have correct `src/store_predict/data/IOPS.csv` paths; no edits needed
- **Verification:** `command grep -rn "samples/IOPS.csv" docs/ CHANGELOG.md` returns nothing

---

**Total deviations:** 1 (TD-A already resolved by prior commit)
**Impact on plan:** No functional impact. The verification confirms the correct state.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All tech debt items resolved
- 61 tests pass across test_ux_polish.py and test_performance.py
- Ready for Phase 19 Plan 01 (batch LLM classification) if not yet executed

---
*Phase: 19-batch-llm-classification*
*Completed: 2026-02-21*
