"""StorePredict NiceGUI application entry point."""

from __future__ import annotations

import os

from nicegui import ui

# Import pages to register their routes with NiceGUI
import store_predict.ui.pages.report
import store_predict.ui.pages.report_print
import store_predict.ui.pages.review
import store_predict.ui.pages.upload  # noqa: F401
from store_predict.config import APP_PORT, APP_TITLE
from store_predict.i18n import t


@ui.page("/")
def index_page() -> None:
    """Landing page for StorePredict."""
    from store_predict.ui.layout import layout

    with layout(), ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"):
        ui.label(APP_TITLE).classes("text-4xl font-bold text-blue-900")
        ui.label(t("home.subtitle")).classes("text-xl text-gray-600")
        ui.label(t("home.description")).classes("text-center text-gray-500 max-w-lg")
        ui.button(
            t("home.cta"),
            on_click=lambda: ui.navigate.to("/upload"),
        ).classes("bg-blue-700 text-white")


def main() -> None:
    """Start the NiceGUI application."""
    storage_secret = os.environ.get("STORAGE_SECRET", "dev-only-not-for-production")
    ui.run(
        title=APP_TITLE,
        port=APP_PORT,
        storage_secret=storage_secret,
        reload=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
