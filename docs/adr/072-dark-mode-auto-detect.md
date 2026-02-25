# ADR-072: Auto-Detect OS Dark Mode on First Visit

**Status:** Accepted
**Date:** 2026-02-25
**Amends:** ADR-020

## Context

ADR-020 established that the dark mode preference is persisted in `app.storage.user`.
The initial implementation defaulted to **light mode** on first visit — `app.storage.user["dark_mode"]`
is absent for new users, `ui.dark_mode()` receives `None` via `bind_value`, which NiceGUI
interprets as "auto", but the bound `ui.switch` appears as *off* (falsy), giving no visual
cue and leaving users on light mode even when their OS is in dark mode.

Pre-sales engineers frequently use StorePredict on MacBooks in dark mode. Having to
manually toggle the switch on every fresh session degrades the experience.

## Decision

On first visit (no `"dark_mode"` key in `app.storage.user`), call `ui.dark_mode().auto()`
explicitly before binding. This signals NiceGUI to honour the browser's
`prefers-color-scheme` media query, applying dark or light mode automatically to match
the OS setting.

```python
dark = ui.dark_mode()
if "dark_mode" not in app.storage.user:
    dark.auto()
dark.bind_value(app.storage.user, "dark_mode")
```

Once the user explicitly toggles the switch, `True` or `False` is written to storage and
auto-detection is no longer applied on subsequent visits.

## Rationale

- `ui.dark_mode().auto()` is a first-class NiceGUI API — no JavaScript or CSS hacks required.
- The stored preference (ADR-020) is still respected: `if "dark_mode" not in storage` ensures
  auto-detect only runs when no explicit choice has been made.
- Clearing browser cookies resets to auto-detect, which is the correct default.

## Alternatives Considered

- **Set default to `True` (always dark):** Forces dark mode on users who prefer light. Rejected.
- **Read `prefers-color-scheme` via JavaScript and write to storage:** More complex; the
  NiceGUI `.auto()` API achieves the same outcome natively. Rejected.

## Consequences

- First-time visitors automatically match their OS theme with zero interaction required.
- The manual toggle switch remains for users who want to override the OS preference.
- The toggle switch shows *off* (falsy) when auto-dark is active and the user has never
  manually set a preference. This is a minor UX imprecision but acceptable given the
  simplicity of the implementation.
