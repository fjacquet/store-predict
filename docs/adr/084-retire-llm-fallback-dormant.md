# ADR-084: Retire LLM Classification from the Active Pipeline (Keep Module Dormant)

**Status:** Accepted
**Date:** 2026-05-23
**Issue:** v10.0.0 — LLM fallback superseded by semantic tier; too slow and fragile for production

## Context

ADR-051 introduced an optional LLM classification fallback (litellm/Ollama) for VMs the
rules engine could not classify. The feature was always opt-in (`LLM_ENABLED=false` default)
and never reached the enabled-by-default state.

In v10.0.0, ADR-082 introduces the semantic-router tier, which fills the classification gap
that the LLM was intended to address — without requiring a running Ollama daemon, without
network latency, and without the parse fragility that plagued LLM responses (reasoning-model
`<think>` blocks, hallucinated category strings, circuit-breaker masking silent failures).

The `llm_classifier.py` module and its companion `llm_config.py` represent real engineering
investment: the circuit-breaker pattern, the batch JSON prompt, the thinking-model strip
logic, the pydantic-settings `SecretStr` hygiene. These artefacts are worth retaining for
two reasons:

1. The LLM integration may be re-enabled in a future release once Ollama deployment is
   co-located with the container (e.g. sidecar pattern), or if a hosted LLM API is available
   in the customer's environment.
2. The tests (`tests/test_llm_classifier.py`) serve as regression coverage for the parse and
   error-path logic independent of any live model.

## Decision

Remove the LLM tier from the **active pipeline** by unwiring it from `upload.py` and the
`_run_pipeline` function. Do **not** delete `llm_classifier.py` or `llm_config.py`. Retain
all existing LLM tests; they must pass (with the circuit breaker opened via a fixture, not
live Ollama calls — see project CLAUDE.md convention on no-live-LLM tests).

Operationally, this means:

- `upload.py` no longer imports or calls `LLMClassifier`.
- `LLM_ENABLED` env var is ignored at runtime (no code reads it in the pipeline path).
- The `litellm` dependency remains in `pyproject.toml` (still needed by the dormant module
  and may be needed by future features).
- The `.env.example` documents that `LLM_ENABLED` has no effect in v10.x.

Re-enabling the LLM tier in a future release is a wiring change in `upload.py` (or
a dedicated optional pipeline stage), not a rewrite.

## Consequences

**Positive:**

- Simpler runtime: no Ollama dependency, no litellm network calls, no circuit-breaker state.
- Upload latency is purely CPU-bound (pandas + ONNX inference), not I/O-bound on an
  external service.
- Deterministic: the same file always produces the same classification result.
- Docker image no longer needs `LLM_API_BASE` / `LLM_MODEL` env vars configured to function
  correctly.

**Negative:**

- Users who had `LLM_ENABLED=true` (rare, given the opt-in default) will find the toggle
  silently ignored. The `.env.example` and release notes document this.
- The `litellm` package remains in the dependency tree (adds ~20 MB to the image) even though
  it is not called at runtime. It can be removed in a future cleanup once there is a
  confirmed decision not to re-enable LLM classification.

## Related

- ADR-051: LLM rule-suggestion feedback loop — the ADR this decision supersedes for the
  active pipeline.
- ADR-082: Semantic-router as primary classifier — the replacement that makes this retirement
  safe.
- ADR-083: FastEmbed offline encoder — eliminates the Ollama runtime dependency entirely.
