---
phase: 27-session-save-restore
plan: "01"
subsystem: pipeline
tags: [session, archive, zip, serialization, i18n]
dependency_graph:
  requires: []
  provides: [session_archive.py, session-i18n-keys]
  affects: [upload.py (Plan 02 wires up the UI)]
tech_stack:
  added: []
  patterns: [zipfile.ZipFile + io.BytesIO, JSON snapshot, IngestionError sentinel]
key_files:
  created:
    - src/store_predict/pipeline/session_archive.py
    - tests/test_session_archive.py
  modified:
    - src/store_predict/i18n/locales/fr.yaml
    - src/store_predict/i18n/locales/en.yaml
decisions:
  - "Session archive uses schema_version=1 in JSON for forward compatibility"
  - "Layout and compute sub-dicts in JSON mapped back to flat app.storage.tab keys on restore"
  - "is_session_zip() catches all exceptions and returns False — never raises, safe to call on any bytes"
  - "restore_session_zip() raises IngestionError (not ValueError/KeyError) to integrate cleanly with pipeline error handling"
  - "Type annotations use dict[str, float | int] for layout/compute sub-dicts to satisfy mypy without type: ignore"
metrics:
  duration: "~3 minutes 19 seconds"
  completed: "2026-02-24"
  tasks_completed: 3
  files_changed: 4
---

# Phase 27 Plan 01: Session Archive Module Summary

**One-liner:** Pure-stdlib ZIP serialization with JSON snapshot for full StorePredict session save/restore — schema_version=1, IngestionError on all failure paths.

## What Was Built

Created the session_archive module that forms the pure-Python core of Phase 27 (Session Save & Restore). The module has zero pandas dependency — it uses only stdlib `io`, `json`, and `zipfile`. This separation allows testing in isolation without any NiceGUI context and keeps `upload.py` from becoming a god file.

### Task 1: session_archive.py

`src/store_predict/pipeline/session_archive.py` provides three public functions:

- **`save_session_zip(session_data, original_file_bytes, original_filename) -> bytes`** — Builds a ZIP containing the original uploaded file plus a `session.json` snapshot of all session state (vm_data, project_name, storage_model, selected_datacenters, selected_clusters, layout config, compute config). Compression: ZIP_DEFLATED.
- **`restore_session_zip(content) -> dict[str, object]`** — Reads the ZIP, parses session.json, validates schema_version==1, and returns a flat dict of app.storage.tab keys (all 19 canonical keys plus `_restored_original_filename` and `_restored_original_bytes` for the upload page).
- **`is_session_zip(content) -> bool`** — Returns True iff content is a valid ZIP containing `session.json` at root. Distinguishes session archives from LiveOptics .zips. Never raises.
- **`SESSION_ZIP_SENTINEL = "session.json"`** — Exported constant for use by upload.py format detection.

### Task 2: i18n keys

Added `session:` block to both `fr.yaml` and `en.yaml`, immediately after the `upload:` block:
- `session.save_button` — button label
- `session.save_tooltip` — tooltip for save button
- `session.restore_success` — success notification with `%{count}` interpolation
- `session.restore_error` — error notification with `%{reason}` interpolation
- `session.restore_format_hint` — format hint shown when a session .zip is detected at upload

### Task 3: Tests

`tests/test_session_archive.py` provides 15 tests covering:
- Round-trip: vm_data, project_name, storage_model, selected_datacenters, layout config, compute config, original file bytes, original filename
- `is_session_zip`: False for non-zip, False for LiveOptics .zip (no session.json), True for valid archive
- Error cases: `IngestionError` on bad zip bytes, missing session.json, wrong schema_version

## Verification Results

All verification criteria passed:

| Check | Result |
|-------|--------|
| Clean import | PASS |
| 15 tests pass | PASS |
| mypy clean | PASS |
| ruff clean | PASS |
| i18n t() keys resolve | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy type annotation errors in restore_session_zip()**
- **Found during:** Overall verification (mypy check)
- **Issue:** `dict[str, object]` for layout/compute sub-dicts caused mypy to reject `float()` and `int()` calls with `object` arguments (13 errors). Initial `type: ignore[assignment]` comments were rejected as unused after type narrowing.
- **Fix:** Changed layout dict type to `dict[str, float | int]` and compute dict type to `dict[str, float | int | bool | str]`. Removed all `type: ignore` comments.
- **Files modified:** `src/store_predict/pipeline/session_archive.py`
- **Commit:** `5b197ff` (included with Task 3 commit)

## Self-Check: PASSED

Files exist:
- `src/store_predict/pipeline/session_archive.py` — FOUND
- `tests/test_session_archive.py` — FOUND
- `src/store_predict/i18n/locales/fr.yaml` — FOUND (contains session block)
- `src/store_predict/i18n/locales/en.yaml` — FOUND (contains session block)

Commits exist:
- `8f71e15` feat(27-01): session_archive module — FOUND
- `e196474` feat(27-01): i18n keys — FOUND
- `5b197ff` feat(27-01): tests + type fix — FOUND
