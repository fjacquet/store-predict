"""Report page -- display calculation results and download PDF."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nicegui import app, ui

from store_predict.pipeline.calculation import calculate
from store_predict.services.pdf_report import (
    format_storage,
    generate_report_pdf,
    sanitize_filename,
)
from store_predict.ui.layout import layout


@ui.page("/report")
async def report_page() -> None:
    """Display calculation summary, workload breakdown, and PDF download."""
    await ui.context.client.connected()

    vm_data: list[dict[str, Any]] | None = app.storage.tab.get("vm_data")
    project_name: str = str(app.storage.tab.get("project_name", ""))

    if not vm_data:
        with (
            layout("StorePredict - Report"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
        ):
            ui.label("No data available. Please upload a file first.").classes(
                "text-xl text-gray-500"
            )
            ui.link("Go to Upload", "/upload").classes("text-blue-600 underline text-lg")
        return

    # Run calculation
    summary = calculate(vm_data)

    with (
        layout("StorePredict - Report"),
        ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-6"),
    ):
        # Title row
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Sizing Report").classes("text-2xl font-bold")
            if project_name:
                ui.label(f"Project: {project_name}").classes("text-lg text-gray-500")

        # Summary cards
        with ui.grid().classes("grid grid-cols-2 md:grid-cols-4 gap-4 w-full"):
            _summary_card("Total VMs", str(summary.total_vms))
            _summary_card("Total Provisioned", format_storage(summary.total_provisioned_mib))
            _summary_card("Total In Use", format_storage(summary.total_in_use_mib))
            _summary_card("Weighted Avg DRR", f"{summary.weighted_avg_drr:.1f}x")
            _summary_card("Required Capacity", format_storage(summary.total_required_mib))

        # Workload breakdown table
        ui.label("Workload Breakdown").classes("text-xl font-semibold")
        columns = [
            {"name": "category", "label": "Category", "field": "category", "align": "left"},
            {"name": "vms", "label": "VMs", "field": "vms", "align": "right"},
            {
                "name": "provisioned",
                "label": "Provisioned (GiB)",
                "field": "provisioned",
                "align": "right",
            },
            {"name": "avg_drr", "label": "Avg DRR", "field": "avg_drr", "align": "right"},
            {
                "name": "required",
                "label": "Required (GiB)",
                "field": "required",
                "align": "right",
            },
        ]
        rows = [
            {
                "category": grp.category,
                "vms": grp.vm_count,
                "provisioned": f"{grp.total_provisioned_mib / 1024:.1f}",
                "avg_drr": f"{grp.avg_drr:.1f}x",
                "required": f"{grp.total_required_mib / 1024:.1f}",
            }
            for grp in summary.workload_groups
        ]
        ui.table(columns=columns, rows=rows).classes("w-full")

        # Action buttons
        with ui.row().classes("gap-4"):
            ui.button(
                "Download PDF Report",
                on_click=lambda: _on_download(summary, project_name),
                icon="download",
            ).classes("bg-blue-700 text-white")

            ui.button(
                "Back to Review",
                on_click=lambda: ui.navigate.to("/review"),
            ).classes("bg-gray-600 text-white")


def _summary_card(label: str, value: str) -> None:
    """Render a single summary metric card."""
    with ui.card().classes("p-4"):
        ui.label(label).classes("text-sm text-gray-500")
        ui.label(value).classes("text-xl font-bold")


def _on_download(summary: object, project_name: str) -> None:
    """Generate PDF and trigger browser download."""
    from store_predict.pipeline.calculation import CalculationSummary

    assert isinstance(summary, CalculationSummary)
    pdf_bytes = generate_report_pdf(summary, project_name)
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.pdf"
    ui.download(pdf_bytes, filename=filename, media_type="application/pdf")
