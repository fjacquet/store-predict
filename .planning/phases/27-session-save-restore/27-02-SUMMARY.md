---
phase: 27-session-save-restore
plan: "02"
subsystem: ui
tags: [session, save-restore, upload, report, nicegui]
dependency_graph:
  requires: [27-01]
  provides: [session-save-ui, session-restore-ui]
  affects: [report-page, upload-page]
tech_stack:
  added: []
  patterns: [nicegui-run-io-bound, slot-context-with-widget, async-nested-functions]
key_files:
  created: []
  modified:
    - src/store_predict/ui/pages/report.py
    - src/store_predict/ui/pages/upload.py
decisions:
  - Save Session button uses purple styling to distinguish it from PDF (blue) and Excel (green) buttons
  - Session zip detection runs BEFORE LiveOptics zip extraction to avoid false positive extraction attempts
  - _handle_session_restore defined as nested async alongside handle_upload (consistent with existing code pattern)
  - Original file bytes captured in _session_original_bytes on every normal upload for later re-save
metrics:
  duration: "~8 min"
  completed: "2026-02-24T20:20:11Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 27 Plan 02: UI Wiring — Session Save/Restore Summary

Session save/restore round-trip wired into NiceGUI UI: Save Session button on report page downloads a portable .zip archive; Upload page detects and restores session .zip files before any LiveOptics extraction logic.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Save Session button to report page | 698a06d | src/store_predict/ui/pages/report.py |
| 1a | Fix ruff import ordering and ternary style | 7b7afb0 | src/store_predict/ui/pages/report.py |
| 2 | Add session restore branch to upload page | 94735b7 | src/store_predict/ui/pages/upload.py |

## What Was Built

### Report Page — Save Session Button

- Added `from store_predict.pipeline.session_archive import save_session_zip` import
- Added `run` to `from nicegui import` imports for `run.io_bound()` usage
- Defined `_save_session()` async handler inside `report_page()` that:
  - Captures `dict(app.storage.tab)` as session snapshot
  - Retrieves `_session_original_bytes` and `_session_original_filename` from tab storage
  - Calls `save_session_zip()` via `run.io_bound()` (thread-safe)
  - Triggers `ui.download()` with `{project_name}_session.zip`
- Added Save Session button with purple styling (`bg-purple-700 text-white`) and save icon, consistent with existing download button pattern

### Upload Page — Session Restore Branch

- Added `from store_predict.pipeline.session_archive import is_session_zip, restore_session_zip` import
- Added `_handle_session_restore()` nested async function:
  - Calls `restore_session_zip()` via `run.io_bound()`
  - Pops `_restored_original_bytes` and `_restored_original_filename` into tab storage
  - Calls `app.storage.tab.update(restored)` to load all session keys
  - Shows success notification with VM count, then navigates to `/review`
  - Handles `IngestionError` with negative notification
- Modified `handle_upload()` to detect session .zip BEFORE LiveOptics extraction:
  ```python
  if filename.lower().endswith(".zip") and is_session_zip(content):
      await _handle_session_restore(content)
      return
  ```
- Added `_session_original_bytes` and `_session_original_filename` capture on every normal (non-session) upload

## Verification

- `report.py` and `upload.py`: syntax OK (ast.parse)
- `mypy`: Success: no issues found in 2 source files
- `ruff check`: All checks passed
- `pytest tests/test_session_archive.py tests/test_validation.py`: 25 passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff import ordering and SIM108 violations**
- **Found during:** Task 1 verification
- **Issue:** `save_session_zip` import placed after `services` imports (wrong alphabetical order); if/else block for bytes check instead of ternary (SIM108)
- **Fix:** Moved `pipeline.session_archive` import before `services.*` imports; replaced if/else with ternary
- **Files modified:** src/store_predict/ui/pages/report.py
- **Commit:** 7b7afb0

**2. [Rule 1 - Bug] Removed unused `type: ignore[arg-type]` in upload.py**
- **Found during:** Task 2 mypy verification
- **Issue:** mypy correctly typed `app.storage.tab.update(restored)` — the `type: ignore[arg-type]` comment was flagged as unused
- **Fix:** Removed the unused comment
- **Files modified:** src/store_predict/ui/pages/upload.py
- **Commit:** 94735b7

## Self-Check: PASSED

- FOUND: src/store_predict/ui/pages/report.py
- FOUND: src/store_predict/ui/pages/upload.py
- FOUND: .planning/phases/27-session-save-restore/27-02-SUMMARY.md
- FOUND: commit 698a06d (Task 1 — Save Session button)
- FOUND: commit 94735b7 (Task 2 — session restore branch)
- FOUND: commit 7b7afb0 (ruff/mypy fixes)
