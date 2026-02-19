"""StorePredict NiceGUI application entry point."""

from __future__ import annotations

from nicegui import ui

# Import pages to register their routes with NiceGUI
import store_predict.ui.pages.report
import store_predict.ui.pages.review
import store_predict.ui.pages.upload  # noqa: F401
from store_predict.config import APP_PORT, APP_TITLE


@ui.page("/")
def index_page() -> None:
    """Landing page for StorePredict."""
    from store_predict.ui.layout import layout

    with layout(), ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"):
        ui.label(APP_TITLE).classes("text-4xl font-bold text-blue-900")
        ui.label(" PowerStore DRR Sizing Tool").classes("text-xl text-gray-600")
        ui.label(
            "Analyze VMware workload exports (RVTools, LiveOptics) to predict "
            "Data Reduction Ratios on Dell PowerStore arrays."
        ).classes("text-center text-gray-500 max-w-lg")
        ui.button(
            "Upload Workload Data",
            on_click=lambda: ui.navigate.to("/upload"),
        ).classes("bg-blue-700 text-white")


def main() -> None:
    """Start the NiceGUI application."""
    ui.run(
        title=APP_TITLE,
        port=APP_PORT,
        storage_secret="change-me-in-production",
        reload=False,
    )


if __name__ == "__main__":
    main()
