---
phase: 21-health-check-module-concerns-page
plan: "02"
subsystem: ui-pages
tags: [health-checks, concerns-page, i18n, navigation, nicegui]
dependency_graph:
  requires:
    - "21-01: health_checks.py pipeline (run_health_checks, HealthCheckResult, Severity, HealthFinding)"
  provides:
    - "/concerns NiceGUI page route"
    - "layout.concerns i18n nav key"
    - "concerns.* i18n section (11 keys)"
    - "health.* i18n section (14 check keys)"
  affects:
    - "src/store_predict/ui/layout.py (nav header)"
    - "src/store_predict/main.py (route registration)"
tech_stack:
  added: []
  patterns:
    - "NiceGUI page with async handler + no-data guard using load_session_data()"
    - "Severity-to-CSS-class mapping via dict lookup"
    - "Findings grouped by check_id prefix (data_quality./sizing_risk./best_practice.)"
    - "run_health_checks() called per-visit, never stored in app.storage.tab"
key_files:
  created:
    - src/store_predict/ui/pages/concerns.py
  modified:
    - src/store_predict/ui/layout.py
    - src/store_predict/main.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
decisions:
  - "Findings grouped by check_id prefix string match, not by a Severity field — matches the domain categories (Data Quality / Sizing Risks / Best Practices)"
  - "HealthCheckResult recomputed on every page visit — not cached in session — so workload edits on Review page are immediately reflected on Concerns page"
  - "Used ruff auto-fix for SIM117 (nested with → combined) and import ordering — all ruff-suggested patterns followed"
metrics:
  duration_seconds: 420
  completed_date: "2026-02-22"
  tasks_completed: 3
  files_changed: 5
---

# Phase 21 Plan 02: /concerns Health Check Page Summary

**One-liner:** NiceGUI /concerns page wiring health check engine findings into grouped severity sections with full EN/FR i18n coverage and nav link.

## What Was Implemented

### Task 1: i18n Keys (en.yaml + fr.yaml)

Added the following new keys to both locale files:

- `layout.concerns` — Navigation link label (EN: "Concerns", FR: "Alertes")
- `concerns.*` section — 11 keys covering page title, no-data/no-findings states, summary badge labels, section headers, and affected VM display
- `health.*` section — 14 health check keys (each with `title` + `detail` subkeys), one per check implemented in `health_checks.py`

Total new i18n keys: 1 + 11 + 14 = **26 keys** added to each locale file.

Key parity verified with `yaml.safe_load` assertion: `set(en_keys) == set(fr_keys)` for both `concerns` and `health` sections.

### Task 2: concerns.py Page

Created `src/store_predict/ui/pages/concerns.py` with:

- `@ui.page("/concerns")` async page function
- No-data guard: `if df is None or df.empty` — renders info card with link to `/upload` and returns early
- `run_health_checks(df)` called fresh on every page visit (not stored in `app.storage.tab`)
- Summary badge bar: critical (red), warning (yellow), info (blue) count pills + total VMs checked
- Findings grouped into three sections by `check_id` prefix:
  - `data_quality.*` → "Data Quality" section
  - `sizing_risk.*` → "Sizing Risks" section
  - `best_practice.*` → "VMware Best Practices" section
- Per-finding cards with left-border severity color coding (red/yellow/blue)
- Affected VM names displayed up to 5 samples in monospace

### Task 3: Navigation Wiring

- `layout.py`: Added `ui.link(t("layout.concerns"), "/concerns")` after the `/layout` link in the nav header row
- `main.py`: Added `import store_predict.ui.pages.concerns` for NiceGUI route registration side-effect

## Key Decisions

1. **Grouping by check_id prefix**: Findings are grouped by the `check_id` string prefix (`data_quality.`, `sizing_risk.`, `best_practice.`) rather than by severity. This matches the intended UI structure (three domain sections) and the domain categories established in Plan 21-01.

2. **No session caching**: `HealthCheckResult` is recomputed on every page visit. This ensures that if a user edits workload classifications on the Review page and then navigates to Concerns, they see updated findings immediately — no stale cache.

3. **Ruff auto-fix applied**: Two lint issues were auto-fixed by ruff:
   - `SIM117`: Combined nested `with layout(...):` + `ui.column()` into a single combined `with` statement
   - `I001`: Import order sorted alphabetically (concerns moved above layout_page in main.py)

## i18n Keys Added

| Section | Count | Examples |
|---------|-------|---------|
| `layout.*` | 1 | `concerns` |
| `concerns.*` | 11 | `title`, `no_data`, `summary_critical`, `section_data_quality`, `affected_vms` |
| `health.*` | 14 | `missing_os`, `zero_provisioned`, `high_powered_off_ratio`, `very_old_hw_version`, `tools_not_installed` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff lint: SIM117 and I001 in generated files**
- **Found during:** Task 2 and Task 3 verification
- **Issue:** ruff flagged `SIM117` (use `with A, B:` instead of nested `with A: with B:`) in concerns.py, and `I001` (unsorted imports) in main.py
- **Fix:** Applied `ruff check --fix` — both issues resolved automatically by ruff
- **Files modified:** `src/store_predict/ui/pages/concerns.py`, `src/store_predict/main.py`
- **Commits:** incorporated into task commits (concerns.py was fixed before commit)

### Pre-existing Test Failure (Out of Scope)

`tests/test_llm_classifier.py::test_llm_config_max_concurrent_default` was already failing before this plan's changes (asserts `max_concurrent == 5`, gets `1`). Logged to deferred items — not caused by this plan.

## Verification Results

| Check | Status |
|-------|--------|
| i18n key parity (yaml assertion) | PASSED |
| `concerns.py` import | PASSED |
| `ruff check concerns.py` | PASSED |
| `mypy concerns.py` | PASSED |
| No `classify_dataframe` in concerns.py | PASSED (0 matches) |
| `load_session_data` used in concerns.py | PASSED (2 matches: import + call) |
| No `app.storage` in concerns.py | PASSED (0 matches) |
| `layout.concerns` in layout.py | PASSED |
| `store_predict.ui.pages.concerns` in main.py | PASSED |
| `ruff check layout.py main.py` | PASSED |
| All module imports together | PASSED |
| `run_health_checks(None).has_data is False` | PASSED |
| Full test suite (386 tests) | PASSED (0 regressions) |

## Self-Check: PASSED

Files created/modified verified to exist:
- `/Users/fjacquet/Projects/store-predict/src/store_predict/ui/pages/concerns.py` — FOUND
- `/Users/fjacquet/Projects/store-predict/src/store_predict/ui/layout.py` — FOUND (modified)
- `/Users/fjacquet/Projects/store-predict/src/store_predict/main.py` — FOUND (modified)
- `/Users/fjacquet/Projects/store-predict/src/store_predict/i18n/locales/en.yaml` — FOUND (modified)
- `/Users/fjacquet/Projects/store-predict/src/store_predict/i18n/locales/fr.yaml` — FOUND (modified)

Commits verified:
- `1932f49` — feat(21-02): add i18n keys for concerns and health sections
- `7662f5a` — feat(21-02): create /concerns health check page
- `8bf67f0` — feat(21-02): wire /concerns nav link and route registration
