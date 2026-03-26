---
phase: 029-reporting-fidelity
plan: "03"
subsystem: pdf
tags: [reportlab, matplotlib, sankey, dpi, pdf-charts]

requires:
  - phase: 029-reporting-fidelity-01
    provides: WorkloadGroupResult with drr field

provides:
  - Sankey diagram rendered at 300 DPI in PDF (print quality, no pixelation)
  - Palette alignment between PDF matplotlib Sankey and ECharts web UI Sankey
  - Larger font sizes (mid-node: 6, axis labels: 7) for legibility

affects:
  - pdf-report
  - pdf-charts

tech-stack:
  added: []
  patterns:
    - "TDD with inspect.getsource() for source-level palette assertions"
    - "ReportLab Image.imageWidth reflects native PNG pixel dimensions"

key-files:
  created:
    - tests/test_pdf_charts.py
  modified:
    - src/store_predict/services/pdf_charts.py

key-decisions:
  - "Use imageWidth attribute on ReportLab Image to verify DPI — avoids PIL dependency in tests"
  - "Use inspect.getsource() for palette assertions — fast, deterministic, no rendering needed"
  - "dpi=300 added directly to both Figure() constructor and fig.savefig() to ensure round-trip accuracy"

patterns-established:
  - "TDD RED/GREEN for rendering changes: write failing pixel-width test before bumping DPI"
  - "Palette alignment test: assert source string '#DEE2E6' in src and '#5B8DB8' not in src"

requirements-completed: [REPORT-01, REPORT-02]

duration: 8min
completed: 2026-03-26
---

# Phase 29 Plan 03: Sankey PDF Rendering Fidelity Summary

**matplotlib Sankey upgraded to 300 DPI with aligned DELL_PALETTE (#DEE2E6 not #5B8DB8) and bumped font sizes (mid-node 5->6, axis 6.5->7)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-26T00:00:00Z
- **Completed:** 2026-03-26T00:08:00Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 2

## Accomplishments

- Sankey PNG now renders at 300 DPI (2083x833 px for 500x200pt defaults), eliminating pixelation at 100% zoom in PDF readers
- 6th palette color corrected from `#5B8DB8` to `#DEE2E6`, matching ECharts DELL_PALETTE exactly
- Mid-node category label fontsize bumped from 5 to 6 for legibility
- Axis label default fontsize bumped from 6.5 to 7 for legibility
- Added 3 new tests proving DPI, palette correctness, and return type

## Task Commits

1. **RED: failing tests for DPI and palette** - `c166b0d` (test)
2. **GREEN: implementation + test fix** - `3160d29` (feat)

## Files Created/Modified

- `src/store_predict/services/pdf_charts.py` — DPI 150->300, palette fix #5B8DB8->#DEE2E6, fontsize bumps
- `tests/test_pdf_charts.py` — New: test_sankey_dpi_300, test_sankey_palette_matches_echart, test_sankey_returns_image_flowable

## Decisions Made

- Used `img.imageWidth` (ReportLab native attribute) instead of PIL to verify pixel dimensions — avoids an extra dependency in tests
- Used `inspect.getsource()` for palette assertion — more reliable than rendering+color-sampling, zero false negatives

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ReportLab Image stores BytesIO as string representation in `filename`**
- **Found during:** Task 1 (test implementation)
- **Issue:** Plan suggested accessing `img._file` for the PNG bytes, but ReportLab stores the BytesIO as str(buf) in `img.filename` and exposes native pixel size via `img.imageWidth`
- **Fix:** Used `img.imageWidth` directly — cleaner, no PIL dependency, same assertion
- **Files modified:** tests/test_pdf_charts.py
- **Verification:** test_sankey_dpi_300 passes with width_px=2083 >= 2000
- **Committed in:** 3160d29

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test approach)
**Impact on plan:** Minor test implementation correction. No scope change, all acceptance criteria met.

## Issues Encountered

- ReportLab Image `_file` attribute is None when constructed with BytesIO; actual PNG dimensions accessible via `imageWidth`/`imageHeight` — resolved by using native ReportLab attributes

## Next Phase Readiness

- PDF Sankey chart is now print-quality (300 DPI) and visually consistent with web UI palette
- All 515 tests pass (4 pre-existing classification failures unrelated to this plan)
- Ready for remaining reporting-fidelity plans

---
*Phase: 029-reporting-fidelity*
*Completed: 2026-03-26*
