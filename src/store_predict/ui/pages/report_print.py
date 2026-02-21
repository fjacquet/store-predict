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
from store_predict.pipeline.layout_engine import generate_all_proposals
from store_predict.services import print_session
from store_predict.services.charts import (
    echart_before_after_options,
    echart_drr_bar_options,
    echart_pie_options,
    echart_sankey_options,
)
from store_predict.services.pdf_report import _layout_metric_rows, format_storage

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

        # ── Layout Recommendations ────────────────────────────────────────────
        if summary.total_vms > 0:
            _build_layout_section(summary)


def _build_layout_section(summary: CalculationSummary) -> None:
    """Render layout strategy comparison table for the print PDF."""
    proposals = generate_all_proposals(summary)
    metric_rows = _layout_metric_rows(proposals)

    ui.label(t("pdf.layout_heading")).classes("text-xl font-bold mt-6 mb-2")

    columns = [
        {"name": "metric", "label": t("layout_page.metric"), "field": "metric", "align": "left"},
        {"name": "consolidation", "label": t("strategy.consolidation"), "field": "consolidation", "align": "right"},
        {"name": "performance", "label": t("strategy.performance"), "field": "performance", "align": "right"},
        {"name": "uniform", "label": t("strategy.uniform"), "field": "uniform", "align": "right"},
    ]
    rows = [
        {
            "metric": t(f"metrics.{key}"),
            "consolidation": consol_val,
            "performance": perf_val,
            "uniform": uni_val,
        }
        for key, consol_val, perf_val, uni_val in metric_rows
    ]
    ui.table(columns=columns, rows=rows).classes("w-full")


def _card(label: str, value: str) -> None:
    """Render a single summary metric card."""
    with ui.card().classes("p-4"):
        ui.label(label).classes("text-sm text-gray-500")
        ui.label(value).classes("text-xl font-bold")


# ---------------------------------------------------------------------------
# Layout print page
# ---------------------------------------------------------------------------

def _fmt_tib(mib: float) -> str:
    """Format MiB as TiB with 2 decimal places."""
    return f"{mib / (1024 * 1024):.2f} TiB"


def _build_print_datastore_table(datastores: tuple[Any, ...]) -> None:
    """Render a datastore table with VM details always expanded (for print)."""
    columns = [
        {"name": "expand", "label": "", "field": "expand", "align": "left"},
        {"name": "name", "label": t("ds.name"), "field": "name", "align": "left"},
        {"name": "raw_cap", "label": t("ds.raw_cap"), "field": "raw_cap", "align": "right"},
        {"name": "used", "label": t("ds.used"), "field": "used", "align": "right"},
        {"name": "util_pct", "label": t("ds.util"), "field": "util_pct", "align": "right"},
        {"name": "vm_count", "label": t("ds.vms"), "field": "vm_count", "align": "right"},
        {"name": "iops", "label": t("ds.iops"), "field": "iops", "align": "right"},
        {"name": "workloads", "label": t("ds.workloads"), "field": "workloads", "align": "left"},
    ]

    rows = [
        {
            "name": ds.name,
            "raw_cap": _fmt_tib(ds.raw_capacity_mib),
            "used": _fmt_tib(ds.used_capacity_mib),
            "util_pct": f"{ds.utilization_pct:.1f}%",
            "vm_count": ds.vm_count,
            "iops": f"{ds.total_iops:,.0f}",
            "workloads": ", ".join(sorted(ds.workload_types)),
            "vm_names": [vm.vm_name for vm in ds.assigned_vms],
        }
        for ds in datastores
    ]

    vms_label = t("ds.vm_list")
    table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")

    table.add_slot(
        "header",
        r'''
        <q-tr :props="props">
          <q-th auto-width />
          <q-th v-for="col in props.cols" :key="col.name" :props="props">
            {{ col.label }}
          </q-th>
        </q-tr>
        ''',
    )

    # Body slot: rows are always expanded for print (no toggle button)
    table.add_slot(
        "body",
        f'''
        <q-tr :props="props">
          <q-td auto-width />
          <q-td v-for="col in props.cols" :key="col.name" :props="props">
            {{{{ col.value }}}}
          </q-td>
        </q-tr>
        <q-tr :props="props">
          <q-td colspan="100%" class="bg-gray-50">
            <div class="p-2">
              <div class="text-sm font-semibold text-gray-600 mb-1">{vms_label}:</div>
              <div
                v-for="vm in props.row.vm_names"
                :key="vm"
                class="text-sm text-gray-700 ml-2"
              >
                {{{{ vm }}}}
              </div>
            </div>
          </q-td>
        </q-tr>
        ''',
    )


@ui.page("/layout/print")
async def layout_print_page(request: Request) -> None:
    """Render a print-optimised layout recommendations page for Playwright PDF export."""
    from store_predict.pipeline.layout_models import PlacementConstraints

    token = request.query_params.get("token", "")
    data: dict[str, Any] | None = print_session.consume(token)

    ui.add_head_html(f"<style>{_PRINT_CSS}</style>")
    await ui.context.client.connected()

    if not data:
        ui.label("Invalid or expired print token.").classes("text-red-600 p-8")
        return

    locale_str = str(data.get("locale", "fr"))
    set_locale(locale_str)

    vm_data = cast("list[dict[str, Any]]", data.get("vm_data", []))
    project_name = str(data.get("project_name", ""))

    if not vm_data:
        ui.label("No data to print.").classes("text-gray-500 p-8")
        return

    # Reconstruct constraints from session data
    constraint_data = data.get("constraints", {})
    constraints = PlacementConstraints(**constraint_data) if constraint_data else PlacementConstraints()

    summary: CalculationSummary = calculate(vm_data)
    proposals = generate_all_proposals(summary, constraints)

    with ui.column().classes("w-full p-6 gap-6"):
        # Title
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ui.label(t("layout_page.title")).classes("text-2xl font-bold")
            if project_name:
                ui.label(project_name).classes("text-lg text-gray-500")

        # Strategy comparison table
        metric_rows = _layout_metric_rows(proposals)
        comp_columns = [
            {"name": "metric", "label": t("layout_page.metric"), "field": "metric", "align": "left"},
            {"name": "consolidation", "label": t("strategy.consolidation"), "field": "consolidation", "align": "right"},
            {"name": "performance", "label": t("strategy.performance"), "field": "performance", "align": "right"},
            {"name": "uniform", "label": t("strategy.uniform"), "field": "uniform", "align": "right"},
        ]
        comp_rows = [
            {
                "metric": t(f"metrics.{key}"),
                "consolidation": consol_val,
                "performance": perf_val,
                "uniform": uni_val,
            }
            for key, consol_val, perf_val, uni_val in metric_rows
        ]
        ui.table(columns=comp_columns, rows=comp_rows).classes("w-full")

        # Per-strategy datastore detail
        for proposal in proposals:
            strategy_label = t(f"strategy.{proposal.strategy_name}")
            ui.label(strategy_label).classes("text-xl font-bold mt-6 mb-2")
            ui.label(t(f"strategy.{proposal.strategy_name}_desc")).classes("text-sm text-gray-500 mb-2")

            if not proposal.datastores:
                ui.label(t("layout_page.no_datastores")).classes("text-gray-400 italic")
                continue

            _build_print_datastore_table(proposal.datastores)
