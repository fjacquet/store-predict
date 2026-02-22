---
phase: 22-compute-sizing-module-page
plan: "02"
subsystem: ui
tags: [nicegui, compute-sizing, i18n, reactive-ui]
dependency_graph:
  requires: [22-01]
  provides: [/compute-page, compute-i18n-keys]
  affects: [layout.py, main.py, en.yaml, fr.yaml]
tech_stack:
  added: []
  patterns: [ui.refreshable, app.storage.tab, @ui.page decorator, session-backed reactive inputs]
key_files:
  created:
    - src/store_predict/ui/pages/compute.py
  modified:
    - src/store_predict/ui/layout.py
    - src/store_predict/main.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
decisions:
  - "dict[str, object] config type resolved via str() cast before int()/float() to satisfy mypy"
  - "compute_sizing() has no ap_enabled parameter — AP values always computed; UI toggle controls display only"
  - "ruff auto-fixed import ordering in main.py; removed redundant # noqa: F401 from compute import"
metrics:
  duration_seconds: 248
  completed_date: "2026-02-22"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
---

# Phase 22 Plan 02: Compute Sizing Page Summary

**One-liner:** Reactive `/compute` NiceGUI page with 9-preset Dell PowerEdge selector, overcommit slider, vMSC/A-P toggles, and `@ui.refreshable` results panel backed by `compute_sizing()` pipeline.

## Files Created

### `src/store_predict/ui/pages/compute.py` (new)

- `@ui.page("/compute")` route registered via NiceGUI decorator
- `_load_compute_config()` reads session config from `app.storage.tab` (6 keys)
- `_resolve_host_config()` maps preset name to `HostConfig`; Custom preset uses session values
- `@ui.refreshable _results_panel()` re-runs `compute_sizing()` on every parameter change
- `_render_aggregate_cards()` shows total active vCPUs, RAM, excluded VM count
- `_render_settings_panel()` shows preset selector, overcommit input, vMSC/AP toggles, custom spec inputs
- No-data guard: redirect card with "Go to Upload" button when session is empty
- All user-visible strings via `t()` — no hardcoded English strings

## Files Modified

### `src/store_predict/ui/layout.py`

- Added 1 line: `ui.link(t("layout.compute"), "/compute")` after concerns link

### `src/store_predict/main.py`

- Added `import store_predict.ui.pages.compute` with ruff-sorted import order

### `src/store_predict/i18n/locales/en.yaml` and `fr.yaml`

- Added `compute:` key under `layout:` section (EN: "Compute Sizing", FR: "Dimensionnement calcul")
- Appended 26-key `compute:` namespace to both files
- Added 4 tooltip keys: `compute_preset`, `compute_overcommit`, `compute_vmsc`, `compute_ap`
- Total additions per file: 33 keys

## i18n Keys

- **26 keys** added to `compute:` namespace in both locales
- **4 tooltip keys** added to `tooltip:` section in both locales
- **1 layout key** added to `layout:` section in both locales
- Parity verified: `en_compute.keys() == fr_compute.keys()` (no gap)

## Session Keys Used

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `compute_preset` | str | "R760 (2x28c / 512 GiB)" | Selected host preset name |
| `compute_overcommit` | float | 4.0 | vCPU overcommit ratio |
| `compute_vmsc` | bool | False | vMSC stretch cluster toggle |
| `compute_ap` | bool | False | Active/Passive DR toggle |
| `compute_custom_cps` | int | 28 | Custom preset cores/socket |
| `compute_custom_sockets` | int | 2 | Custom preset socket count |
| `compute_custom_ram` | int | 512 | Custom preset RAM (GiB) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy type errors from `dict[str, object]` cfg**

- **Found during:** Task 2 mypy check
- **Issue:** `int(cfg["key"])` and `float(cfg["key"])` fail mypy because `object` type isn't narrowed to numeric types. 8 errors reported.
- **Fix:** Changed to `int(str(cfg["key"]))` and `float(str(cfg["key"]))` to satisfy mypy's type system. Runtime behavior unchanged (values are always str/int/float from session storage).
- **Files modified:** `src/store_predict/ui/pages/compute.py`
- **Commit:** 83179e4

**2. [Rule 3 - Blocking] ruff import order issue in main.py**

- **Found during:** Task 2 ruff check
- **Issue:** Adding `import store_predict.ui.pages.compute` before the existing imports violated ruff's I001 (isort) rule. RUF100 (unused noqa) also triggered.
- **Fix:** Ran `ruff check --fix` to auto-sort imports. The `# noqa: F401` was removed from the compute import (ruff auto-sorted it to a position where it's no longer flagged).
- **Files modified:** `src/store_predict/main.py`
- **Commit:** 83179e4

**3. [Informational] `compute_sizing()` has no `ap_enabled` parameter**

- **Found during:** Task 2 code review of pipeline module
- **Issue:** Plan's code sample called `compute_sizing(..., ap_enabled=bool(cfg["ap_enabled"]))` but the actual function signature (from 22-01) only has `vmsc_enabled`. AP values are always computed.
- **Fix:** Removed `ap_enabled` from `compute_sizing()` call. The toggle controls display in `_results_panel()` via `if cfg["ap_enabled"]:` — no pipeline change needed.
- **Impact:** None — behavior matches specification.

## Test Results

- **439 tests passed**, 1 skipped, 2 pre-existing failures (unrelated to Phase 22)
- Pre-existing failures: `test_llm_classifier.py::test_llm_config_max_concurrent_default` and `test_llm_config_timeout_default` (documented in STATE.md)
- No new test failures introduced

## Self-Check: PASSED
