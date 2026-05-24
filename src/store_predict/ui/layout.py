"""Shared layout components for the NiceGUI app."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from nicegui import ui

from store_predict.i18n import t
from store_predict.ui.components.dark_mode_toggle import add_dark_mode_toggle
from store_predict.ui.components.locale_toggle import add_locale_toggle
from store_predict.ui.theme import apply_theme

if TYPE_CHECKING:
    from collections.abc import Iterator

# Primary navigation: (i18n key, route). Single source so the header stays in sync.
_NAV_LINKS: tuple[tuple[str, str], ...] = (
    ("layout.home", "/"),
    ("layout.upload", "/upload"),
    ("layout.scope", "/scope"),
    ("layout.review", "/review"),
    ("layout.report", "/report"),
    ("layout.layout", "/layout"),
    ("layout.concerns", "/concerns"),
    ("layout.compute", "/compute"),
)


@contextmanager
def layout(title: str = "StorePredict") -> Iterator[None]:
    """Shared page layout with header, navigation and locale/dark mode toggles."""
    apply_theme()
    with ui.header().classes("sp-header items-center justify-between px-6 py-3"):
        ui.html('<span class="sp-brand">Store<span class="sp-accent">Predict</span></span>')
        with ui.row().classes("gap-5 items-center"):
            for key, route in _NAV_LINKS:
                ui.link(t(key), route).classes("sp-nav-link")
            add_dark_mode_toggle()
            add_locale_toggle()
    yield
