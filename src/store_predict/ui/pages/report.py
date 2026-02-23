"""Report page -- display calculation results and download PDF."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

from nicegui import app, ui

from store_predict.config import APP_PORT
from store_predict.i18n import t
from store_predict.i18n.locale import get_locale
from store_predict.pipeline.calculation import CalculationSummary, calculate
from store_predict.pipeline.health_checks import HealthCheckResult, run_health_checks
from store_predict.services import playwright_pdf, print_session
from store_predict.services.charts import (
    echart_before_after_options,
    echart_drr_bar_options,
    echart_pie_options,
    echart_sankey_options,
)
from store_predict.services.excel_report import generate_report_xlsx
from store_predict.services.pdf_report import (
    format_storage,
    sanitize_filename,
    validate_logo,
)
from store_predict.ui.layout import layout
from store_predict.ui.state import load_session_data


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
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("upload_file", size="3rem").classes("text-gray-400")
            ui.label(t("report.no_data")).classes("text-xl text-gray-500")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return

    # Run calculation
    summary = calculate(vm_data)

    # Run health checks for export enrichment
    df = load_session_data()
    health_result: HealthCheckResult | None = run_health_checks(df) if df is not None else None

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
            pdf_btn = (
                ui.button(
                    t("report.download_pdf"),
                    icon="download",
                )
                .classes("bg-blue-700 text-white")
                .tooltip(t("tooltip.download_pdf"))
            )

            excel_btn = (
                ui.button(
                    t("report.download_excel"),
                    icon="table_view",
                )
                .classes("bg-green-700 text-white")
                .tooltip(t("tooltip.download_excel"))
            )

            ui.button(
                t("report.back_to_review"),
                on_click=lambda: ui.navigate.to("/review"),
            ).classes("bg-gray-600 text-white")

        async def on_download_pdf() -> None:
            pdf_btn.disable()
            try:
                await _on_download_playwright(summary, project_name, pdf_btn)
            finally:
                pdf_btn.enable()

        async def on_download_excel() -> None:
            excel_btn.disable()
            try:
                _on_download_excel(summary, project_name, health_result)
            finally:
                excel_btn.enable()

        pdf_btn.on("click", on_download_pdf)
        excel_btn.on("click", on_download_excel)

        # Charts section
        _build_charts_section(summary)

        # Logo upload section (secondary action, below buttons)
        _build_logo_upload_section()


def _build_charts_section(summary: CalculationSummary) -> None:
    """Render interactive ECharts visualizations below the workload breakdown table."""
    if not summary.workload_groups:
        return

    ui.label(t("report.charts_heading")).classes("text-xl font-bold mb-4")

    # Sankey — full width
    with ui.row().classes("w-full"):
        ui.echart(echart_sankey_options(summary)).classes("w-full h-72")

    # Pie + DRR bar — two-column grid
    with ui.grid(columns=2).classes("w-full gap-4"):
        ui.echart(echart_pie_options(summary)).classes("h-64")
        ui.echart(echart_drr_bar_options(summary)).classes("h-64")

    # Before/after bar — full width
    with ui.row().classes("w-full"):
        ui.echart(echart_before_after_options(summary)).classes("w-full h-64")


def _summary_card(label: str, value: str) -> None:
    """Render a single summary metric card."""
    with ui.card().classes("p-4"):
        ui.label(label).classes("text-sm text-gray-500")
        ui.label(value).classes("text-xl font-bold")


async def _on_download_playwright(summary: object, project_name: str, btn: ui.button) -> None:
    """Generate PDF via Playwright and trigger browser download."""
    from store_predict.pipeline.calculation import CalculationSummary

    assert isinstance(summary, CalculationSummary)

    company_logo_b64: str = app.storage.tab.get("company_logo_b64", "")
    locale = get_locale()

    data: dict[str, Any] = {
        "vm_data": [
            {
                "vm_name": vm.vm_name,
                "workload_category": vm.workload_category,
                "provisioned_mib": vm.provisioned_mib,
                "in_use_mib": vm.in_use_mib,
                "drr": vm.drr,
                "peak_iops": vm.peak_iops,
                "avg_iops": vm.avg_iops,
                "peak_throughput_mbs": vm.peak_throughput_mbs,
                "iops_8k_equivalent": vm.iops_8k_equivalent,
            }
            for vm in summary.vm_calculations
        ],
        "project_name": project_name,
        "locale": locale,
        "company_logo_b64": company_logo_b64,
    }
    token = print_session.create(data)
    try:
        pdf_bytes = await playwright_pdf.generate_pdf(token, APP_PORT)
    except Exception:
        ui.notify(t("error.unexpected"), type="negative")
        return

    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.pdf"
    ui.download(pdf_bytes, filename=filename, media_type="application/pdf")


def _build_logo_upload_section() -> None:
    """Render the company logo upload widget on the report page."""
    with ui.card().classes("w-full max-w-md p-4 gap-2"):
        ui.label(t("report.upload_logo")).classes("text-sm font-semibold")
        ui.upload(
            label=t("report.logo_upload_label"),
            on_upload=_handle_logo_upload,
            auto_upload=True,
            max_file_size=200_000,
        ).props('accept=".png,.jpg,.jpeg"').classes("w-full").tooltip(t("tooltip.upload_logo"))
        ui.button(
            t("report.logo_remove"),
            on_click=_remove_logo,
            icon="delete",
        ).classes("bg-gray-400 text-white text-sm")


async def _handle_logo_upload(e: object) -> None:
    """Validate and store uploaded company logo in tab storage."""
    content: bytes = e.content.read()  # type: ignore[attr-defined]
    filename: str = e.name  # type: ignore[attr-defined]
    try:
        validate_logo(content, filename)
        app.storage.tab["company_logo_b64"] = base64.b64encode(content).decode("ascii")
        ui.notify(t("report.logo_uploaded"), type="positive")
    except Exception:
        ui.notify(t("error.logo_upload_failed"), type="negative")


def _remove_logo() -> None:
    """Remove company logo from tab storage."""
    app.storage.tab.pop("company_logo_b64", None)
    ui.notify(t("report.logo_removed"), type="info")


def _on_download_excel(
    summary: object,
    project_name: str,
    health_result: HealthCheckResult | None = None,
) -> None:
    """Generate Excel workbook and trigger browser download."""
    from store_predict.pipeline.calculation import CalculationSummary

    assert isinstance(summary, CalculationSummary)
    xlsx_bytes = generate_report_xlsx(summary, project_name, locale=get_locale(), health_result=health_result)
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.xlsx"
    ui.download(
        xlsx_bytes,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
