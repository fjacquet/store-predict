"""Per-session locale helpers backed by app.storage.tab."""
from __future__ import annotations

_DEFAULT_LOCALE = "fr"  # French is the primary use-case language


def get_locale() -> str:
    """Return the current tab's locale from NiceGUI session storage.

    Falls back to French (primary user language) when:
    - locale key not yet set in this tab's storage
    - called outside a NiceGUI request context (e.g., pytest, scripts)

    The RuntimeError catch is intentional: it makes every function using t()
    safely callable in unit tests without a live NiceGUI server.
    """
    try:
        from nicegui import app

        return str(app.storage.tab.get("locale", _DEFAULT_LOCALE))
    except RuntimeError:
        # Outside NiceGUI request context (e.g., pytest, CLI scripts)
        return _DEFAULT_LOCALE


def set_locale(locale: str) -> None:
    """Persist locale choice to tab-scoped session storage."""
    from nicegui import app

    app.storage.tab["locale"] = locale


__all__ = ["get_locale", "set_locale"]
