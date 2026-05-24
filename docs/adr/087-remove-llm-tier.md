# ADR-087: Remove the Dormant LLM Classification Tier

**Status:** Accepted — 2026-05-24

## Context

ADR-084 retired the LLM classification tier from the active pipeline and kept
the module dormant, anticipating that a future cleanup pass would finish the
job. ADR-082 and ADR-085 established the semantic-router (FastEmbed) classifier
as the sole AI-assisted tier. With v10 fully shipped, the dormant LLM code now
only adds surface area: a 20 KB pipeline module (`llm_classifier.py`), a service
config (`llm_config.py`), an AI-classification toggle in the upload UI, a
rule-suggestions panel in the review UI, session-state helpers for LLM
suggestions, `LLM_*` env vars in `.env.example`, and a direct `litellm` entry in
`pyproject.toml` dependencies.

`litellm` is also pulled in transitively by `semantic-router`, so removing our
direct dependency does not evict it from the environment.

## Decision

Fully remove:

- `src/store_predict/pipeline/llm_classifier.py`
- `src/store_predict/services/llm_config.py`
- The AI-classification toggle (`upload.llm_toggle` / `llm_cfg` block) from the
  upload page
- The rule-suggestions panel (`_build_rule_suggestions_panel`) from the review
  page
- `get_llm_ui_enabled`, `set_llm_ui_enabled`, `save_rule_suggestions`,
  `load_rule_suggestions` from `state.py`
- All `llm:` and `rule_suggestions:` i18n blocks and `upload.llm_toggle`,
  `upload.llm_disabled_hint`, `tooltip.llm_toggle` keys from all four locales
  (EN / FR / DE / IT)
- The `LLM_*` env-var section from `.env.example`
- The `litellm>=1.83.7` direct dependency from `pyproject.toml`

`litellm` remains available as a transitive dependency of `semantic-router` and
is not force-removed from the lock file.

## Consequences

- **Smaller attack surface**: one fewer dependency to audit and one fewer config
  surface (`LLM_*` env vars are no longer read).
- **Simpler UI**: the upload page no longer shows a toggle that was always
  disabled in standard deployments.
- **No functional regression**: the semantic-router tier (ADR-082) handles all
  AI-assisted classification. Rule-based overrides remain first priority.
- **Breaking for existing `.env` files**: any `LLM_*` env vars are now silently
  ignored (no code reads them). This is safe — they had no effect since ADR-084.
