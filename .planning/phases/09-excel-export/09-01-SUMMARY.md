---
phase: 09-excel-export
plan: "01"
subsystem: reporting
tags: [xlsxwriter, xlsx, excel, i18n, pdf-report-mirror]

requires:
  - phase: 08-i18n-foundation
    provides: "i18n YAML infrastructure (en.yaml/fr.yaml) and t() helper for locale-aware strings"
  - phase: 05-reports
    provides: "CalculationSummary dataclass and pdf_report.py pattern to mirror"

provides:
  - "generate_report_xlsx() pure function returning in-memory .xlsx bytes"
  - "18 excel.* i18n keys in both en.yaml and fr.yaml for sheet names and column headers"
  - "xlsxwriter mypy override in pyproject.toml"

affects:
  - "09-02 (upload/report UI integration — will call generate_report_xlsx)"

tech-stack:
  added: ["xlsxwriter 3.2.9 (already installed, now configured for mypy)"]
  patterns:
    - "Module-level import of store_predict.i18n ensures YAML load_path configured before _i18n.t() calls"
    - "_i18n.set('locale', locale) at function entry + direct _i18n.t() bypasses NiceGUI session locale wrapper"
    - "BytesIO + in_memory: True Workbook option for zero-disk-touch report generation"
    - "buf.getvalue() after wb.close() pattern (not buf.read())"
    - "ws.autofit() as final call after freeze_panes on each worksheet"

key-files:
  created:
    - "src/store_predict/services/excel_report.py — generate_report_xlsx() pure function, 3-sheet xlsx"
  modified:
    - "pyproject.toml — [[tool.mypy.overrides]] for xlsxwriter.*"
    - "src/store_predict/i18n/locales/en.yaml — excel: section with 18 keys"
    - "src/store_predict/i18n/locales/fr.yaml — excel: section with French translations"

key-decisions:
  - "Use _i18n.t() directly (not store_predict.i18n.t() wrapper) so locale set at function entry is respected; wrapper overrides with NiceGUI session locale which returns 'fr' outside NiceGUI context"
  - "Import store_predict.i18n at module level (noqa: F401) to ensure YAML load_path configured before first _i18n.t() call"
  - "Three sheets mirror CalculationSummary structure: Summary (label-value), Workload Breakdown (grouped), VM Detail (per-VM)"
  - "Performance columns/rows gated on has_performance_data flag — absent when LiveOptics/RVTools has no IOPS data"

patterns-established:
  - "Excel service mirrors pdf_report.py shape: same locale param, same BytesIO, same TYPE_CHECKING import"
  - "Alternate row colouring: even body rows get alt_fmt (#f0f0f0), odd rows use default (None)"

requirements-completed: [XLSX-02, XLSX-03, XLSX-04, XLSX-05]

duration: 8min
completed: 2026-02-20
---

# Phase 09 Plan 01: Excel Report Service Summary

**XlsxWriter three-sheet .xlsx report generator with brand styling, freeze panes, autofit, and locale-aware labels via direct _i18n.t() bypassing NiceGUI session wrapper**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20T08:05:56Z
- **Completed:** 2026-02-20T08:13:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `generate_report_xlsx(summary, project_name, locale) -> bytes` pure function producing valid .xlsx PK ZIP output
- Three styled sheets: Summary (label-value metrics), Workload Breakdown (category subtotals + totals row), VM Detail (per-VM row with optional performance columns)
- Brand blue (#1e3a5f) header row with white bold text, freeze panes at row 1, autofit columns on all sheets
- 18 new `excel.*` i18n keys in both en.yaml and fr.yaml; EN and FR outputs verified to differ in bytes
- mypy override for `xlsxwriter.*` suppresses import-untyped errors; mypy strict passes on all 35 source files

## Task Commits

Each task was committed atomically:

1. **Task 1: Add xlsxwriter mypy override and excel i18n keys** - `f0906a7` (chore)
2. **Task 2: Implement excel_report.py service module** - `4055d38` (feat)

## Files Created/Modified

- `src/store_predict/services/excel_report.py` — Pure function `generate_report_xlsx()` with three private sheet helpers
- `pyproject.toml` — New `[[tool.mypy.overrides]]` block for `xlsxwriter.*`
- `src/store_predict/i18n/locales/en.yaml` — `excel:` section with 18 English keys
- `src/store_predict/i18n/locales/fr.yaml` — `excel:` section with 18 French keys (all sheet names ≤31 chars)

## Decisions Made

- Used `_i18n.t()` directly instead of `store_predict.i18n.t()` wrapper — the wrapper calls `get_locale()` which returns "fr" outside NiceGUI context regardless of `_i18n.set("locale", ...)`, making EN/FR outputs identical in tests
- Imported `store_predict.i18n` at module level (noqa: F401) to ensure YAML load_path is configured before first `_i18n.t()` call
- Performance rows in Summary and extra columns in VM Detail both gated on `summary.has_performance_data`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused VMCalculation and WorkloadGroupResult from TYPE_CHECKING import**

- **Found during:** Task 2 (ruff check)
- **Issue:** Plan specified importing all three types under TYPE_CHECKING, but only CalculationSummary is used as annotation; ruff F401 flagged VMCalculation and WorkloadGroupResult as unused
- **Fix:** Reduced TYPE_CHECKING import to `CalculationSummary` only
- **Files modified:** `src/store_predict/services/excel_report.py`
- **Verification:** ruff reports zero issues
- **Committed in:** 4055d38 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added module-level store_predict.i18n import to ensure YAML configured**

- **Found during:** Task 2 (full verification — EN != FR assertion failed)
- **Issue:** Direct `_i18n.t()` calls without prior `store_predict.i18n` import caused YAML files not loaded, returning key-not-found placeholders identically for EN and FR
- **Fix:** Added `import store_predict.i18n  # noqa: F401` at module level to ensure YAML load_path and skip_locale_root_data config are applied before any `_i18n.t()` call
- **Files modified:** `src/store_predict/services/excel_report.py`
- **Verification:** `b_en != b_fr` assertion passes; EN: 7654 bytes, FR: 7689 bytes
- **Committed in:** 4055d38 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 missing critical)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- The `store_predict.i18n.t()` wrapper reads locale from NiceGUI session storage (`app.storage.tab`), falling back to "fr" outside NiceGUI — this means it cannot be used in standalone functions that need to honour a `locale` parameter. Solution: call `_i18n.t()` directly after `_i18n.set("locale", locale)`, with module-level `store_predict.i18n` import for YAML configuration.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `generate_report_xlsx()` is ready for integration into the report page UI (Plan 09-02)
- Caller is responsible for filename construction (e.g., `f"{sanitize_filename(project_name)}_sizing.xlsx"`)
- Function accepts same `summary` and `locale` parameters as `generate_report_pdf()` for drop-in UI integration

---
*Phase: 09-excel-export*
*Completed: 2026-02-20*
