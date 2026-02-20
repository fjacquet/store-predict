---
phase: 08-i18n-foundation
plan: "01"
subsystem: i18n
tags: [python-i18n, yaml, localization, fr, en, locale, nicegui]

# Dependency graph
requires: []
provides:
  - "t() translation helper backed by python-i18n YAML files"
  - "get_locale() / set_locale() tab-scoped session helpers"
  - "English YAML locale file (73 strings, 8 namespaces)"
  - "French YAML locale file (73 strings, 8 namespaces)"
  - "add_locale_toggle() FR/EN toggle button component"
  - "python-i18n[YAML] declared in pyproject.toml"
affects:
  - 08-02-wrap-upload
  - 08-03-wrap-review-report
  - all future plans using t() for UI strings

# Tech tracking
tech-stack:
  added: [python-i18n==0.3.9, PyYAML (via python-i18n[YAML])]
  patterns:
    - "t() reads locale per call from app.storage.tab (tab-scoped, NiceGUI safe)"
    - "get_locale() catches RuntimeError for pytest safety outside NiceGUI context"
    - "YAML locale files use %{variable_name} placeholder syntax"
    - "layout.language key shows switch-target language (FR in en.yaml, EN in fr.yaml)"
    - "Lazy import of get_locale() inside t() to avoid circular imports"

key-files:
  created:
    - src/store_predict/i18n/__init__.py
    - src/store_predict/i18n/locale.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - src/store_predict/ui/components/locale_toggle.py
  modified:
    - pyproject.toml

key-decisions:
  - "Default locale is 'fr' (French) per CLAUDE.md — primary user language"
  - "t() sets python-i18n process-global locale per call — safe in NiceGUI single-threaded async"
  - "Full page reload on locale switch (location.reload()) required because ui.header cannot be in @ui.refreshable"
  - "skip_locale_root_data=True so YAML keys are not prefixed with locale name"
  - "python-i18n[YAML]>=0.3.9 and i18n/locales/*.yaml added to package-data for distribution"

patterns-established:
  - "i18n pattern: t('namespace.key', param=value) for all UI strings going forward"
  - "RuntimeError guard in get_locale() for pytest compatibility without NiceGUI server"

requirements-completed: [I18N-01, I18N-02]

# Metrics
duration: 8min
completed: 2026-02-20
---

# Phase 08 Plan 01: i18n Foundation Summary

**python-i18n[YAML] infrastructure with t() helper, 73-string EN/FR YAML locale files, and locale_toggle component — all 145 tests still passing**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20T03:34:36Z
- **Completed:** 2026-02-20T03:42:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- i18n package created with t() helper reading locale from app.storage.tab on every call
- get_locale() / set_locale() tab-scoped helpers with RuntimeError guard for pytest safety
- 73-string English YAML covering all 8 UI namespaces (upload, review, report, columns, stats, pdf, layout, dialog)
- 73-string French YAML with identical key structure and native French translations
- add_locale_toggle() FR/EN button component that writes to tab storage and triggers page reload
- All 145 existing tests continue to pass; ruff and mypy report zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add python-i18n dependency and create i18n package** - `7d52370` (feat)
2. **Task 2: Write YAML locale files and locale_toggle component** - `28743c2` (feat)

## Files Created/Modified
- `pyproject.toml` - Added python-i18n[YAML]>=0.3.9 dependency, i18n/locales/*.yaml package-data, mypy override for i18n.*
- `src/store_predict/i18n/__init__.py` - t() helper with lazy get_locale() import, python-i18n configuration
- `src/store_predict/i18n/locale.py` - get_locale() with RuntimeError fallback to 'fr', set_locale() for tab storage
- `src/store_predict/i18n/locales/en.yaml` - 73 English strings across 8 namespaces
- `src/store_predict/i18n/locales/fr.yaml` - 73 French strings across 8 namespaces
- `src/store_predict/ui/components/locale_toggle.py` - add_locale_toggle() with page-reload on switch

## Decisions Made
- Default locale set to 'fr' (French) — CLAUDE.md specifies French as primary use case
- t() sets python-i18n process-global locale per call — safe because NiceGUI's async loop is single-threaded, no coroutine interleaving within one synchronous t() call
- Full page reload on locale switch required: ui.header cannot be inside @ui.refreshable (NiceGUI 1.5+ limitation), and AG Grid does not support dynamic localeText updates
- skip_locale_root_data=True so YAML keys are not prefixed with locale name (e.g., 'upload.title' not 'fr.upload.title')
- Lazy import of get_locale() inside t() avoids circular import between i18n/__init__.py and i18n/locale.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all verification checks passed on first attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- t() helper fully operational and tested
- Both YAML locale files complete with all 73 strings in both languages
- locale_toggle component ready to be added to the shared header in plan 08-02 or 08-03
- Plans 08-02 and 08-03 can immediately begin wrapping UI strings with t() calls

---
*Phase: 08-i18n-foundation*
*Completed: 2026-02-20*
