"""Upload page with file dropzone and pipeline integration."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import app, background_tasks, run, ui

if TYPE_CHECKING:
    import pandas as pd

from store_predict.config import DRR_CSV_PATH
from store_predict.i18n import t
from store_predict.logging_config import hash_name
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import ingest_file, ingest_two_files
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.pipeline.session_archive import is_session_zip, restore_session_zip
from store_predict.pipeline.validation import validate_upload
from store_predict.pipeline.zip_extraction import extract_liveoptics_from_zip
from store_predict.services.drr_table import DRRTable
from store_predict.services.semantic_config import get_semantic_config
from store_predict.ui.layout import layout
from store_predict.ui.state import (
    add_pending_file,
    clear_pending_files,
    clear_session_data,
    get_pending_files,
    set_project_name,
)

logger = logging.getLogger(__name__)


@ui.page("/upload")
async def upload_page() -> None:
    """Upload page -- accept RVTools/LiveOptics files and run the sizing pipeline."""
    await ui.context.client.connected()
    # Unique token per page-load routes chunked uploads to this session's queue.
    upload_token = str(uuid.uuid4())
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

        # File chips container — shows uploaded file names + format badges
        chips_row = ui.row().classes("w-full flex-wrap gap-2")

        def _refresh_chips() -> None:
            chips_row.clear()
            with chips_row:
                for entry in get_pending_files():
                    ui.chip(
                        t("upload.file_ready", name=entry["name"], fmt=entry["fmt"]),
                        icon="check_circle",
                        color="positive",
                    ).props("outline")

        _refresh_chips()

        # File upload dropzone — chunked to survive corporate proxy timeouts.
        # Files are POSTed in 2 MB pieces to /api/upload/{token}; on_upload is
        # intentionally absent because the custom url bypasses NiceGUI's internal
        # upload handler. A ui.timer polls app.storage.general for completion.
        with ui.card().classes("w-full"):
            upload_widget = (
                ui.upload(
                    label=t("upload.drop_label"),
                    auto_upload=True,
                    multiple=True,
                    max_files=2,
                    max_file_size=50_000_000,
                )
                .props(f'accept=".xlsx,.csv,.zip" url=/api/upload/{upload_token} chunk-size=2097152')
                .classes("w-full")
            )

        # "Analyser" button — always enabled; run_analysis guards against empty pending list
        analyse_btn = (  # noqa: F841
            ui.button(t("upload.analyse_button"), on_click=lambda: background_tasks.create(run_analysis()))
            .classes("w-full")
            .props("color=primary")
        )

        # Spinner and progress bar (initially hidden)
        with ui.column().classes("w-full items-center gap-2"):
            spinner = ui.spinner(size="xl")
            spinner.visible = False
            progress = ui.linear_progress(value=0).classes("w-full")
            progress.visible = False

        # Format hints
        ui.label(t("upload.supported_formats")).classes("text-sm").style("color:var(--sp-muted)")

        async def _handle_session_restore(zip_bytes: bytes) -> None:
            """Restore a StorePredict session archive into app.storage.tab and navigate to /review."""
            try:
                restored = await run.io_bound(restore_session_zip, zip_bytes)
            except IngestionError as exc:
                with upload_widget:
                    ui.notify(t("session.restore_error", reason=str(exc)), type="negative")
                return

            with upload_widget:
                # Store original file bytes for future re-save
                app.storage.tab["_session_original_bytes"] = restored.pop("_restored_original_bytes", b"")
                app.storage.tab["_session_original_filename"] = restored.pop(
                    "_restored_original_filename", "upload.xlsx"
                )
                # Restore all session keys
                app.storage.tab.update(restored)
                vm_count = len(restored.get("vm_data") or [])  # type: ignore[arg-type]
                ui.notify(t("session.restore_success", count=vm_count), type="positive")
                ui.navigate.to("/review")

        async def _handle_assembled_file(tmp_path: Path, original_filename: str) -> None:
            """Stage an assembled file: validate, detect format, update chips.

            Called from the upload-polling timer after all chunks are received.
            The file is already on disk at tmp_path (written by the chunk endpoint).
            Does NOT run the pipeline — that happens on "Analyser" click.
            NiceGUI background tasks never have slot context (the slot stack is always empty).
            All calls that need client context (app.storage.tab, ui.notify, ui.navigate.to)
            must use `with upload_widget:` to enter a slot and make the client reachable.
            `with upload_widget:` doesn't add child elements — it only sets the slot context.
            """
            try:
                content = tmp_path.read_bytes()
                filename = original_filename

                # Session restore path: detect StorePredict session .zip before LiveOptics extraction
                if filename.lower().endswith(".zip") and is_session_zip(content):
                    tmp_path.unlink(missing_ok=True)
                    await _handle_session_restore(content)
                    return

                # Zip: extract inner xlsx, replace tmp_path
                if filename.lower().endswith(".zip"):
                    logger.info("ZIP upload detected: file=%s — extracting inner xlsx", hash_name(original_filename))
                    content, filename = extract_liveoptics_from_zip(content)
                    tmp_path.unlink(missing_ok=True)
                    with tempfile.NamedTemporaryFile(
                        suffix=Path(filename).suffix,
                        delete=False,
                    ) as tmp:
                        tmp.write(content)
                        tmp_path = Path(tmp.name)

                validate_upload(content, filename)

                # Detect format so we can show a badge
                from store_predict.pipeline.ingestion import detect_format

                fmt = detect_format(tmp_path)

                with upload_widget:
                    add_pending_file(str(tmp_path), fmt.value, filename)
                    # Store for session save: capture latest file for single-file sessions
                    app.storage.tab["_session_original_bytes"] = content
                    app.storage.tab["_session_original_filename"] = original_filename
                    _refresh_chips()

            except IngestionError as exc:
                logger.warning("Upload validation failed for file=%s: %s", hash_name(original_filename), exc)
                with upload_widget:
                    ui.notify(str(exc), type="negative", timeout=0)
            except Exception:
                logger.exception("Unexpected error handling assembled upload: file=%s", hash_name(original_filename))
                with upload_widget:
                    ui.notify(t("error.unexpected"), type="negative", timeout=0)

        async def _poll_completed_uploads() -> None:
            """Drain assembled-upload queue and process each file."""
            queue_key = f"upload_queue_{upload_token}"
            queue: list[dict[str, str]] = app.storage.general.get(queue_key, [])
            if not queue:
                return
            result = queue.pop(0)
            app.storage.general[queue_key] = queue
            path = Path(result["path"])
            filename = result["filename"]
            background_tasks.create(_handle_assembled_file(path, filename))

        ui.timer(0.5, _poll_completed_uploads)

        async def _run_pipeline(
            df: pd.DataFrame,
            _tab: dict[str, object],
            _project_name: str,
        ) -> None:
            """Classify, enrich with DRR, store results, and navigate.

            Shared by single-file and two-file paths.
            _tab and _project_name must be captured inside a slot context
            by the caller before this coroutine is awaited.
            """

            progress.value = 0.6
            registry = RuleRegistry(build_override_rules())
            sem_cfg = get_semantic_config()
            semantic = None
            if sem_cfg.enabled:
                with upload_widget:
                    sem_notif = ui.notification(t("semantic.classifying"), spinner=True, timeout=None, type="info")
                try:
                    semantic = await run.io_bound(SemanticClassifier, sem_cfg)
                except Exception:
                    logger.warning("Semantic classifier init failed; using overrides + default only")
                    semantic = None
                    with upload_widget:
                        sem_notif.message = t("semantic.error")
                        sem_notif.type = "warning"
                        sem_notif.spinner = False

            df = await run.io_bound(classify_dataframe, df, registry, semantic)

            if semantic is not None:
                sem_count = int((df["classification_confidence"] == "semantic").sum())
                with upload_widget:
                    if sem_count > 0:
                        sem_notif.message = t("semantic.classified_notify", count=sem_count)
                        sem_notif.type = "positive"
                    else:
                        sem_notif.dismiss()
                    sem_notif.spinner = False

            progress.value = 0.85
            drr_table = DRRTable.from_csv(DRR_CSV_PATH)
            df["drr"] = df.apply(
                lambda r: drr_table.get_ratio(r["workload_category"], r["workload_subcategory"]),
                axis=1,
            )

            records: list[dict[str, object]] = df.to_dict(orient="records")  # type: ignore[assignment]
            for row in records:
                for key, val in row.items():
                    if isinstance(val, float) and val != val:  # NaN check
                        row[key] = None
            _tab["vm_data"] = records
            _tab["project_name"] = _project_name
            progress.value = 1.0

            with upload_widget:
                ui.notify(t("upload.loaded_notify", count=len(df)), type="positive")
            await asyncio.sleep(0.3)
            with upload_widget:
                ui.navigate.to("/scope")

        async def run_analysis() -> None:
            """Run the sizing pipeline on all staged files.

            1 file  → ingest_file() (existing single-file path)
            2 files → ingest_two_files() (merge path)
            """
            # Capture all tab-bound values inside slot context before the async work
            with upload_widget:
                _tab = app.storage.tab
                pending = get_pending_files()  # capture before clear_session_data wipes it
                _project_name = str(_tab.get("project_name", ""))
                clear_session_data()

            if not pending:
                with upload_widget:
                    ui.notify(t("upload.supported_formats"), type="warning")
                return

            spinner.visible = True
            progress.visible = True
            progress.value = 0.1
            upload_widget.disable()

            try:
                if len(pending) == 1:
                    tmp_path = Path(str(pending[0]["path"]))
                    df = await run.io_bound(ingest_file, tmp_path)
                else:
                    path1 = Path(str(pending[0]["path"]))
                    path2 = Path(str(pending[1]["path"]))
                    df = await run.io_bound(ingest_two_files, path1, path2)

                    # Show merge summary notification
                    stats = df.attrs.get("merge_stats", {})
                    if stats:
                        with upload_widget:
                            ui.notify(
                                t(
                                    "upload.merge_summary",
                                    total=stats.get("total", 0),
                                    matched=stats.get("matched", 0),
                                    rv_only=stats.get("rv_only", 0),
                                    lo_only=stats.get("lo_only", 0),
                                ),
                                type="info",
                                timeout=8000,
                            )

                # Surface the RVTools guest-level capacity adjustment (vSAN: FTT-free,
                # mount-aware). Only shown when vSAN VMs are present, since that is when
                # the datastore figure would otherwise be FTT-inflated.
                cap_info = df.attrs.get("rvtools_capacity_info")
                if cap_info is not None and cap_info.vsan_vm_count > 0:
                    with upload_widget:
                        ui.notify(
                            t(
                                "upload.vsan_capacity_basis",
                                vsan=cap_info.vsan_vm_count,
                                provisioned=round(cap_info.post_provisioned_mib / 1024 / 1024, 1),
                                raw=round(cap_info.pre_provisioned_mib / 1024 / 1024, 1),
                                fallback=cap_info.fallback_count,
                            ),
                            type="info",
                            timeout=10000,
                        )

                progress.value = 0.3
                await _run_pipeline(df, _tab, _project_name)

            except IngestionError as exc:
                with upload_widget:
                    ui.notify(str(exc), type="negative")
            except Exception:
                logger.exception("Unexpected error in run_analysis")
                with upload_widget:
                    ui.notify(t("error.unexpected"), type="negative")
            finally:
                spinner.visible = False
                progress.visible = False
                upload_widget.enable()
                # Clean up temp files
                for entry in pending:
                    Path(str(entry["path"])).unlink(missing_ok=True)
                with upload_widget:
                    clear_pending_files()
                    _refresh_chips()
