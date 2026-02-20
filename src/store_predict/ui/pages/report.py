"""Report page -- display calculation results and download PDF."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nicegui import app, ui

from store_predict.i18n import t
from store_predict.i18n.locale import get_locale
from store_predict.pipeline.calculation import calculate
from store_predict.services.excel_report import generate_report_xlsx
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
            ui.label(t("report.no_data")).classes("text-xl text-gray-500")
            ui.link(t("report.go_to_upload"), "/upload").classes("text-blue-600 underline text-lg")
        return

    # Run calculation
    summary = calculate(vm_data)

    with (
        layout("StorePredict - Report"),
        ui.column().classes("w-full p-4 gap-6"),
    ):
        # Title row
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(t("report.title")).classes("text-2xl font-bold")
            if project_name:
                ui.label(t("report.project_label", name=project_name)).classes("text-lg text-gray-500")

        # Totals cards
        ui.label(t("report.totals_heading")).classes("text-xl font-semibold")
        with ui.grid().classes("grid grid-cols-2 md:grid-cols-4 gap-4 w-full"):
            _summary_card(t("stats.total_vms"), str(summary.total_vms))
            _summary_card(t("stats.total_cpus"), f"{summary.total_cpus:,}")
            _summary_card(t("stats.total_memory"), format_storage(summary.total_memory_mib))
            _summary_card(t("stats.total_provisioned"), format_storage(summary.total_provisioned_mib))
            _summary_card(t("stats.total_in_use"), format_storage(summary.total_in_use_mib))
            _summary_card(t("stats.required_capacity"), format_storage(summary.total_required_mib))

        # Averages cards
        ui.label(t("report.averages_heading")).classes("text-xl font-semibold")
        with ui.grid().classes("grid grid-cols-2 md:grid-cols-4 gap-4 w-full"):
            _summary_card(t("stats.avg_cpus"), f"{summary.avg_vm_cpus:.1f}")
            _summary_card(t("stats.avg_memory"), format_storage(summary.avg_vm_memory_mib))
            _summary_card(t("stats.avg_storage"), format_storage(summary.avg_vm_size_mib))
            _summary_card(t("stats.avg_drr"), f"{summary.weighted_avg_drr:.1f}x")
            _summary_card(
                t("stats.largest_vm"),
                f"{summary.largest_vm_name} ({format_storage(summary.largest_vm_provisioned_mib)})",
            )

        # Performance summary cards (only when LiveOptics data available)
        if summary.has_performance_data:
            ui.label(t("report.performance_heading")).classes("text-xl font-semibold")
            with ui.grid().classes("grid grid-cols-2 md:grid-cols-4 gap-4 w-full"):
                _summary_card(t("stats.total_avg_iops"), f"{summary.total_avg_iops:,.0f}")
                _summary_card(
                    t("stats.hottest_vm"),
                    f"{summary.max_vm_peak_iops:,.0f} ({summary.max_vm_peak_iops_name})",
                )
                _summary_card(t("stats.peak_throughput"), f"{summary.peak_throughput_mbs:,.1f} MB/s")
                _summary_card(t("stats.iops_8k"), f"{summary.total_iops_8k_equivalent:,.0f}")

        # Workload breakdown table
        ui.label(t("report.breakdown_heading")).classes("text-xl font-semibold")
        columns = [
            {"name": "category", "label": t("columns.workload_category"), "field": "category", "align": "left"},
            {"name": "vms", "label": t("columns.vm_name"), "field": "vms", "align": "right"},
            {
                "name": "provisioned",
                "label": t("columns.provisioned_mib"),
                "field": "provisioned",
                "align": "right",
            },
            {"name": "avg_drr", "label": t("columns.drr"), "field": "avg_drr", "align": "right"},
            {
                "name": "required",
                "label": t("pdf.table_required"),
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
                t("report.download_pdf"),
                on_click=lambda: _on_download(summary, project_name),
                icon="download",
            ).classes("bg-blue-700 text-white")

            ui.button(
                t("report.download_excel"),
                on_click=lambda: _on_download_excel(summary, project_name),
                icon="table_view",
            ).classes("bg-green-700 text-white")

            ui.button(
                t("report.back_to_review"),
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
    pdf_bytes = generate_report_pdf(summary, project_name, locale=get_locale())
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.pdf"
    ui.download(pdf_bytes, filename=filename, media_type="application/pdf")


def _on_download_excel(summary: object, project_name: str) -> None:
    """Generate Excel workbook and trigger browser download."""
    from store_predict.pipeline.calculation import CalculationSummary

    assert isinstance(summary, CalculationSummary)
    xlsx_bytes = generate_report_xlsx(summary, project_name, locale=get_locale())
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.xlsx"
    ui.download(
        xlsx_bytes,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
