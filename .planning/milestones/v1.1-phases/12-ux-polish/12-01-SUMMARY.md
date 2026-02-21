---
phase: 12-ux-polish
plan: "01"
subsystem: ui
tags: [nicegui, asyncio, i18n, spinner, progress, run.io_bound, ux]

requires:
  - phase: 11-llm-classification-fallback
    provides: LLM classifier wired into upload pipeline, llm.classifying i18n key

provides:
  - Spinner and linear progress bar during file upload pipeline execution
  - run.io_bound wrapping of ingest_file and classify_dataframe for responsive event loop
  - Persistent LLM ui.notification with in-place spinner updated to positive/negative result
  - i18n error keys: error.unexpected, error.logo_upload_failed, upload.processing, llm.error (en+fr)
  - Raw exception string replaced with t('error.unexpected') i18n message

affects: [phase-12-ux-polish, tests, upload-pipeline]

tech-stack:
  added: []
  patterns:
    - "Local async def inside page function closes over page-scoped UI widgets"
    - "asyncio.ensure_future wraps local async handler for on_upload callback"
    - "run.io_bound wraps blocking pipeline steps so NiceGUI event loop stays responsive"
    - "ui.notification with spinner=True, timeout=None for persistent in-place status updates"

key-files:
  created: []
  modified:
    - src/store_predict/ui/pages/upload.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml

key-decisions:
  - "asyncio.ensure_future used to wrap local async handler in on_upload callback (NiceGUI limitation)"
  - "Spinner and progress bar positioned below the upload card, above format hints"
  - "LLM notification uses ui.notification (not ui.notify) so it persists while LLM runs and can be updated in-place"
  - "except Exception (bare) in LLM block: logs failure gracefully without crashing the whole upload"

patterns-established:
  - "Upload UX pattern: disable widget + show spinner + progress while pipeline runs, re-enable on finish"
  - "Persistent notification pattern: ui.notification(spinner=True, timeout=None) updated in-place"

requirements-completed: [UX-01, UX-02, UX-03]

duration: 4min
completed: 2026-02-20
---

# Phase 12 Plan 01: UX Polish — Upload Feedback Summary

**Spinner, linear progress bar, run.io_bound pipeline offloading, and persistent LLM notification replacing silent upload wait in NiceGUI upload page**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-20T17:40:36Z
- **Completed:** 2026-02-20T17:44:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added 8 new i18n keys across en.yaml and fr.yaml (error.unexpected, error.logo_upload_failed, upload.processing, llm.error) with accurate French translations
- Refactored upload.py: module-level _handle_upload replaced by local async handle_upload that closes over spinner, progress, and upload_widget
- Wrapped ingest_file and classify_dataframe with run.io_bound so NiceGUI event loop stays responsive during 2-10 second pipeline execution
- Upgraded LLM notification from fire-and-forget ui.notify to persistent ui.notification with spinner=True, timeout=None, updated in-place to positive (success) or negative (LLM error)
- Replaced raw f"Unexpected error: {exc}" with t("error.unexpected") i18n message
- All 207 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add new i18n keys to en.yaml and fr.yaml** - `9bed8ea` (feat)
2. **Task 2: Refactor upload.py with spinner, progress, run.io_bound, and persistent LLM notification** - `90a3a59` (feat)

## Files Created/Modified

- `src/store_predict/ui/pages/upload.py` - Refactored with local async handler, spinner, progress, run.io_bound, persistent LLM notification, i18n error messages
- `src/store_predict/i18n/locales/en.yaml` - Added upload.processing, llm.error, error.unexpected, error.logo_upload_failed
- `src/store_predict/i18n/locales/fr.yaml` - French mirrors of all 4 new keys

## Decisions Made

- Used `asyncio.ensure_future` to bridge the `on_upload` callback (synchronous by NiceGUI convention) to the local async handler, since NiceGUI's on_upload does not natively support async callables
- Spinner and progress widgets placed below the upload card in a centered column, above format hints label
- LLM notification uses `ui.notification` (persistent, can be updated) rather than `ui.notify` (fire-and-forget) so users see the AI classification progress and outcome
- Bare `except Exception` in the LLM block ensures an LLM API failure does not crash the entire upload flow; rules-based results are preserved

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all code changes passed ruff, mypy, and the full 207-test suite on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Upload page now provides full visual feedback during the pipeline run
- LLM classification shows persistent spinner notification updated in-place
- All error paths show i18n messages instead of raw Python exception strings
- Ready to continue with remaining 12-ux-polish plans
