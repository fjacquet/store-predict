# ADR-020: Dark Mode in app.storage.user (Per-User)

**Status:** Accepted
**Date:** 2026-02-19

## Context

NiceGUI provides two scoped storage namespaces: `app.storage.tab` (per browser tab, cleared on close) and `app.storage.user` (persists across tabs and restarts via cookie).

## Decision

Store the dark mode preference in `app.storage.user`.

## Rationale

- Dark mode is a personal preference, not a per-upload workflow setting
- Users expect their UI theme to persist when they open a new tab or return the next day
- Decoupled from `app.storage.tab`, which holds upload state that must reset per session

## Alternatives Considered

- **app.storage.tab:** Resets on each new tab; user must toggle dark mode repeatedly

## Consequences

- Dark mode preference is tied to the browser cookie identity, not a login account
- Clearing browser cookies resets the preference (acceptable UX trade-off)
- See ADR-008 for the broader session storage split strategy
