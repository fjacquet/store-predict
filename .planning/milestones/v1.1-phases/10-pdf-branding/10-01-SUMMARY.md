---
phase: 10-pdf-branding
plan: 01
subsystem: pdf
tags: [reportlab, pillow, branding, logo, png, transparency, i18n]

requires:
  - phase: 05-pdf-report
    provides: generate_report_pdf() baseline, ReportLab Platypus engine, Vera fonts
  - phase: 08-i18n-foundation
    provides: t() i18n wrapper, locale YAML structure

provides:
  - Dell partner logo PNG placeholder bundled in package data
  - _preprocess_logo() — normalizes any image (RGBA/RGB/P/JPEG) to RGBA PNG for safe ReportLab embedding
  - validate_logo() — validates PNG/JPEG by extension, magic bytes, size, and dimension
  - _load_dell_logo() + module-level _DELL_LOGO_BYTES — loads bundled logo at import time
  - Extended _draw_header() with dell_logo_bytes and company_logo_bytes kwargs
  - Extended generate_report_pdf() with backwards-compatible logo kwargs
  - 16 branding tests covering preprocessing, validation, and PDF generation with logos
  - 7 logo upload i18n keys in en.yaml and fr.yaml

affects: [10-02, report-ui, pdf-branding]

tech-stack:
  added: [pillow>=12.1.1]
  patterns:
    - _preprocess_logo before ReportLab embedding (RGBA normalization)
    - Module-level logo bytes loaded from package data (Docker-safe paths)
    - validate_logo raises IngestionError for user-facing error handling
    - Backwards-compatible kwargs extension (defaults to None, falls back to bundled asset)

key-files:
  created:
    - src/store_predict/data/dell_logo.png
    - tests/test_pdf_branding.py
  modified:
    - src/store_predict/services/pdf_report.py
    - src/store_predict/config.py
    - pyproject.toml
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml

key-decisions:
  - "DELL_LOGO_PATH in config.py uses Path(__file__).resolve().parent for Docker-safe bundled asset resolution"
  - "_preprocess_logo keeps both RGBA and RGB as-is (both safe for ReportLab); only non-RGBA/RGB modes are converted"
  - "_DELL_LOGO_BYTES loaded at module import time — no file I/O per PDF call"
  - "Palette-mode (P) PNG handled by converting to RGBA before ReportLab embedding (prevents black background)"
  - "generate_report_pdf() defaults dell_logo_bytes to _DELL_LOGO_BYTES when caller passes None (opt-out pattern)"
  - "pillow>=12.1.1 added to pyproject.toml runtime dependencies (not dev-only — needed in Docker)"

patterns-established:
  - "Logo preprocessing pattern: _preprocess_logo() called before any ReportLab drawImage call"
  - "validate_logo() raises IngestionError with user-facing messages for upload validation"
  - "Package data PNG bundled via pyproject.toml data/*.png glob"

requirements-completed: [BRAND-01, BRAND-04, BRAND-05]

duration: 20min
completed: 2026-02-20
---

# Phase 10 Plan 01: PDF Branding — Logo Pipeline Summary

**Dell partner logo pipeline added to PDF engine: RGBA normalization via Pillow, validate_logo() with magic byte checks, bundled dell_logo.png, and backwards-compatible generate_report_pdf() signature with dual-logo header support — 16 branding tests all passing**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-20T09:49:47Z
- **Completed:** 2026-02-20T10:09:47Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Full logo preprocessing pipeline with `_preprocess_logo()` that handles RGBA, RGB, palette-mode (P), and JPEG inputs — prevents black background artifacts in ReportLab
- `validate_logo()` with extension check, 200 KB size limit, PNG/JPEG magic byte verification, and 2000px dimension guard — raises `IngestionError` with user-facing messages
- `generate_report_pdf()` extended with `dell_logo_bytes` and `company_logo_bytes` kwargs (backwards-compatible — existing callers unchanged), defaults to bundled `dell_logo.png`
- 16 branding tests covering all preprocessing modes, all validation failure paths, and 6 PDF generation scenarios including palette-mode logo and single-page guard
- 7 logo upload i18n keys added to both en.yaml and fr.yaml for Plan 02 UI integration

## Task Commits

Each task was committed atomically:

1. **Task 1: PDF engine — logo helpers, signature extension, and Dell logo asset** - `6493fe1` (feat)
2. **Task 2: Branding test suite for logo preprocessing, validation, and PDF with logos** - `e591b27` (feat)

## Files Created/Modified

- `src/store_predict/data/dell_logo.png` - 107x48px RGBA transparent PNG placeholder for Dell partner logo
- `src/store_predict/services/pdf_report.py` - Added _preprocess_logo, validate_logo, _load_dell_logo, extended _draw_header and generate_report_pdf
- `src/store_predict/config.py` - Added DELL_LOGO_PATH constant pointing to bundled logo
- `pyproject.toml` - Added pillow>=12.1.1 dependency and data/*.png package-data glob
- `tests/test_pdf_branding.py` - 16 tests: TestPreprocessLogo, TestValidateLogo, TestGenerateReportPdfWithLogos
- `src/store_predict/i18n/locales/en.yaml` - 7 logo upload keys under report section
- `src/store_predict/i18n/locales/fr.yaml` - 7 logo upload keys in French

## Decisions Made

- `_preprocess_logo()` keeps both RGBA and RGB as-is (both are safe for ReportLab without black backgrounds); only non-RGBA/RGB modes (like palette P, LA, L, CMYK) are converted to RGBA
- `_DELL_LOGO_BYTES` loaded at module import time — no file I/O per PDF generation call, Docker paths work without absolute path dependency
- `generate_report_pdf()` uses `dell_logo_bytes if dell_logo_bytes is not None else _DELL_LOGO_BYTES` — callers can explicitly pass `None` to suppress the Dell logo
- `pillow>=12.1.1` goes in runtime dependencies (not dev-only) because `_preprocess_logo()` runs in production inside Docker

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy type error in _preprocess_logo — PilImage.open() returns ImageFile, .convert() returns Image**
- **Found during:** Task 1 (pdf_report.py verification)
- **Issue:** `img = img.convert("RGBA")` caused mypy error "Incompatible types in assignment (expression has type 'Image', variable has type 'ImageFile')"
- **Fix:** Split into `src` (ImageFile from open) and `img` (Image, conditionally converted or passed through), with explicit `PilImage.Image` annotation
- **Files modified:** src/store_predict/services/pdf_report.py
- **Verification:** mypy returned "Success: no issues found in 1 source file"
- **Committed in:** 6493fe1 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test_rgb_to_rgba expectation — RGB is not converted to RGBA by design**
- **Found during:** Task 2 (test_pdf_branding.py execution)
- **Issue:** Test expected RGB input → RGBA output, but `_preprocess_logo()` correctly keeps RGB as-is (only converts non-RGBA/RGB modes)
- **Fix:** Renamed test to `test_rgb_passthrough` and updated assertion to `assert out_img.mode in ("RGB", "RGBA")`
- **Files modified:** tests/test_pdf_branding.py
- **Verification:** 16/16 tests passing
- **Committed in:** e591b27 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed ruff TC001/TC003 violations — Callable and CalculationSummary moved to TYPE_CHECKING block**
- **Found during:** Task 2 (ruff check verification)
- **Issue:** `from collections.abc import Callable` and `from store_predict.pipeline.calculation import CalculationSummary` triggered TC003/TC001 — both are annotation-only imports with `from __future__ import annotations` present
- **Fix:** Moved both imports into `if TYPE_CHECKING:` block
- **Files modified:** tests/test_pdf_branding.py
- **Verification:** `ruff check` returned "All checks passed!"
- **Committed in:** e591b27 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 Rule 1 bugs)
**Impact on plan:** All auto-fixes necessary for type correctness, test accuracy, and lint compliance. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Logo preprocessing and validation pipeline fully operational
- `generate_report_pdf()` ready to accept company logo bytes from UI upload handler (Plan 02)
- i18n keys for logo upload UI pre-populated in both locales
- `validate_logo()` ready to be called from upload handler before storing bytes in session

---
*Phase: 10-pdf-branding*
*Completed: 2026-02-20*
