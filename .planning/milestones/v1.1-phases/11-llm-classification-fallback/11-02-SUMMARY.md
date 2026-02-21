---
phase: 11-llm-classification-fallback
plan: "02"
subsystem: ui
tags: [llm, i18n, docker-compose, nicegui, litellm, openrouter]

requires:
  - phase: 11-01
    provides: classify_unknown_vms_async function and LLMConfig pydantic-settings service

provides:
  - LLM fallback wired into upload pipeline (conditional on LLM_ENABLED env var)
  - 4 i18n keys in llm: section for both en.yaml and fr.yaml
  - docker-compose.yml env_file support and LLM_* env var stubs
  - .env.example for operator onboarding

affects: [upload-pipeline, docker-deployment, i18n]

tech-stack:
  added: []
  patterns:
    - "Conditional async call pattern: check config.enabled before calling async LLM fallback"
    - "env_file required: false in docker-compose for optional .env overlay"

key-files:
  created:
    - .env.example
  modified:
    - src/store_predict/ui/pages/upload.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - docker-compose.yml

key-decisions:
  - "type: ignore[assignment] on df.to_dict(orient='records') annotation — pandas returns dict[Hashable, Any] but keys are always str at runtime"
  - "LLM block uses separate drr_table_for_llm instance; downstream drr_table for DRR column lookup is a separate load"
  - ".env.example tracked in git; .env already excluded via .gitignore"

patterns-established:
  - "LLM fallback gate: check llm_cfg.enabled before any LLM call — feature never active in CI"
  - "User notification pattern: ui.notify(t('llm.classifying')) before async LLM pass, then count notify after"

requirements-completed: [LLM-01, LLM-05]

duration: 8min
completed: 2026-02-20
---

# Phase 11 Plan 02: LLM Upload Wiring Summary

**LLM classification fallback wired into upload pipeline with i18n notifications, docker-compose env stubs, and .env.example operator guide**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20T12:41:54Z
- **Completed:** 2026-02-20T12:49:50Z
- **Tasks:** 2
- **Files modified:** 5 (en.yaml, fr.yaml, docker-compose.yml, upload.py, .env.example created)

## Accomplishments

- Added `llm:` section with 4 keys to both en.yaml (English) and fr.yaml (real French translations)
- Updated docker-compose.yml with `env_file` (`.env`, required: false) and LLM_* env vars with OpenRouter/Mistral defaults
- Created `.env.example` tracked in git for operator onboarding
- Wired `classify_unknown_vms_async` into `_handle_upload()` with conditional guard on `llm_cfg.enabled`
- 207 tests pass, ruff clean, mypy clean

## Task Commits

Each task was committed atomically:

1. **Task 1: i18n keys, docker-compose env stubs, and .env.example** - `de76318` (feat)
2. **Task 2: Wire LLM classifier into upload pipeline** - `0f05c64` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `src/store_predict/i18n/locales/en.yaml` - Added llm: section with 4 keys
- `src/store_predict/i18n/locales/fr.yaml` - Added llm: section with 4 real French translations
- `docker-compose.yml` - Added env_file block and LLM_ENABLED/LLM_MODEL/LLM_API_KEY/LLM_API_BASE env vars
- `.env.example` - New file: operator guide with commented LLM config block pointing to OpenRouter
- `src/store_predict/ui/pages/upload.py` - Added LLM fallback block after classify_dataframe, imports LLMConfig and classify_unknown_vms_async

## Decisions Made

- Used `type: ignore[assignment]` on `df.to_dict(orient="records")` line — pandas type stub returns `dict[Hashable, Any]` but keys are always strings at runtime; annotation narrowing needed for downstream type safety
- LLM block uses a separate `drr_table_for_llm` instance to pass to classify_unknown_vms_async; the downstream `drr_table` for DRR column lookup is a separate load (matches plan spec)
- `.env.example` tracked in git; `.env` already excluded by existing `.gitignore` entry

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy type narrowing error on df.to_dict()**
- **Found during:** Task 2 (Wire LLM classifier into upload pipeline)
- **Issue:** `df.to_dict(orient="records")` returns `list[dict[Hashable, Any]]` per pandas stubs, but variable typed as `list[dict[str, Any]]` causing mypy assignment error
- **Fix:** Added `# type: ignore[assignment]` inline comment — runtime keys are always str, annotation is correct
- **Files modified:** src/store_predict/ui/pages/upload.py
- **Verification:** mypy reports "Success: no issues found in 1 source file"
- **Committed in:** 0f05c64 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 type annotation bug)
**Impact on plan:** Necessary for mypy compliance. No scope creep.

## Issues Encountered

None beyond the mypy type annotation fix documented above.

## User Setup Required

To enable LLM classification:

1. Copy `.env.example` to `.env`
2. Set `LLM_ENABLED=true`
3. Set `LLM_API_KEY=sk-or-v1-...` (OpenRouter key from https://openrouter.ai)
4. Optionally set `LLM_MODEL` (default: `mistralai/mistral-small-3.1-24b-instruct`)

## Next Phase Readiness

- Phase 11 complete: LLM classification fallback fully wired end-to-end
- Upload pipeline now has opt-in LLM fallback that activates only when LLM_ENABLED=true
- All existing tests pass (207 total); CI unaffected (LLM_ENABLED defaults to false)

## Self-Check: PASSED

- FOUND: .env.example
- FOUND: src/store_predict/i18n/locales/en.yaml (llm: section present)
- FOUND: src/store_predict/i18n/locales/fr.yaml (llm: section present)
- FOUND: docker-compose.yml (LLM_ENABLED, LLM_MODEL, LLM_API_KEY, LLM_API_BASE present)
- FOUND: .planning/phases/11-llm-classification-fallback/11-02-SUMMARY.md
- FOUND commit de76318 (Task 1: i18n + docker-compose + .env.example)
- FOUND commit 0f05c64 (Task 2: upload.py wiring)
- 207 tests pass, ruff clean, mypy clean

---
*Phase: 11-llm-classification-fallback*
*Completed: 2026-02-20*
