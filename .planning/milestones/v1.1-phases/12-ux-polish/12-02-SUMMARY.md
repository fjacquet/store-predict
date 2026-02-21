---
phase: 12-ux-polish
plan: "02"
subsystem: ui
tags: [nicegui, ux, i18n, no-data, button-guards, notify-types]

requires:
  - phase: 12-ux-polish
    plan: "01"
    provides: Upload page with spinner, run.io_bound, persistent LLM notification, i18n error keys

provides:
  - review.py no-data state upgraded to card-with-CTA (ui.card + ui.icon + ui.button)
  - report.py no-data state upgraded to card-with-CTA (ui.card + ui.icon + ui.button)
  - report.py PDF and Excel buttons disable during generation and re-enable on finish
  - report.py _handle_logo_upload uses t("error.logo_upload_failed") instead of str(exc)
  - All ui.notify() type values confirmed canonical across upload, review, report pages
  - test_ux_polish.py with 20 tests locking in UX patterns (i18n keys, notify types, structural elements)

affects: [phase-12-ux-polish, tests, review-page, report-page]

tech-stack:
  added: []
  patterns:
    - "No-data card pattern: ui.card + ui.icon(upload_file) + ui.label + ui.button(navigate)"
    - "Button guard pattern: capture ref, wrap on_click with disable/try/finally/enable"
    - "Logo error i18n: bare except Exception with t('error.logo_upload_failed')"
    - "UX test pattern: regex/string inspection of page source — no mocking, real files"

key-files:
  created:
    - tests/test_ux_polish.py
  modified:
    - src/store_predict/ui/pages/review.py
    - src/store_predict/ui/pages/report.py

key-decisions:
  - "Merged nested with statements into parenthesized multi-context with (ruff SIM117 fix)"
  - "pdf_btn and excel_btn wired via .on('click', handler) after button row creation to allow handler closure"
  - "IngestionError str(exc) in upload.py left unchanged — domain error with user-facing message, not raw exception"
  - "20 tests written vs 11 planned — parametrize over 2 locales x 4 keys = 8 + 3 structural + 9 other = 20 total"

patterns-established:
  - "No-data empty state uses card-with-icon-and-CTA-button — consistent across all pages"
  - "Download button guards: disable + try/finally + enable, async on_click"

requirements-completed: [UX-03, UX-04]

duration: 5min
completed: 2026-02-20
---

# Phase 12 Plan 02: UX Polish — Review/Report Pages Summary

**No-data card-with-CTA upgrade, download button disable/enable guards, logo error i18n fix, canonical notify types audit, and 20 structural tests across review and report pages**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-20T13:27:38Z
- **Completed:** 2026-02-20T13:33:10Z
- **Tasks:** 2
- **Files modified:** 3 (review.py, report.py, test_ux_polish.py created)

## Accomplishments

- Upgraded review.py no-data state from plain `ui.link` to `ui.card` with `ui.icon("upload_file")`, `ui.label`, and `ui.button` CTA
- Upgraded report.py no-data state from plain `ui.link` to `ui.card` with `ui.icon("upload_file")`, `ui.label`, and `ui.button` CTA
- Added download button guards in report.py: `pdf_btn` and `excel_btn` captured as references, async handlers `on_download_pdf` and `on_download_excel` disable then re-enable buttons via `try/finally`
- Fixed `_handle_logo_upload` except clause to use `t("error.logo_upload_failed")` instead of `str(exc)`
- Audited all `ui.notify()` calls across upload.py, review.py, report.py — all use canonical types (positive/negative/warning/info)
- Created `tests/test_ux_polish.py` with 20 tests: 8 parametrized i18n key tests, 2 YAML validity tests, 2 raw exception guard tests, 3 notify type tests, 2 no-data structural tests, 3 upload UX tests
- Full test suite: 227 passed, 1 skipped, 0 failures (up from 207 in Phase 12-01)

## Task Commits

Each task was committed atomically:

1. **Task 1: Polish review.py and report.py** - `6de92ce` (feat)
2. **Task 2: Write test_ux_polish.py** - `d311070` (test)

## Files Created/Modified

- `src/store_predict/ui/pages/review.py` — no-data section upgraded to card-with-CTA
- `src/store_predict/ui/pages/report.py` — no-data card-with-CTA, button disable/enable guards, logo i18n fix
- `tests/test_ux_polish.py` — 20 tests locking in UX patterns (160 lines)

## Decisions Made

- Merged nested `with` statements into parenthesized multi-context `with` to fix ruff SIM117 — the three context managers (layout, column, card) collapse cleanly into a single parenthesized `with`
- PDF and Excel buttons wired via `.on("click", handler)` after button creation so handlers can close over `pdf_btn`/`excel_btn` refs without forward-reference issues
- Left `upload.py` line 148 `str(exc)` intact — it surfaces `IngestionError` which contains intentional user-facing domain messages, not raw internal exception strings
- 20 tests written (plan said 11 minimum at 60 lines minimum) — parametrize multiplied count; test file is 160 lines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff SIM117 — nested with statements merged**
- **Found during:** Task 1 (ruff check)
- **Issue:** Both review.py and report.py had nested `with` statements inside the no-data block; ruff SIM117 requires merging into a single parenthesized `with`
- **Fix:** Merged `with ui.card()` into the outer parenthesized `with (layout(...), ui.column(...), ui.card(...)):`
- **Files modified:** review.py, report.py
- **Commit:** `6de92ce`

## Issues Encountered

None — all changes passed ruff and mypy (pre-existing ingestion.py unused-ignore unrelated). Test suite green on first run.

## User Setup Required

None.

## Next Phase Readiness

- Phase 12 UX Polish is now complete (both plans done)
- Review and report pages match the same quality bar as the upload page
- All UX requirements (UX-01 through UX-04) fulfilled and tested
- 227 tests total, all green
