"""FR/EN language toggle button for the shared header."""
from __future__ import annotations

from nicegui import ui

from store_predict.i18n import t
from store_predict.i18n.locale import get_locale, set_locale


def add_locale_toggle() -> None:
    """Add FR/EN language toggle button to the current layout container.

    The button label shows the language you will SWITCH TO (not current),
    which is the standard UX convention (same as Wikipedia, Google, etc.).

    Clicking writes the new locale to app.storage.tab and reloads the page.
    Full page reload is required because:
    - ui.header cannot be inside @ui.refreshable (NiceGUI 1.5+ limitation)
    - AG Grid does not support dynamic localeText updates on existing grid instances
    """
    current = get_locale()
    next_locale = "en" if current == "fr" else "fr"
    label = t("layout.language")  # "FR" (when current=en) or "EN" (when current=fr)

    def _switch() -> None:
        set_locale(next_locale)
        ui.run_javascript("location.reload()")

    ui.button(label, on_click=_switch).props("flat color=white dense")
