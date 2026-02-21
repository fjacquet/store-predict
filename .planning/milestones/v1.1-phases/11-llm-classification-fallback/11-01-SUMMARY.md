---
phase: 11-llm-classification-fallback
plan: "01"
subsystem: api
tags: [litellm, pydantic-settings, async, circuit-breaker, llm, classification]

requires:
  - phase: 03-classification
    provides: DRRTable with category entries used as valid_categories set
  - phase: 10-branding
    provides: no direct dependency, but project structure context

provides:
  - LLMConfig BaseSettings class with SecretStr api_key (llm_config.py)
  - classify_unknown_vms_async async function for LLM-based VM classification
  - classify_single_vm async function with circuit breaker and timeout
  - 7 unit tests for config and classifier (real objects, no mocks)

affects:
  - 11-02 (pipeline wiring — will import classify_unknown_vms_async)
  - upload pipeline (future integration point)

tech-stack:
  added:
    - pydantic-settings>=2.13.0,<3.0 (runtime dependency)
    - litellm (already in deps, now has mypy override)
  patterns:
    - SecretStr for API key storage (never logged/repr'd)
    - Module-level circuit breaker state with monotonic clock
    - TYPE_CHECKING block for DRRTable/LLMConfig imports in pipeline module
    - asyncio.Semaphore for bounded concurrency in async gather
    - lru_cache singleton for config (bypass with direct instantiation in tests)

key-files:
  created:
    - src/store_predict/services/llm_config.py
    - src/store_predict/pipeline/llm_classifier.py
    - tests/test_llm_classifier.py
  modified:
    - pyproject.toml (pydantic-settings dep + litellm/pydantic_settings mypy overrides)

key-decisions:
  - "pydantic-settings BaseSettings with LLM_ env prefix for typed config"
  - "SecretStr for api_key so value never appears in repr() or str()"
  - "DRRTable and LLMConfig in TYPE_CHECKING block in llm_classifier.py (ruff TC001)"
  - "asyncio.TimeoutError unified with Exception catch — UP041 fix replaced asyncio.TimeoutError alias with TimeoutError"
  - "Circuit breaker state as module globals — simple, zero-dependency, thread-safe for single-threaded async"
  - "classify_single_vm returns None on invalid LLM response (not in valid_categories) — conservative sizing"

patterns-established:
  - "LLM_ENABLED=false default — feature opt-in via env var, never active in tests"
  - "Prompt injection mitigation: truncate vm_name (100 chars), os_name (50 chars), strip newlines, system prompt instructs model to treat as data"
  - "No VM names in logs — only count-level info messages"

requirements-completed: [LLM-02, LLM-03, LLM-04, LLM-06, LLM-07]

duration: 12min
completed: 2026-02-20
---

# Phase 11 Plan 01: LLM Classification Engine Summary

**LLMConfig pydantic-settings module and async LLM classifier with circuit breaker, prompt injection mitigation, and 7 unit tests using litellm**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-20T13:53:12Z
- **Completed:** 2026-02-20T14:05:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- LLMConfig BaseSettings class reads 6 env vars (LLM_ENABLED/MODEL/API_KEY/API_BASE/TIMEOUT/MAX_CONCURRENT) with SecretStr masking for the API key
- classify_unknown_vms_async: skips when disabled, filters only "default" confidence records, bounded async concurrency via Semaphore, logs only counts
- classify_single_vm: input sanitization against prompt injection, asyncio.wait_for timeout, circuit breaker (3 failures -> 60s cooldown), response validation against valid_categories
- 7 unit tests passing (207 total suite), mypy strict + ruff clean on both new modules
- pydantic-settings added to runtime dependencies; litellm and pydantic_settings mypy overrides added

## Task Commits

Each task was committed atomically:

1. **Task 1: LLMConfig pydantic-settings module** - `61c7b78` (feat)
2. **Task 2: async LLM classifier with circuit breaker and unit tests** - `8d43f76` (feat)

## Files Created/Modified

- `/Users/fjacquet/Projects/store-predict/src/store_predict/services/llm_config.py` - LLMConfig BaseSettings with SecretStr api_key and get_llm_config() singleton
- `/Users/fjacquet/Projects/store-predict/src/store_predict/pipeline/llm_classifier.py` - classify_single_vm and classify_unknown_vms_async with circuit breaker
- `/Users/fjacquet/Projects/store-predict/tests/test_llm_classifier.py` - 7 unit tests for config and classifier
- `/Users/fjacquet/Projects/store-predict/pyproject.toml` - pydantic-settings dep + mypy overrides

## Decisions Made

- pydantic-settings BaseSettings with LLM_ env prefix: clean typed config without manual os.getenv calls
- SecretStr for api_key: value never appears in repr() or str() — prevents key leakage in logs
- DRRTable and LLMConfig moved to TYPE_CHECKING block in llm_classifier.py per ruff TC001 rule (safe because `from __future__ import annotations` is present)
- asyncio.TimeoutError replaced with TimeoutError per ruff UP041 (Python 3.11+ alias)
- Circuit breaker as module globals: simple, zero-dependency, correct for NiceGUI's single-threaded async model
- classify_single_vm returns None for invalid LLM responses (not in valid_categories) — conservative fallback preserves defensible sizing numbers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unnecessary type: ignore comments causing mypy errors**
- **Found during:** Task 2 verification (mypy run)
- **Issue:** `# type: ignore[arg-type]` and `# type: ignore[union-attr]` on litellm calls triggered `unused-ignore` errors because litellm.* is already ignored via mypy override
- **Fix:** Removed both type: ignore comments
- **Files modified:** src/store_predict/pipeline/llm_classifier.py
- **Verification:** mypy reports "Success: no issues found in 2 source files"
- **Committed in:** 8d43f76 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed ruff TC001 and UP041 linting errors**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** DRRTable/LLMConfig imports not in TYPE_CHECKING block (TC001); asyncio.TimeoutError should be TimeoutError (UP041)
- **Fix:** Moved imports to TYPE_CHECKING block; ruff auto-fixed UP041
- **Files modified:** src/store_predict/pipeline/llm_classifier.py
- **Verification:** ruff check reports no issues
- **Committed in:** 8d43f76 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — code correctness for type checking compliance)
**Impact on plan:** Minor fixes required by the project's strict mypy + ruff configuration. No scope creep.

## Issues Encountered

- pydantic-settings was not yet installed (litellm was already present from a prior phase). Installed via `uv pip install "pydantic-settings>=2.13.0,<3.0"` before writing code.

## User Setup Required

To enable LLM classification, set environment variables:

```bash
LLM_ENABLED=true
LLM_API_KEY=<your OpenRouter key>
LLM_API_BASE=https://openrouter.ai/api/v1
# Optional: use free tier model
LLM_MODEL=mistralai/mistral-small-3.1-24b-instruct:free
```

With no env vars set, the feature is disabled (default) and all 207 tests pass without any LLM credentials.

## Self-Check: PASSED

All created files exist on disk. Both task commits verified in git log.

## Next Phase Readiness

- LLM engine is complete and ready for pipeline wiring (Phase 11 Plan 02)
- classify_unknown_vms_async is the integration point: call it after rule-based classification with the records list
- No API credentials needed for development or CI — feature is off by default

---
*Phase: 11-llm-classification-fallback*
*Completed: 2026-02-20*
