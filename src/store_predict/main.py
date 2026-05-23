"""StorePredict NiceGUI application entry point."""

from __future__ import annotations

import logging
import os
import secrets
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

logger = logging.getLogger(__name__)


def _resolve_storage_secret() -> tuple[str, bool]:
    """Return ``(storage_secret, is_dev_mode)``.

    Production requires ``STORAGE_SECRET`` in the environment. Dev mode is
    opt-in via ``STORE_PREDICT_DEV=1``; when enabled without a configured
    secret we mint an ephemeral one so sessions stay unguessable even in dev.
    """
    secret = os.environ.get("STORAGE_SECRET")
    is_dev = os.environ.get("STORE_PREDICT_DEV") == "1"
    if secret:
        return secret, is_dev
    if not is_dev:
        raise RuntimeError(
            "STORAGE_SECRET must be set. Set STORE_PREDICT_DEV=1 for a local dev run with an ephemeral secret."
        )
    ephemeral = secrets.token_urlsafe(32)
    logger.warning("STORE_PREDICT_DEV=1 and STORAGE_SECRET unset; using ephemeral secret")
    return ephemeral, is_dev


@ui.page("/")
def index_page() -> None:
    """Landing page for StorePredict."""
    from store_predict.ui.layout import layout

    with layout(), ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"):
        ui.label(APP_TITLE).classes("text-5xl sp-display").style("color:var(--sp-ink)")
        ui.label(t("home.subtitle")).classes("text-xl").style("color:var(--sp-muted)")
        ui.label(t("home.description")).classes("text-center max-w-lg").style("color:var(--sp-muted)")
        ui.button(
            t("home.cta"),
            on_click=lambda: ui.navigate.to("/upload"),
        ).props("size=lg unelevated")


_PUBLIC_DIR = Path(__file__).resolve().parents[2] / "public"


def main() -> None:
    """Start the NiceGUI application."""
    setup_logging()
    # Increase spool size so 2 MB chunks stay in RAM during multipart parsing.
    MultiPartParser.spool_max_size = 4 * 1024 * 1024  # 4 MB
    register_routes()
    if _PUBLIC_DIR.is_dir():
        app.add_static_files("/public", str(_PUBLIC_DIR))
    storage_secret, is_dev = _resolve_storage_secret()
    favicon = str(_PUBLIC_DIR / "favicon.svg") if (_PUBLIC_DIR / "favicon.svg").exists() else None
    ui.run(
        title=APP_TITLE,
        port=APP_PORT,
        storage_secret=storage_secret,
        favicon=favicon,
        reload=is_dev,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
