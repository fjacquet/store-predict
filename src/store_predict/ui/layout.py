"""Shared layout components for the NiceGUI app."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from nicegui import ui

from store_predict.ui.components.dark_mode_toggle import add_dark_mode_toggle

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def layout(title: str = "StorePredict") -> Iterator[None]:
    """Shared page layout with header, navigation, and dark mode toggle."""
    with ui.header().classes("bg-blue-900 text-white items-center justify-between"):
        ui.label(title).classes("text-2xl font-bold")
        with ui.row().classes("gap-4 items-center"):
            ui.link("Home", "/").classes("text-white no-underline hover:underline")
            ui.link("Upload", "/upload").classes("text-white no-underline hover:underline")
            ui.link("Review", "/review").classes("text-white no-underline hover:underline")
            add_dark_mode_toggle()
    yield
