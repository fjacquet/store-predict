"""Print-optimised report page rendered by Playwright for PDF export.

Route: ``/report/print?token=<uuid>``

No navigation chrome, no header — only the content that should appear in the PDF.
Session data is recovered from the one-time token store so that Playwright
(which has no access to ``app.storage.tab``) can still read user-specific data.
"""

from __future__ import annotations

from typing import Any, cast

from nicegui import ui
from starlette.requests import Request  # noqa: TC002

from store_predict.i18n import t
from store_predict.i18n.locale import set_locale
from store_predict.pipeline.calculation import CalculationSummary, calculate
from store_predict.services import print_session
from store_predict.services.charts import (
    echart_before_after_options,
    echart_drr_bar_options,
    echart_pie_options,
    echart_sankey_options,
)
from store_predict.services.pdf_report import format_storage

_PRINT_CSS = """
@media print {
  * { -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }
  .no-print { display: none !important; }
}
body { font-family: sans-serif; margin: 0; padding: 0; }
"""


@ui.page("/report/print")
async def report_print_page(request: Request) -> None:
    """Render a print-optimised version of the report for Playwright PDF export."""
    # Read token and consume session data before waiting for the client —
    # print_session uses an in-process dict, no NiceGUI storage access needed yet.
    token = request.query_params.get("token", "")
    data: dict[str, Any] | None = print_session.consume(token)

    ui.add_head_html(f"<style>{_PRINT_CSS}</style>")

    # app.storage.tab requires an established WebSocket connection.
    await ui.context.client.connected()

    if not data:
        ui.label("Invalid or expired print token.").classes("text-red-600 p-8")
        return

    # Restore locale so t() produces the correct language for this Playwright session.
    locale_str = str(data.get("locale", "fr"))
    set_locale(locale_str)

    vm_data = cast("list[dict[str, Any]]", data.get("vm_data", []))
    project_name = str(data.get("project_name", ""))

    if not vm_data:
        ui.label("No data to print.").classes("text-gray-500 p-8")
        return

    summary: CalculationSummary = calculate(vm_data)

    with ui.column().classes("w-full p-6 gap-6"):
        # Header row
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ui.label(t("report.title")).classes("text-2xl font-bold")
            if project_name:
                ui.label(t("report.project_label", name=project_name)).classes("text-lg text-gray-500")

        # ── Totals ──────────────────────────────────────────────────────────
        ui.label(t("report.totals_heading")).classes("text-xl font-semibold")
        with ui.grid().classes("grid grid-cols-3 gap-4 w-full"):
            _card(t("stats.total_vms"), str(summary.total_vms))
            _card(t("stats.total_cpus"), f"{summary.total_cpus:,}")
            _card(t("stats.total_memory"), format_storage(summary.total_memory_mib))
            _card(t("stats.total_provisioned"), format_storage(summary.total_provisioned_mib))
            _card(t("stats.total_in_use"), format_storage(summary.total_in_use_mib))
            _card(t("stats.required_capacity"), format_storage(summary.total_required_mib))

        # ── Averages ─────────────────────────────────────────────────────────
        ui.label(t("report.averages_heading")).classes("text-xl font-semibold")
        with ui.grid().classes("grid grid-cols-3 gap-4 w-full"):
            _card(t("stats.avg_cpus"), f"{summary.avg_vm_cpus:.1f}")
            _card(t("stats.avg_memory"), format_storage(summary.avg_vm_memory_mib))
            _card(t("stats.avg_storage"), format_storage(summary.avg_vm_size_mib))
            _card(t("stats.avg_drr"), f"{summary.weighted_avg_drr:.1f}x")
            _card(
                t("stats.largest_vm"),
                f"{summary.largest_vm_name} ({format_storage(summary.largest_vm_provisioned_mib)})",
            )

        # ── Performance (LiveOptics only) ────────────────────────────────────
        if summary.has_performance_data:
            ui.label(t("report.performance_heading")).classes("text-xl font-semibold")
            with ui.grid().classes("grid grid-cols-3 gap-4 w-full"):
                _card(t("stats.total_avg_iops"), f"{summary.total_avg_iops:,.0f}")
                _card(
                    t("stats.hottest_vm"),
                    f"{summary.max_vm_peak_iops:,.0f} ({summary.max_vm_peak_iops_name})",
                )
                _card(t("stats.peak_throughput"), f"{summary.peak_throughput_mbs:,.1f} MB/s")
                _card(t("stats.iops_8k"), f"{summary.total_iops_8k_equivalent:,.0f}")

        # ── Workload breakdown table ──────────────────────────────────────────
        ui.label(t("report.breakdown_heading")).classes("text-xl font-semibold")
        columns = [
            {"name": "category", "label": t("columns.workload_category"), "field": "category", "align": "left"},
            {"name": "vms", "label": t("columns.vm_name"), "field": "vms", "align": "right"},
            {"name": "provisioned", "label": t("columns.provisioned_mib"), "field": "provisioned", "align": "right"},
            {"name": "avg_drr", "label": t("columns.drr"), "field": "avg_drr", "align": "right"},
            {"name": "required", "label": t("pdf.table_required"), "field": "required", "align": "right"},
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

        # ── Charts ────────────────────────────────────────────────────────────
        if summary.workload_groups:
            ui.label(t("report.charts_heading")).classes("text-xl font-bold mt-4")

            with ui.row().classes("w-full"):
                ui.echart(echart_sankey_options(summary)).classes("w-full h-72")

            with ui.grid(columns=2).classes("w-full gap-4"):
                ui.echart(echart_pie_options(summary)).classes("h-64")
                ui.echart(echart_drr_bar_options(summary)).classes("h-64")

            with ui.row().classes("w-full"):
                ui.echart(echart_before_after_options(summary)).classes("w-full h-64")


def _card(label: str, value: str) -> None:
    """Render a single summary metric card."""
    with ui.card().classes("p-4"):
        ui.label(label).classes("text-sm text-gray-500")
        ui.label(value).classes("text-xl font-bold")
