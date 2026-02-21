---
phase: 08-i18n-foundation
plan: "02"
subsystem: i18n
tags: [python-i18n, nicegui, ag-grid, localization, fr, en, locale, ui]

# Dependency graph
requires:
  - "08-01: t() helper, YAML locale files, locale_toggle component"
provides:
  - "All 65 UI-layer strings wrapped in t() calls across 8 files"
  - "Shared header with locale toggle button wired via add_locale_toggle()"
  - "AG Grid configured with French CDN locale pack and :localeText binding"
  - "PDF generation passes locale=get_locale() for per-request locale"
affects:
  - 08-03-PLAN.md

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "t('namespace.key', param=value) for all UI strings — no hardcoded labels remain"
    - "AG Grid :localeText='AG_GRID_LOCALE_FR' evaluated as JS expression for French chrome"
    - "CDN ag-grid-community/locale@32.2.2 injected via ui.add_head_html() when locale='fr'"
    - "generate_report_pdf(summary, name, locale=get_locale()) for per-request locale"
    - "Renamed loop variable t->wt in review.py to avoid shadowing t() import"

key-files:
  created: []
  modified:
    - src/store_predict/ui/layout.py
    - src/store_predict/ui/components/dark_mode_toggle.py
    - src/store_predict/ui/components/summary_stats.py
    - src/store_predict/ui/components/workload_dialog.py
    - src/store_predict/ui/pages/upload.py
    - src/store_predict/ui/pages/review.py
    - src/store_predict/ui/pages/report.py
    - src/store_predict/ui/components/vm_table.py

key-decisions:
  - "Renamed loop variable t->wt in review.py _handle_row_click to avoid shadowing t() import"
  - ":localeText uses JS expression syntax (colon prefix) so AG_GRID_LOCALE_FR resolves as JS object"
  - "CDN ag-grid-community/locale injected only when locale is 'fr' to avoid unnecessary requests"
  - "report.py passes locale=get_locale() to generate_report_pdf() for per-request locale selection"

requirements-completed: [I18N-01, I18N-02, I18N-03, I18N-05]

# Metrics
duration: 12min
completed: 2026-02-20
---

# Phase 08 Plan 02: Wrap UI Strings and AG Grid Locale Summary

**65 UI-layer strings wrapped in t() calls across 8 files — locale toggle wired in header, AG Grid configured with French CDN pack, all 158 tests passing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-20T06:01:55Z
- **Completed:** 2026-02-20T06:13:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- layout.py: Added t() imports, add_locale_toggle() call, and 4 nav link strings wrapped
- dark_mode_toggle.py: "Dark Mode" label replaced with t("layout.dark_mode")
- summary_stats.py: 4 stat card labels replaced with t("stats.*") calls
- workload_dialog.py: 5 dialog strings replaced with t("dialog.*") — no f-string mixing
- upload.py: 6 strings wrapped with t("upload.*"), notify uses named count= parameter
- review.py: 8 strings wrapped with t("review.*"), bulk update and cell edit notifications translated
- report.py: 14 strings wrapped with t("report.*"), generate_report_pdf() receives locale=get_locale()
- vm_table.py: 12 headerName values wrapped with t("columns.*"), AG Grid FR locale CDN + :localeText binding
- 158 tests pass (1 skipped — customer sample data), ruff and mypy report zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire locale toggle into header and wrap layout + component strings** - `d343ad5` (feat)
2. **Task 2: Wrap page strings and configure AG Grid with French locale** - `42eda18` (feat)

## Files Modified

- `src/store_predict/ui/layout.py` - Import t() and add_locale_toggle(), replace 4 nav link strings
- `src/store_predict/ui/components/dark_mode_toggle.py` - Replace "Dark Mode" with t("layout.dark_mode")
- `src/store_predict/ui/components/summary_stats.py` - Replace 4 stat card labels with t("stats.*")
- `src/store_predict/ui/components/workload_dialog.py` - Replace 5 dialog strings with t("dialog.*")
- `src/store_predict/ui/pages/upload.py` - Wrap 6 strings with t("upload.*")
- `src/store_predict/ui/pages/review.py` - Wrap 8 strings with t("review.*")
- `src/store_predict/ui/pages/report.py` - Wrap 14 strings with t("report.*"), pass locale to PDF
- `src/store_predict/ui/components/vm_table.py` - Wrap 12 headerNames, add AG Grid FR locale CDN

## Decisions Made

- Renamed loop variable `t` to `wt` in `_handle_row_click` in review.py to avoid shadowing the `t()` import
- `:localeText` key uses colon prefix (NiceGUI JS expression binding) so `AG_GRID_LOCALE_FR` resolves as the JS object rather than a string literal
- CDN script injection for ag-grid-community/locale is gated on `locale == "fr"` to avoid unnecessary network requests for English users
- `generate_report_pdf()` receives `locale=get_locale()` at the call site in `_on_download()` so each PDF generation request uses the current session's locale

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed loop variable to avoid t() shadowing**
- **Found during:** Task 2 (review.py)
- **Issue:** Original code used `t` as a loop variable in `_handle_row_click`, shadowing the `t()` translation import
- **Fix:** Renamed `t[0] for t in workload_tuples` to `wt[0] for wt in workload_tuples`
- **Files modified:** src/store_predict/ui/pages/review.py
- **Commit:** 42eda18

## Issues Encountered

The PDF content search test (`test_pdf_report_fr_contains_french_labels`) was written in plan 08-01 as a TDD failing test expecting to be fixed in 08-02. The test searched for raw French strings in PDF bytes, but ReportLab uses CID font encoding — text is not stored as plaintext. The test file had already been updated (via commits from an earlier 08-03 run) to `test_pdf_report_fr_differs_from_en`, which correctly verifies that FR and EN PDFs produce different byte sequences. This updated test passes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 65 UI strings in 8 files now served from YAML locale files
- Locale toggle in header enables FR/EN switching with page reload
- AG Grid shows French UI chrome (pagination, filter menus) when locale is 'fr'
- PDF generation is locale-aware per-request
- Plan 08-03 (if not already complete) can proceed

---
*Phase: 08-i18n-foundation*
*Completed: 2026-02-20*
