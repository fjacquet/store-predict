"""Shared layout components for the NiceGUI app."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from nicegui import ui

from store_predict.i18n import t
from store_predict.ui.components.dark_mode_toggle import add_dark_mode_toggle
from store_predict.ui.components.locale_toggle import add_locale_toggle

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def layout(title: str = "StorePredict") -> Iterator[None]:
    """Shared page layout with header, navigation and locale/dark mode toggles."""
    with ui.header().classes("bg-blue-900 text-white items-center justify-between"):
        ui.label(title).classes("text-2xl font-bold")
        with ui.row().classes("gap-4 items-center"):
            ui.link(t("layout.home"), "/").classes("text-white no-underline hover:underline")
            ui.link(t("layout.upload"), "/upload").classes("text-white no-underline hover:underline")
            ui.link(t("layout.scope"), "/scope").classes("text-white no-underline hover:underline")
            ui.link(t("layout.review"), "/review").classes("text-white no-underline hover:underline")
            ui.link(t("layout.report"), "/report").classes("text-white no-underline hover:underline")
            ui.link(t("layout.layout"), "/layout").classes("text-white no-underline hover:underline")
            ui.link(t("layout.concerns"), "/concerns").classes("text-white no-underline hover:underline")
            ui.link(t("layout.compute"), "/compute").classes("text-white no-underline hover:underline")
            add_dark_mode_toggle()
            add_locale_toggle()
    yield
