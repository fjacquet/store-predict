# ADR-043: i18n Architecture — Per-Call Locale via t() Wrapper with YAML Files

**Status:** Accepted
**Date:** 2026-02-20

## Context

StorePredict needed to support French and English UI. The primary use case is French (pre-sales in France); English is secondary. Requirements were: minimal dependency weight, YAML locale files (easier to maintain than .po files), and compatibility with NiceGUI's async event loop.

Options evaluated: `python-i18n[YAML]`, Babel/gettext, custom dict approach, and Flask-Babel.

## Decision

Use `python-i18n[YAML]` with a thin `t()` wrapper that sets the process-global locale per call, reading the locale from `app.storage.tab['locale']`.

```python
def t(key: str, **kwargs: object) -> str:
    from store_predict.i18n.locale import get_locale
    locale = get_locale()
    i18n.set("locale", locale)
    return str(i18n.t(key, **kwargs))
```

YAML files live at `src/store_predict/i18n/locales/{en,fr}.yaml` with `skip_locale_root_data: True` so keys are accessed without a locale prefix (e.g., `t("review.title")` not `t("fr.review.title")`).

## Rationale

- **python-i18n is lightweight**: No Babel/gettext compilation step, no `.po`/`.mo` files, no Babel CLI dependency
- **YAML is readable**: Translators can edit YAML without tooling; nested structure mirrors UI hierarchy
- **Per-call locale is safe**: NiceGUI's async event loop is single-threaded. Each request handler runs to completion before the next fires. Setting `i18n.set("locale")` immediately before `i18n.t()` within the same synchronous call stack is safe — there is no context switch between the two calls
- **`app.storage.tab` isolation**: Each browser tab has its own locale preference, naturally supporting users with different language preferences in the same server process

## Alternatives Considered

- **Babel/gettext**: Requires compilation, `.po` file tooling, separate extraction step. Overkill for 2 languages and ~100 strings
- **Custom dict approach**: No interpolation support, no pluralization, manual maintenance
- **Flask-Babel**: Flask dependency, incompatible with NiceGUI

## Consequences

- All user-facing strings must go through `t()` — hardcoded strings in new features will be caught by code review
- The `i18n` package has no `py.typed` marker; `pyrightconfig.json` needs `reportMissingModuleSource: false`
- Adding a third language requires only a new `{lang}.yaml` file and a UI toggle option
- `get_locale()` catches `RuntimeError` for pytest safety (no NiceGUI app context in tests)
