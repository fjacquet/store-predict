---
phase: 11-llm-classification-fallback
verified: 2026-02-20T15:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 11: LLM Classification Fallback Verification Report

**Phase Goal:** Use LLM to classify VMs that the rules engine marks as "Unknown Reducible", with configurable provider support.
**Verified:** 2026-02-20
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LLMConfig reads enabled/model/api_key/api_base/timeout from LLM_* env vars | VERIFIED | `LLMConfig(BaseSettings)` with `SettingsConfigDict(env_prefix="LLM_")`, all 6 fields present at llm_config.py:47-54 |
| 2 | LLM_ENABLED defaults to false with no env var set | VERIFIED | `enabled: bool = False` at llm_config.py:49; test `test_llm_disabled_by_default` confirms |
| 3 | API key never appears in repr() or str() of LLMConfig | VERIFIED | `api_key: SecretStr` at llm_config.py:51; test `test_api_key_not_exposed_in_repr` confirmed passing |
| 4 | classify_unknown_vms_async returns records unchanged when config.enabled is False | VERIFIED | `if not config.enabled: return records` at llm_classifier.py:139; tests confirm |
| 5 | classify_single_vm returns None when LLM response is not in valid_categories set | VERIFIED | `return raw if raw in valid_categories else None` at llm_classifier.py:105 |
| 6 | Circuit breaker opens after 3 failures and skips calls for 60s cooldown | VERIFIED | `_CB_FAIL_MAX=3`, `_CB_COOLDOWN=60.0` at llm_classifier.py:37-38; check at line 70; open at line 109 |
| 7 | All LLM calls use asyncio.wait_for with 30s timeout | VERIFIED | `await asyncio.wait_for(litellm.acompletion(...), timeout=config.timeout)` at llm_classifier.py:92-101; `timeout: int = 30` default |
| 8 | VM name and OS truncated and newlines stripped before building prompt | VERIFIED | `safe_vm = vm_name[:100].replace("\n", " ").replace("\r", " ")` at llm_classifier.py:74; same for os_name (50 chars) at line 75 |
| 9 | upload.py conditionally calls classify_unknown_vms_async when LLM_ENABLED=true | VERIFIED | `llm_cfg = LLMConfig(); if llm_cfg.enabled: ... await classify_unknown_vms_async(...)` at upload.py:63-68 |
| 10 | UI notifies user during LLM classification with i18n strings; all 4 llm: keys in both locales | VERIFIED | `ui.notify(t("llm.classifying"))` at upload.py:65; all 4 keys present in en.yaml:111-115 and fr.yaml:111-115 with real French |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/store_predict/services/llm_config.py` | LLMConfig BaseSettings with SecretStr api_key | VERIFIED | 65 lines; exports `LLMConfig` and `get_llm_config`; SecretStr masking; lru_cache singleton |
| `src/store_predict/pipeline/llm_classifier.py` | classify_unknown_vms_async and classify_single_vm | VERIFIED | 174 lines; both functions implemented with circuit breaker, semaphore concurrency, prompt injection mitigation |
| `tests/test_llm_classifier.py` | Unit tests (min 60 lines) | VERIFIED | 69 lines; 7 test functions; all 7 pass |
| `src/store_predict/ui/pages/upload.py` | LLM classification call after classify_dataframe | VERIFIED | Contains `classify_unknown_vms_async` import and conditional await call at lines 21, 68 |
| `src/store_predict/i18n/locales/en.yaml` | llm: section with 4 keys | VERIFIED | Lines 111-115; all 4 keys: classifying, classified_notify, unavailable, disabled |
| `src/store_predict/i18n/locales/fr.yaml` | French translations for all llm: keys | VERIFIED | Lines 111-115; real French translations (not English copies) |
| `docker-compose.yml` | LLM_ENABLED and LLM_* env vars with defaults | VERIFIED | Lines 6, 12-15; env_file block and all 4 LLM_* env vars with OpenRouter/Mistral defaults |
| `.env.example` | Commented LLM config block for operator reference | VERIFIED | File exists; contains commented LLM_ENABLED, LLM_API_KEY, LLM_MODEL, LLM_API_BASE |
| `.gitignore` | .env excluded | VERIFIED | `.env` at line 46; `.env.local` at line 47 |
| `pyproject.toml` | pydantic-settings dep and mypy overrides | VERIFIED | `pydantic-settings>=2.13.0,<3.0` at line 20; litellm mypy override at line 91; pydantic_settings override at line 95 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/store_predict/pipeline/llm_classifier.py` | `src/store_predict/services/llm_config.py` | TYPE_CHECKING import of LLMConfig | VERIFIED | `from store_predict.services.llm_config import LLMConfig` in TYPE_CHECKING block at llm_classifier.py:28; used in function signatures |
| `src/store_predict/pipeline/llm_classifier.py` | `litellm.acompletion` | asyncio.wait_for | VERIFIED | `await asyncio.wait_for(litellm.acompletion(...), timeout=config.timeout)` at lines 92-101 (multi-line call — correct implementation) |
| `src/store_predict/ui/pages/upload.py` | `src/store_predict/pipeline/llm_classifier.py` | await classify_unknown_vms_async | VERIFIED | Import at line 21; `await classify_unknown_vms_async(vm_records, drr_table_for_llm, llm_cfg)` at line 68 |
| `src/store_predict/ui/pages/upload.py` | `src/store_predict/services/llm_config.py` | LLMConfig() conditional check | VERIFIED | Import at line 25; `llm_cfg = LLMConfig(); if llm_cfg.enabled:` at lines 63-64 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LLM-01 | 11-02 | Unknown VMs sent to LLM for classification | SATISFIED | upload.py calls classify_unknown_vms_async after classify_dataframe; records with classification_confidence=="default" are processed |
| LLM-02 | 11-01 | LLM provider configurable via env vars (litellm supports OpenAI/Anthropic/Ollama/OpenRouter) | SATISFIED | LLMConfig reads LLM_MODEL, LLM_API_KEY, LLM_API_BASE; litellm.acompletion used as multi-provider abstraction |
| LLM-03 | 11-01 | LLM disabled by default, opt-in via LLM_ENABLED | SATISFIED | `enabled: bool = False`; default verified in test and by code inspection |
| LLM-04 | 11-01 | Async non-blocking with 30s timeout and circuit breaker | SATISFIED | asyncio.wait_for at line 92; 30s default; circuit breaker with 3-failure threshold and 60s cooldown |
| LLM-05 | 11-02 | Classification source in AG Grid (rules/LLM/manual) | SATISFIED | classification_confidence set to "llm" at llm_classifier.py:162; existing AG Grid column passes through value |
| LLM-06 | 11-01 | LLM responses validated against known DRR categories | SATISFIED | `return raw if raw in valid_categories else None` at llm_classifier.py:105; hallucinated categories rejected |
| LLM-07 | 11-01 | API keys via pydantic-settings SecretStr, never logged or exposed | SATISFIED | `api_key: SecretStr`; NEVER logged (only count-level messages logged); test confirms not in repr() or str() |

All 7 requirements satisfied. No orphaned requirements.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No anti-patterns found. No TODO/FIXME/placeholder comments in any LLM-related source files. No empty implementations. No stub handlers.

---

### Human Verification Required

#### 1. LLM Classification End-to-End with Real API Key

**Test:** Copy `.env.example` to `.env`, set `LLM_ENABLED=true` and a real OpenRouter API key (`LLM_API_KEY=sk-or-v1-...`). Upload an RVTools file containing VMs that match "Unknown Reducible". After upload, check the review table.
**Expected:** AG Grid shows `classification_confidence = "llm"` for VMs that were unclassified by rules; a positive notification "AI classified N VM(s)" appears; `classification_confidence = "rule_match"` records are unchanged.
**Why human:** Requires a live LLM API key and real network call; cannot verify LLM provider connectivity programmatically in CI.

#### 2. LLM Unavailable Error Handling (UI)

**Test:** Set `LLM_ENABLED=true` with an invalid API key (`LLM_API_KEY=invalid`). Upload a file with unknown VMs.
**Expected:** The upload still completes (circuit breaker or exception handled internally); VMs remain as "Unknown Reducible"; no crash; ideally the UI shows a warning using `t("llm.unavailable")`.
**Why human:** The `t("llm.unavailable")` key exists in i18n but is not wired in upload.py (only `classifying` and `classified_notify` are used). This may be intentional (errors are swallowed silently) but should be human-confirmed as acceptable UX.

#### 3. Docker Compose LLM Integration

**Test:** Run `docker compose up --build` with `.env` containing `LLM_ENABLED=true`. Verify the container reads the env vars correctly from the env_file overlay.
**Expected:** Container starts; LLM feature activates when file is uploaded with unknown VMs.
**Why human:** Requires Docker environment and live configuration; cannot verify container env var injection programmatically.

---

## Gaps Summary

No gaps. All automated checks passed.

The only observation (not a gap) is that `t("llm.unavailable")` and `t("llm.disabled")` i18n keys exist in both locale files but are not called from upload.py — they are available for future error surfacing. The current behavior silently swallows LLM failures and returns records unchanged, which is the documented design (circuit breaker handles this internally). This is consistent with the plan's statement: "The existing `except IngestionError` and `except Exception` blocks in `_handle_upload` already catch LLM failures."

---

## Test Results

- **LLM unit tests:** 7/7 passed (`tests/test_llm_classifier.py`)
- **Full test suite:** 207 passed, 1 skipped, 0 failed
- **mypy:** No issues on `llm_config.py`, `llm_classifier.py`, `upload.py`
- **ruff:** No issues on all LLM-related source files

---

_Verified: 2026-02-20_
_Verifier: Claude (gsd-verifier)_
