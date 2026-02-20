# ADR-054: AI classification toggle is per-session, not a server restart

**Date:** 2026-02-20
**Status:** Accepted

## Context

LLM classification is controlled by the `LLM_ENABLED` environment variable, which
requires a server restart to change. Pre-sales engineers sometimes want to skip the
LLM step for a specific upload (e.g. when working offline, when the LLM API is slow,
or when they trust the rules-based results for a well-known customer environment)
without restarting the application.

## Decision

Add a `ui.switch` on the upload page that enables or disables LLM classification
**per browser session** (tab-scoped). The session flag `app.storage.tab["llm_ui_enabled"]`
defaults to `True` and is respected by the upload handler in addition to the
environment-level `LLMConfig.enabled` check:

```python
if llm_cfg.enabled and _llm_ui_enabled:
    # run LLM classification
```

When `LLM_ENABLED=false` (env var), the switch is rendered but disabled (greyed out)
with a hint label — it is always visible so users understand the feature exists and
know how to activate it at the system level.

The session flag is captured from `app.storage.tab` immediately when the slot context
is available (before the `handle_upload` background task loses direct tab access),
consistent with the existing pattern for `project_name`.

## Consequences

- Server operators retain hard control via `LLM_ENABLED=false`; the UI toggle cannot
  override a disabled LLM configuration.
- The toggle state persists across uploads within the same browser tab session but
  resets to `True` on a fresh tab — the safe default (use AI when available).
- `LLMConfig()` is instantiated once at page render time (not per-upload) to avoid
  re-reading environment variables on every upload, consistent with the existing code.
- No new environment variable or configuration file is needed; the feature is purely
  session-state driven.
