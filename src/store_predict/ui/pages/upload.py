"""Upload page placeholder."""

from __future__ import annotations

from nicegui import ui

from store_predict.ui.layout import layout


@ui.page("/upload")
def upload_page() -> None:
    """Upload page - file upload will be implemented in Phase 2."""
    with (
        layout("StorePredict - Upload"),
        ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-4"),
    ):
        ui.label("Upload Workload Data").classes("text-xl font-semibold")
        ui.label("Upload page - coming in Phase 2").classes("text-gray-500 italic")
        ui.label(
            "Accepts RVTools (.xlsx), LiveOptics (.xlsx, .csv)"
        ).classes("text-sm text-gray-400")
