---
phase: 19-batch-llm-classification
plan: 01
subsystem: pipeline
tags: [llm, litellm, batch, classification, async]

# Dependency graph
requires:
  - phase: none
    provides: "existing llm_classifier.py with classify_single_vm and classify_unknown_vms_async"
provides:
  - "classify_batch_vms() for sending N VMs in one LLM call"
  - "_parse_batch_response() for JSON array LLM response parsing"
  - "_chunks() helper for list partitioning"
  - "LLMConfig.batch_size field (default 10, env LLM_BATCH_SIZE)"
  - "classify_unknown_vms_async() refactored to use batch chunking"
affects: [19-02-adaptive-batch]

# Tech tracking
tech-stack:
  added: []
  patterns: ["prompt-level batching with JSON array request/response"]

key-files:
  created: []
  modified:
    - src/store_predict/services/llm_config.py
    - src/store_predict/pipeline/llm_classifier.py
    - tests/test_llm_classifier.py

key-decisions:
  - "_chunks returns list[list] not generator — simpler for asyncio.gather consumption"
  - "max_tokens scaled by batch_size * 60 to accommodate JSON array response"
  - "Circuit breaker treats one batch as one failure event (not N failures)"

patterns-established:
  - "Batch LLM prompt: JSON array input, JSON array output with id-based mapping"

requirements-completed: [BATCH-LLM]

# Metrics
duration: 5min
completed: 2026-02-21
---

# Phase 19 Plan 01: Batch LLM Classification Summary

**Prompt-level batch classification sending N VMs per LLM call with JSON array request/response and configurable batch_size**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-21T11:41:16Z
- **Completed:** 2026-02-21T11:46:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- LLMConfig extended with batch_size=10 (env LLM_BATCH_SIZE)
- classify_batch_vms() sends batch JSON prompt, parses JSON array response with validation
- classify_unknown_vms_async() refactored from per-VM to chunked batch calls
- 9 new tests covering config, parsing, disabled-mode, and helper functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend LLMConfig and implement classify_batch_vms()** - `a7bf391` (feat)
2. **Task 2: Add batch classification tests** - `3010659` (test)

## Files Created/Modified
- `src/store_predict/services/llm_config.py` - Added batch_size field with LLM_BATCH_SIZE env var
- `src/store_predict/pipeline/llm_classifier.py` - Added _BATCH_SYSTEM_PROMPT, _parse_batch_response, classify_batch_vms, _chunks; refactored classify_unknown_vms_async to use batch chunking
- `tests/test_llm_classifier.py` - 9 new tests for batch config, parsing, disabled-mode, chunks helper

## Decisions Made
- _chunks returns list[list] not generator for simpler asyncio.gather consumption
- max_tokens scaled by batch_size * 60 to accommodate JSON array response
- Circuit breaker treats one batch as one failure event (not N individual failures)
- classify_single_vm preserved unchanged as public API

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff B905 zip-without-strict**
- **Found during:** Task 1 (implementation)
- **Issue:** ruff flagged `zip(chunk, results)` without `strict=True`
- **Fix:** Added `strict=True` to the zip call
- **Files modified:** src/store_predict/pipeline/llm_classifier.py
- **Verification:** ruff check clean
- **Committed in:** a7bf391 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor lint fix, no scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Batch classification core is complete
- Ready for Phase 19-02 (adaptive batch sizing, metrics, integration tests)

---
*Phase: 19-batch-llm-classification*
*Completed: 2026-02-21*
