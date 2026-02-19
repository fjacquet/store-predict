# ADR-008: Tab Storage for Data, User Storage for Preferences

**Status:** Accepted
**Date:** 2026-02-18

## Context

NiceGUI offers `app.storage.tab` (per-tab) and `app.storage.user` (per-user, cross-tab) for session state. Upload data and user preferences need different scoping.

## Decision

Use `app.storage.tab` for upload data (DataFrame, project name) and `app.storage.user` for preferences (dark mode).

## Rationale

- Multiple browser tabs should maintain independent upload sessions
- Dark mode preference should persist across tabs and page navigations
- DataFrames are serialized as `list[dict]` via `.to_dict(orient="records")`

## Consequences

- Each tab has its own upload data — no cross-tab data sharing
- Dark mode setting applies globally per user
- DataFrame serialization adds overhead but ensures JSON compatibility
