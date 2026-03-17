"""StorePredict NiceGUI application entry point."""

from __future__ import annotations

import os
from pathlib import Path

from nicegui import app, ui
from starlette.formparsers import MultiPartParser

import store_predict.ui.pages.compute
import store_predict.ui.pages.concerns

# Import pages to register their routes with NiceGUI
import store_predict.ui.pages.layout_page
import store_predict.ui.pages.report
import store_predict.ui.pages.review
import store_predict.ui.pages.scope
import store_predict.ui.pages.upload  # noqa: F401
from store_predict.chunk_upload import register_routes
from store_predict.config import APP_PORT, APP_TITLE
from store_predict.i18n import t
from store_predict.logging_config import setup_logging


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


_PUBLIC_DIR = Path(__file__).resolve().parents[2] / "public"


def main() -> None:
    """Start the NiceGUI application."""
    setup_logging()
    # Increase spool size so 2 MB chunks stay in RAM during multipart parsing.
    MultiPartParser.spool_max_size = 4 * 1024 * 1024  # 4 MB
    register_routes()
    if _PUBLIC_DIR.is_dir():
        app.add_static_files("/public", str(_PUBLIC_DIR))
    storage_secret = os.environ.get("STORAGE_SECRET", "dev-only-not-for-production")
    favicon = str(_PUBLIC_DIR / "favicon.svg") if (_PUBLIC_DIR / "favicon.svg").exists() else None
    ui.run(
        title=APP_TITLE,
        port=APP_PORT,
        storage_secret=storage_secret,
        favicon=favicon,
        reload=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
