"""Upload page with file dropzone and pipeline integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nicegui import ui

from store_predict.config import DRR_CSV_PATH
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import ingest_file
from store_predict.pipeline.validation import validate_upload
from store_predict.services.drr_table import DRRTable
from store_predict.ui.layout import layout
from store_predict.ui.state import get_project_name, save_session_data, set_project_name


async def _handle_upload(e: object) -> None:
    """Process uploaded file through ingestion + classification pipeline.

    Steps: temp file -> ingest -> classify -> DRR lookup -> session state -> navigate.
    """
    tmp_path: Path | None = None
    try:
        # Write uploaded content to a temp file
        # Read and validate before writing to disk
        content = await e.file.read()  # type: ignore[attr-defined]
        validate_upload(content, e.file.name)  # type: ignore[attr-defined]

        with tempfile.NamedTemporaryFile(
            suffix=Path(e.file.name).suffix,  # type: ignore[attr-defined]
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Run ingestion pipeline (detect format, parse, filter templates)
        df = ingest_file(tmp_path)

        # Run classification pipeline
        registry = RuleRegistry(build_default_rules())
        df = classify_dataframe(df, registry)

        # Add DRR column from reference table
        drr_table = DRRTable.from_csv(DRR_CSV_PATH)
        df["drr"] = df.apply(
            lambda r: drr_table.get_ratio(r["workload_category"], r["workload_subcategory"]),
            axis=1,
        )

        # Store results in session state
        save_session_data(df, get_project_name())

        # Notify and navigate
        ui.notify(f"Loaded {len(df)} VMs", type="positive")
        ui.navigate.to("/review")

    except IngestionError as exc:
        ui.notify(str(exc), type="negative")
    except Exception as exc:
        ui.notify(f"Unexpected error: {exc}", type="negative")
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@ui.page("/upload")
async def upload_page() -> None:
    """Upload page -- accept RVTools/LiveOptics files and run the sizing pipeline."""
    await ui.context.client.connected()
    with (
        layout("StorePredict - Upload"),
        ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6"),
    ):
        ui.label("Upload Workload Data").classes("text-3xl font-bold")

        # Project name input
        project_input = ui.input(
            label="Project Name",
            placeholder="e.g., Customer-DC-Migration-2026",
            on_change=lambda e: set_project_name(e.value or ""),
        ).classes("w-full")
        # Set initial value from session
        project_input.value = get_project_name()

        # File upload dropzone
        with ui.card().classes("w-full"):
            ui.upload(
                label="Drop RVTools or LiveOptics file here (.xlsx, .csv)",
                on_upload=_handle_upload,
                auto_upload=True,
                max_file_size=50_000_000,
            ).props('accept=".xlsx,.csv"').classes("w-full")

        # Format hints
        ui.label("Supported formats: RVTools (.xlsx), LiveOptics (.xlsx, .csv)").classes("text-sm text-gray-400")
