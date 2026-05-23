"""Language selector (EN/FR/DE/IT) for the shared header."""

from __future__ import annotations

from nicegui import ui

from store_predict.i18n.locale import get_locale, set_locale

# (locale code, native name shown in the menu, short label shown on the button)
_LANGUAGES: tuple[tuple[str, str, str], ...] = (
    ("en", "English", "EN"),
    ("fr", "Français", "FR"),
    ("de", "Deutsch", "DE"),
    ("it", "Italiano", "IT"),
)


def add_locale_toggle() -> None:
    """Add an EN/FR/DE/IT language selector to the shared header.

    The button shows the current language; its menu lists all four by native
    name. Choosing one writes the locale to ``app.storage.tab`` and reloads the
    page — a full reload is required because ``ui.header`` can't be refreshable
    and AG Grid can't swap ``localeText`` on an existing grid instance.
    """
    current = get_locale()
    short = next((label for code, _name, label in _LANGUAGES if code == current), current.upper())

    def _switch(code: str) -> None:
        set_locale(code)
        ui.run_javascript("location.reload()")

    with ui.button(short, icon="language").props("flat color=white dense"), ui.menu():
        for code, name, _label in _LANGUAGES:
            item = ui.menu_item(name, on_click=lambda c=code: _switch(c))
            if code == current:
                item.props("active").classes("text-weight-bold")
