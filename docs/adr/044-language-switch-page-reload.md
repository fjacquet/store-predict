# ADR-044: Language Switch via Full Page Reload

**Status:** Accepted
**Date:** 2026-02-20

## Context

When a user toggles the FR/EN language switch in the header, all visible UI elements must update to the new language. NiceGUI's reactive UI system (`@ui.refreshable`) is the natural mechanism for this, but it has a constraint: `ui.header` (and its children, including the nav bar and language toggle) cannot be placed inside a `@ui.refreshable` function in NiceGUI 1.5+.

This means the header — which contains nav links and the locale toggle — cannot be dynamically re-rendered without a page reload.

## Decision

Language switching triggers a full browser page reload via `ui.run_javascript('location.reload()')`.

```python
def add_locale_toggle() -> None:
    target_locale = "en" if get_locale() == "fr" else "fr"
    target_label = t("layout.language")  # "EN" when current is FR, "FR" when current is EN

    async def _switch() -> None:
        set_locale(target_locale)
        await ui.run_javascript("location.reload()")

    ui.button(target_label, on_click=_switch).props("flat dense")
```

The new locale is persisted to `app.storage.tab['locale']` before the reload, so the page reloads in the correct language.

## Rationale

- **Correctness over elegance**: A full reload guarantees all elements reflect the new locale — including the header, AG Grid column headers (set at construction time), and any string computed outside the refreshable scope
- **No partial-update bugs**: Partial refresh approaches (refreshing only the body) risk leaving stale strings in the header or in AG Grid
- **Acceptable UX cost**: Language switching is infrequent (done once per session). The reload is fast given the app's small payload
- **AG Grid column headers**: AG Grid community edition does not support dynamic locale switching. Column headers are set at construction time via `t("columns.*")`. A page reload is the only way to re-render them in the new locale

## Alternatives Considered

- **`@ui.refreshable` for entire page body**: Feasible for body content but impossible for `ui.header`. Would still leave header strings stale after language switch
- **Reactive string bindings**: NiceGUI does not support reactive string bindings that would auto-update all `ui.label` elements on a state change
- **Dynamic AG Grid column re-definition**: AG Grid community edition does not expose a public API to replace column definitions after initialization without destroying and recreating the grid (which is equivalent to a page reload anyway)

## Consequences

- Language switch always works correctly for all UI elements
- Slight UX friction on language switch — accepted given the infrequent nature of the action
- I18N-05 requirement wording updated to reflect this constraint: "Language switch updates all visible UI elements (implemented via full page reload — NiceGUI 1.5+ prohibits `ui.header` inside `@ui.refreshable`)"
- If NiceGUI adds support for refreshable headers in a future version, the reload can be replaced with `ui.refreshable` without changing the public API of `add_locale_toggle()`
