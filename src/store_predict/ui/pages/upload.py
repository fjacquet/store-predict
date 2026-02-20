"""Upload page with file dropzone and pipeline integration."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from nicegui import app, background_tasks, run, ui

from store_predict.config import DRR_CSV_PATH
from store_predict.i18n import t
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import ingest_file
from store_predict.pipeline.llm_classifier import classify_unknown_vms_async
from store_predict.pipeline.validation import validate_upload
from store_predict.pipeline.zip_extraction import extract_liveoptics_from_zip
from store_predict.services.drr_table import DRRTable
from store_predict.services.llm_config import LLMConfig
from store_predict.ui.layout import layout
from store_predict.ui.state import set_project_name

logger = logging.getLogger(__name__)


@ui.page("/upload")
async def upload_page() -> None:
    """Upload page -- accept RVTools/LiveOptics files and run the sizing pipeline."""
    await ui.context.client.connected()
    with (
        layout("StorePredict - Upload"),
        ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6"),
    ):
        ui.label(t("upload.title")).classes("text-3xl font-bold")

        # Project name input
        project_input = ui.input(
            label=t("upload.project_label"),
            placeholder=t("upload.project_placeholder"),
            on_change=lambda e: set_project_name(e.value or ""),
        ).classes("w-full")
        # Set initial value from session (slot context is active here)
        project_input.value = str(app.storage.tab.get("project_name", ""))

        # File upload dropzone
        with ui.card().classes("w-full"):
            upload_widget = (
                ui.upload(
                    label=t("upload.drop_label"),
                    on_upload=lambda e: background_tasks.create(handle_upload(e)),
                    auto_upload=True,
                    max_file_size=50_000_000,
                )
                .props('accept=".xlsx,.csv,.zip"')
                .classes("w-full")
            )

        # Spinner and progress bar (initially hidden)
        with ui.column().classes("w-full items-center gap-2"):
            spinner = ui.spinner(size="xl")
            spinner.visible = False
            progress = ui.linear_progress(value=0).classes("w-full")
            progress.visible = False

        # Format hints
        ui.label(t("upload.supported_formats")).classes("text-sm text-gray-400")

        async def handle_upload(e: object) -> None:
            """Process uploaded file through ingestion + classification pipeline.

            Steps: temp file -> ingest -> classify -> DRR lookup -> session state -> navigate.
            Wraps blocking I/O with run.io_bound so the event loop stays responsive.

            NiceGUI background tasks never have slot context (the slot stack is always empty).
            All calls that need client context (app.storage.tab, ui.notify, ui.navigate.to)
            must use `with upload_widget:` to enter a slot and make the client reachable.
            `with upload_widget:` doesn't add child elements — it only sets the slot context.
            """
            # Enter upload_widget slot to make context.client available.
            with upload_widget:
                _tab = app.storage.tab
            _project_name = str(_tab.get("project_name", ""))

            tmp_path: Path | None = None
            spinner.visible = True
            progress.visible = True
            progress.value = 0.1
            upload_widget.disable()
            try:
                # Read and validate before writing to disk
                content = await e.file.read()  # type: ignore[attr-defined]

                # Detect ZIP upload and extract LiveOptics xlsx before validation
                original_filename = e.file.name  # type: ignore[attr-defined]
                filename = original_filename
                if filename.lower().endswith(".zip"):
                    content, filename = extract_liveoptics_from_zip(content)
                validate_upload(content, filename)

                with tempfile.NamedTemporaryFile(
                    suffix=Path(filename).suffix,
                    delete=False,
                ) as tmp:
                    tmp.write(content)
                    tmp_path = Path(tmp.name)

                progress.value = 0.3
                # Run blocking I/O in thread pool so the event loop stays responsive
                df = await run.io_bound(ingest_file, tmp_path)

                progress.value = 0.6
                registry = RuleRegistry(build_default_rules())
                df = await run.io_bound(classify_dataframe, df, registry)

                # --- LLM Classification Fallback ---
                llm_cfg = LLMConfig()
                logger.info(
                    "LLM config: enabled=%s model=%s api_base=%s",
                    llm_cfg.enabled,
                    llm_cfg.model,
                    llm_cfg.api_base,
                )
                if llm_cfg.enabled:
                    with upload_widget:
                        llm_notif = ui.notification(t("llm.classifying"), spinner=True, timeout=None, type="info")
                    try:
                        drr_table_for_llm = DRRTable.from_csv(DRR_CSV_PATH)
                        vm_records: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]
                        vm_records = await classify_unknown_vms_async(vm_records, drr_table_for_llm, llm_cfg)
                        df = pd.DataFrame(vm_records)
                        llm_count = sum(1 for r in vm_records if r.get("classification_confidence") == "llm")
                        if llm_count > 0:
                            llm_notif.message = t("llm.classified_notify", count=llm_count)
                            llm_notif.type = "positive"
                        else:
                            llm_notif.dismiss()
                    except Exception:
                        llm_notif.message = t("llm.error")
                        llm_notif.type = "negative"
                    finally:
                        llm_notif.spinner = False
                # --- End LLM Classification Fallback ---

                progress.value = 0.85
                # Add DRR column from reference table
                drr_table = DRRTable.from_csv(DRR_CSV_PATH)
                df["drr"] = df.apply(
                    lambda r: drr_table.get_ratio(r["workload_category"], r["workload_subcategory"]),
                    axis=1,
                )

                # Store results via pre-captured _tab reference (dict persists beyond slot).
                records: list[dict[str, object]] = df.to_dict(orient="records")  # type: ignore[assignment]
                for row in records:
                    for key, val in row.items():
                        if isinstance(val, float) and val != val:  # NaN check
                            row[key] = None
                _tab["vm_data"] = records
                _tab["project_name"] = _project_name
                progress.value = 1.0

                # Notify and navigate — both need client context via slot
                with upload_widget:
                    ui.notify(t("upload.loaded_notify", count=len(df)), type="positive")
                await asyncio.sleep(0.3)
                with upload_widget:
                    ui.navigate.to("/review")

            except IngestionError as exc:
                with upload_widget:
                    ui.notify(str(exc), type="negative")
            except Exception:
                with upload_widget:
                    ui.notify(t("error.unexpected"), type="negative")
            finally:
                spinner.visible = False
                progress.visible = False
                upload_widget.enable()
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
