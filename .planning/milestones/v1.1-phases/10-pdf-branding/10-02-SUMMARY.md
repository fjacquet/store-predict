---
phase: 10-pdf-branding
plan: 02
subsystem: ui
tags: [nicegui, logo-upload, base64, tab-storage, pdf, branding, i18n, pillow]

requires:
  - phase: 10-pdf-branding-01
    provides: validate_logo(), generate_report_pdf() with company_logo_bytes kwarg, i18n keys for logo upload
  - phase: 05-pdf-report
    provides: generate_report_pdf() baseline, ReportLab engine
  - phase: 08-i18n-foundation
    provides: t() i18n wrapper, locale YAML structure

provides:
  - _build_logo_upload_section() — NiceGUI card with ui.upload widget accepting PNG/JPEG up to 200 KB
  - _handle_logo_upload() — async handler validating upload via validate_logo() and storing base64 in tab storage
  - _remove_logo() — clears company_logo_b64 from app.storage.tab with notification
  - Updated _on_download() — decodes base64 from tab storage and passes company_logo_bytes to generate_report_pdf
  - 11-test suite covering validation wiring, base64 roundtrip, and PDF generation with/without logo

affects: [report-ui, pdf-branding, tab-storage]

tech-stack:
  added: []
  patterns:
    - Logo upload: ui.upload auto_upload → async handler → validate_logo → base64 encode → tab storage
    - Logo decode: app.storage.tab.get('company_logo_b64', '') → base64.b64decode if non-empty → company_logo_bytes
    - Test: real objects only (no mocks) — validate_logo, base64 operations, and generate_report_pdf called directly

key-files:
  created:
    - tests/test_logo_ui_wiring.py
  modified:
    - src/store_predict/ui/pages/report.py

key-decisions:
  - "Logo upload section positioned below action buttons — keeps primary PDF/Excel/Back buttons prominent"
  - "async _handle_logo_upload catches all exceptions and displays ui.notify negative toast (broad except is correct for user-facing upload errors)"
  - "base64 decode guard: empty string short-circuits to None — avoids base64.b64decode('') which would succeed but produce empty bytes"
  - "test_pdf_bytes_differ_with_and_without_logo uses len() comparison as proxy — adding a PNG image always increases PDF size"

patterns-established:
  - "Tab storage encode pattern: base64.b64encode(content).decode('ascii') — always ASCII-safe for JSON storage"
  - "Tab storage decode pattern: base64.b64decode(b64) if b64 else None — guards against empty string"

requirements-completed: [BRAND-02, BRAND-03]

duration: 10min
completed: 2026-02-20
---

# Phase 10 Plan 02: PDF Branding — Logo Upload UI Wiring Summary

**Company logo upload UI wired to report page: ui.upload widget with validate_logo integration, base64 tab storage, remove button, and _on_download updated to embed logo in PDF — 11 tests passing, 200 total tests, 0 failures**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-20T10:20:58Z
- **Completed:** 2026-02-20T10:30:58Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_build_logo_upload_section()` renders a NiceGUI card with `ui.upload` accepting `.png,.jpg,.jpeg` files up to 200 KB, plus a remove button — placed below action buttons in `report_page()`
- `_handle_logo_upload()` async handler calls `validate_logo()` from Plan 01, stores base64-encoded bytes in `app.storage.tab['company_logo_b64']`, shows positive toast on success or negative toast on error
- `_on_download()` updated to read `company_logo_b64` from tab storage, decode it with base64 guard, and pass `company_logo_bytes` to `generate_report_pdf()` — enabling customer logo in PDF header
- 11-test suite: `TestLogoValidationWiring` (4), `TestBase64RoundTrip` (3), `TestPdfDownloadWithCompanyLogo` (4) — all tests use real objects, no mocks

## Task Commits

Each task was committed atomically:

1. **Task 1: Logo upload UI widget and tab storage wiring in report.py** - `e1933e2` (feat)
2. **Task 2: Test suite for logo UI wiring and PDF download with company logo** - `4898434` (feat)

## Files Created/Modified

- `src/store_predict/ui/pages/report.py` - Added base64/validate_logo imports, _build_logo_upload_section(), _handle_logo_upload(), _remove_logo(), updated _on_download() to decode logo from tab storage
- `tests/test_logo_ui_wiring.py` - 11 tests: logo validation wiring, base64 roundtrip, PDF generation with/without company logo, and logo-embedded PDF differs from logo-free PDF

## Decisions Made

- Logo upload section placed below action buttons to keep primary Download PDF/Excel/Back buttons prominent
- `async def _handle_logo_upload` uses broad `except Exception` — correct for user-facing upload handlers where any error should show a toast, not crash the page
- base64 decode guard (`base64.b64decode(b64) if b64 else None`) handles the edge case where empty string in tab storage would produce empty bytes rather than None
- `test_pdf_bytes_differ_with_and_without_logo` uses `len(with_logo) > len(without_logo)` as proxy — adding a PNG image to a PDF always increases file size, making this a reliable embedding proof

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed two ruff linting issues in test_logo_ui_wiring.py**
- **Found during:** Task 2 (ruff verification)
- **Issue:** `TC005` (empty `TYPE_CHECKING` block) and `I001` (import sort order) — both auto-fixable
- **Fix:** Ran `ruff check --fix` — removed empty `if TYPE_CHECKING:` block and reordered imports
- **Files modified:** tests/test_logo_ui_wiring.py
- **Verification:** `rtk ruff check` returned "No issues found"; 11/11 tests still passing
- **Committed in:** 4898434 (Task 2 commit, ruff fix applied before commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** Auto-fix required for lint compliance. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full BRAND-02 and BRAND-03 requirements delivered
- Company logo upload, tab storage, and PDF embedding pipeline fully operational
- Phase 10 PDF branding complete (Plans 01 and 02 both done)

---
*Phase: 10-pdf-branding*
*Completed: 2026-02-20*
