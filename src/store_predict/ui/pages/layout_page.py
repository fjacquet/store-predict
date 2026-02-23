"""Layout recommendations page -- side-by-side comparison of three datastore strategies."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nicegui import app, ui

from store_predict.config import APP_PORT
from store_predict.i18n import t
from store_predict.i18n.locale import get_locale
from store_predict.pipeline.calculation import CalculationSummary, calculate
from store_predict.pipeline.layout_engine import generate_all_proposals
from store_predict.pipeline.layout_models import DatastoreRecommendation, LayoutProposal, PlacementConstraints
from store_predict.services import playwright_pdf, print_session
from store_predict.services.excel_report import generate_report_xlsx
from store_predict.services.pdf_report import sanitize_filename
from store_predict.ui.layout import layout

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _load_constraints() -> PlacementConstraints:
    """Read constraint values from tab session, using defaults."""
    return PlacementConstraints(
        max_ds_capacity_mib=float(app.storage.tab.get("layout_max_ds_mib", 4 * 1024 * 1024)),
        max_vms_per_ds=int(app.storage.tab.get("layout_max_vms", 25)),
        iops_budget_per_ds=float(app.storage.tab.get("layout_iops_budget", 100_000.0)),
        snapshot_reserve_pct=float(app.storage.tab.get("layout_snapshot_pct", 15.0)),
        growth_margin_pct=float(app.storage.tab.get("layout_growth_pct", 20.0)),
    )


def _save_constraints(c: PlacementConstraints) -> None:
    """Write constraint values to tab session."""
    app.storage.tab["layout_max_ds_mib"] = c.max_ds_capacity_mib
    app.storage.tab["layout_max_vms"] = c.max_vms_per_ds
    app.storage.tab["layout_iops_budget"] = c.iops_budget_per_ds
    app.storage.tab["layout_snapshot_pct"] = c.snapshot_reserve_pct
    app.storage.tab["layout_growth_pct"] = c.growth_margin_pct


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_tib(mib: float) -> str:
    """Format MiB as TiB with 2 decimal places."""
    return f"{mib / (1024 * 1024):.2f} TiB"


def _fmt_pct(value: float) -> str:
    """Format a float as percentage with 1 decimal place."""
    return f"{value:.1f}%"


# ---------------------------------------------------------------------------
# Strategy recommendation
# ---------------------------------------------------------------------------


def _recommend_strategy(proposals: list[LayoutProposal]) -> str:
    """Return strategy_name of the recommended proposal.

    Logic:
    - If highest isolation_score > 0.5 -> "performance"
    - If single workload category across all VMs -> "consolidation"
    - else -> "uniform"
    Ties broken by fewest datastores.
    """
    if not proposals:
        return "uniform"

    # Find all unique workload categories across all proposals
    all_categories: set[str] = set()
    for proposal in proposals:
        for ds in proposal.datastores:
            all_categories.update(ds.workload_types)

    # Check if single workload type (homogeneous)
    if len(all_categories) <= 1:
        return "consolidation"

    # Check if performance has high isolation score
    for proposal in proposals:
        if proposal.strategy_name == "performance" and proposal.metrics.isolation_score > 0.5:
            return "performance"

    # Default: uniform
    return "uniform"


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------


def _build_comparison_table(proposals: list[LayoutProposal]) -> None:
    """Render the side-by-side strategy comparison table."""
    recommended = _recommend_strategy(proposals)

    # Header with strategy names + recommended badge
    ui.label(t("layout_page.comparison_heading")).classes("text-xl font-semibold")

    # Strategy summary cards with recommendation indicator
    with ui.grid().classes("grid grid-cols-3 gap-4 w-full mb-4"):
        for proposal in proposals:
            is_recommended = proposal.strategy_name == recommended
            card_classes = "p-4 text-center border-2"
            if is_recommended:
                card_classes += " border-green-500 bg-green-50"
            else:
                card_classes += " border-gray-200"

            with ui.card().classes(card_classes):
                with ui.row().classes("items-center justify-center gap-2"):
                    strategy_label = t(f"strategy.{proposal.strategy_name}")
                    ui.label(strategy_label).classes("text-lg font-bold")
                    if is_recommended:
                        ui.badge(t("layout_page.recommended"), color="green")
                ui.label(t(f"strategy.{proposal.strategy_name}_desc")).classes("text-sm text-gray-500")
                ui.label(str(proposal.metrics.total_ds_count)).classes("text-3xl font-bold text-blue-700")
                ui.label(t("metrics.ds_count")).classes("text-xs text-gray-500")

    # Full metrics comparison table
    p = proposals
    columns = [
        {"name": "metric", "label": t("layout_page.metric"), "field": "metric", "align": "left"},
        {
            "name": "consolidation",
            "label": t("strategy.consolidation"),
            "field": "consolidation",
            "align": "right",
        },
        {
            "name": "performance",
            "label": t("strategy.performance"),
            "field": "performance",
            "align": "right",
        },
        {
            "name": "uniform",
            "label": t("strategy.uniform"),
            "field": "uniform",
            "align": "right",
        },
    ]

    def _row(metric_key: str, c_val: str, p_val: str, u_val: str) -> dict[str, str]:
        return {
            "metric": t(f"metrics.{metric_key}"),
            "consolidation": c_val,
            "performance": p_val,
            "uniform": u_val,
        }

    rows = [
        _row(
            "ds_count",
            str(p[0].metrics.total_ds_count),
            str(p[1].metrics.total_ds_count),
            str(p[2].metrics.total_ds_count),
        ),
        _row(
            "raw_capacity",
            _fmt_tib(p[0].metrics.total_raw_capacity_mib),
            _fmt_tib(p[1].metrics.total_raw_capacity_mib),
            _fmt_tib(p[2].metrics.total_raw_capacity_mib),
        ),
        _row(
            "usable_capacity",
            _fmt_tib(p[0].metrics.total_usable_capacity_mib),
            _fmt_tib(p[1].metrics.total_usable_capacity_mib),
            _fmt_tib(p[2].metrics.total_usable_capacity_mib),
        ),
        _row(
            "used_capacity",
            _fmt_tib(p[0].metrics.total_used_capacity_mib),
            _fmt_tib(p[1].metrics.total_used_capacity_mib),
            _fmt_tib(p[2].metrics.total_used_capacity_mib),
        ),
        _row(
            "avg_utilization",
            _fmt_pct(p[0].metrics.avg_utilization_pct),
            _fmt_pct(p[1].metrics.avg_utilization_pct),
            _fmt_pct(p[2].metrics.avg_utilization_pct),
        ),
        _row(
            "min_utilization",
            _fmt_pct(p[0].metrics.min_utilization_pct),
            _fmt_pct(p[1].metrics.min_utilization_pct),
            _fmt_pct(p[2].metrics.min_utilization_pct),
        ),
        _row(
            "max_utilization",
            _fmt_pct(p[0].metrics.max_utilization_pct),
            _fmt_pct(p[1].metrics.max_utilization_pct),
            _fmt_pct(p[2].metrics.max_utilization_pct),
        ),
        _row(
            "avg_vm_density",
            f"{p[0].metrics.avg_vm_density:.1f}",
            f"{p[1].metrics.avg_vm_density:.1f}",
            f"{p[2].metrics.avg_vm_density:.1f}",
        ),
        _row(
            "max_vm_density",
            str(p[0].metrics.max_vm_density),
            str(p[1].metrics.max_vm_density),
            str(p[2].metrics.max_vm_density),
        ),
        _row(
            "total_iops",
            f"{p[0].metrics.total_iops_placed:,.0f}",
            f"{p[1].metrics.total_iops_placed:,.0f}",
            f"{p[2].metrics.total_iops_placed:,.0f}",
        ),
        _row(
            "max_iops_ds",
            f"{p[0].metrics.max_iops_single_ds:,.0f}",
            f"{p[1].metrics.max_iops_single_ds:,.0f}",
            f"{p[2].metrics.max_iops_single_ds:,.0f}",
        ),
        _row(
            "iops_headroom",
            _fmt_pct(p[0].metrics.iops_headroom_pct),
            _fmt_pct(p[1].metrics.iops_headroom_pct),
            _fmt_pct(p[2].metrics.iops_headroom_pct),
        ),
        _row(
            "isolation_score",
            f"{p[0].metrics.isolation_score:.2f}",
            f"{p[1].metrics.isolation_score:.2f}",
            f"{p[2].metrics.isolation_score:.2f}",
        ),
        _row(
            "snapshot_rating",
            p[0].metrics.snapshot_granularity_rating,
            p[1].metrics.snapshot_granularity_rating,
            p[2].metrics.snapshot_granularity_rating,
        ),
        _row(
            "oversized_vms",
            str(p[0].metrics.oversized_vm_count),
            str(p[1].metrics.oversized_vm_count),
            str(p[2].metrics.oversized_vm_count),
        ),
    ]

    ui.table(columns=columns, rows=rows).classes("w-full")


# ---------------------------------------------------------------------------
# Expandable datastore table
# ---------------------------------------------------------------------------


def _build_datastore_table(datastores: tuple[DatastoreRecommendation, ...]) -> None:
    """Render a ui.table with expandable rows for VM drill-down."""
    # Expand All / Collapse All buttons
    with ui.row().classes("gap-2 mb-2"):
        ui.button(
            t("layout_page.expand_all"),
            icon="unfold_more",
            on_click=lambda: ui.run_javascript(
                "document.querySelectorAll('.q-table .q-btn .q-icon').forEach(i => {"
                "  if (i.textContent.trim() === 'expand_more') i.closest('button').click();"
                "})"
            ),
        ).props("flat dense size=sm")
        ui.button(
            t("layout_page.collapse_all"),
            icon="unfold_less",
            on_click=lambda: ui.run_javascript(
                "document.querySelectorAll('.q-table .q-btn .q-icon').forEach(i => {"
                "  if (i.textContent.trim() === 'expand_less') i.closest('button').click();"
                "})"
            ),
        ).props("flat dense size=sm")

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
            "util_pct_raw": ds.utilization_pct,
            "vm_count": ds.vm_count,
            "iops": f"{ds.total_iops:,.0f}",
            "workloads": ", ".join(sorted(ds.workload_types)),
            "vm_names": [vm.vm_name for vm in ds.assigned_vms],
        }
        for ds in datastores
    ]

    table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")

    table.add_slot(
        "header",
        r"""
        <q-tr :props="props">
          <q-th auto-width />
          <q-th v-for="col in props.cols" :key="col.name" :props="props">
            {{ col.label }}
          </q-th>
        </q-tr>
        """,
    )

    vms_label = t("ds.vm_list")
    table.add_slot(
        "body",
        f"""
        <q-tr :props="props">
          <q-td auto-width>
            <q-btn
              @click="props.expand = !props.expand"
              :icon="props.expand ? 'expand_less' : 'expand_more'"
              size="sm"
              color="primary"
              round
              dense
              flat
            />
          </q-td>
          <q-td v-for="col in props.cols" :key="col.name" :props="props"
            :class="{{
              'text-red-600 font-bold': col.name === 'util_pct' && props.row.util_pct_raw > 80,
              'text-yellow-600': col.name === 'util_pct' && props.row.util_pct_raw > 60 && props.row.util_pct_raw <= 80,
              'text-green-600': col.name === 'util_pct' && props.row.util_pct_raw <= 60
            }}"
          >
            {{{{ col.value }}}}
          </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
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
        """,
    )


# ---------------------------------------------------------------------------
# Per-strategy detail view
# ---------------------------------------------------------------------------


def _build_strategy_detail(proposal: LayoutProposal) -> None:
    """Render description, summary stats, and expandable datastore table for one strategy."""
    desc_key = f"strategy.{proposal.strategy_name}_desc"
    ui.label(t(desc_key)).classes("text-sm text-gray-500 mb-2")

    m = proposal.metrics
    with ui.row().classes("gap-4 mb-4 flex-wrap"):
        with ui.card().classes("p-3 text-center min-w-[100px]"):
            ui.label(str(m.total_ds_count)).classes("text-2xl font-bold text-blue-700")
            ui.label(t("metrics.ds_count")).classes("text-xs text-gray-500")
        with ui.card().classes("p-3 text-center min-w-[120px]"):
            ui.label(_fmt_tib(m.total_raw_capacity_mib)).classes("text-xl font-bold text-blue-700")
            ui.label(t("metrics.raw_capacity")).classes("text-xs text-gray-500")
        with ui.card().classes("p-3 text-center min-w-[100px]"):
            ui.label(_fmt_pct(m.avg_utilization_pct)).classes("text-xl font-bold text-blue-700")
            ui.label(t("metrics.avg_utilization")).classes("text-xs text-gray-500")
        with ui.card().classes("p-3 text-center min-w-[100px]"):
            ui.label(f"{m.isolation_score:.2f}").classes("text-xl font-bold text-blue-700")
            ui.label(t("metrics.isolation_score")).classes("text-xs text-gray-500").tooltip(
                t("tooltip.isolation_score")
            )
        with ui.card().classes("p-3 text-center min-w-[100px]"):
            ui.label(str(m.oversized_vm_count)).classes("text-xl font-bold text-blue-700")
            ui.label(t("metrics.oversized_vms")).classes("text-xs text-gray-500").tooltip(t("tooltip.oversized_vms"))

    if not proposal.datastores:
        ui.label(t("layout_page.no_datastores")).classes("text-gray-400 italic p-4")
        return

    _build_datastore_table(proposal.datastores)


# ---------------------------------------------------------------------------
# Strategy tabs (three-tab detail view)
# ---------------------------------------------------------------------------


def _build_strategy_tabs(proposals: list[LayoutProposal]) -> None:
    """Render three strategy tabs (Consolidation/Performance/Uniform) with per-datastore detail."""
    ui.label(t("layout_page.detail_tabs_heading")).classes("text-xl font-semibold mt-6")

    # Map strategy names to proposals for easy lookup
    by_name: dict[str, LayoutProposal] = {p.strategy_name: p for p in proposals}

    with ui.tabs().classes("w-full") as tabs:
        tab_consol = ui.tab("consolidation", label=t("strategy.consolidation"), icon="compress")
        tab_perf = ui.tab("performance", label=t("strategy.performance"), icon="speed")
        tab_unif = ui.tab("uniform", label=t("strategy.uniform"), icon="balance")

    with ui.tab_panels(tabs, value=tab_consol).classes("w-full"):
        with ui.tab_panel(tab_consol):
            if "consolidation" in by_name:
                _build_strategy_detail(by_name["consolidation"])
        with ui.tab_panel(tab_perf):
            if "performance" in by_name:
                _build_strategy_detail(by_name["performance"])
        with ui.tab_panel(tab_unif):
            if "uniform" in by_name:
                _build_strategy_detail(by_name["uniform"])


# ---------------------------------------------------------------------------
# Results rendering (comparison + detail tabs)
# ---------------------------------------------------------------------------


def _render_results(proposals: list[LayoutProposal]) -> None:
    """Render comparison table and strategy detail tabs inside the results container."""
    _build_comparison_table(proposals)
    _build_strategy_tabs(proposals)


# ---------------------------------------------------------------------------
# Reactive rebuild
# ---------------------------------------------------------------------------


def _rebuild_layout(
    container: ui.column,
    vm_data: list[dict[str, Any]],
) -> None:
    """Recalculate and re-render the results container."""
    constraints = _load_constraints()
    summary = calculate(vm_data)
    proposals = generate_all_proposals(summary, constraints)
    container.clear()
    with container:
        _render_results(proposals)


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


async def _on_download_layout_pdf(summary: CalculationSummary, project_name: str) -> None:
    """Generate layout PDF via Playwright layout print page and trigger download."""
    locale = get_locale()
    constraints = _load_constraints()

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
        "constraints": {
            "max_ds_capacity_mib": constraints.max_ds_capacity_mib,
            "max_vms_per_ds": constraints.max_vms_per_ds,
            "iops_budget_per_ds": constraints.iops_budget_per_ds,
            "snapshot_reserve_pct": constraints.snapshot_reserve_pct,
            "growth_margin_pct": constraints.growth_margin_pct,
        },
    }
    token = print_session.create(data)
    try:
        pdf_bytes = await playwright_pdf.generate_layout_pdf(token, APP_PORT)
    except Exception:
        ui.notify(t("error.unexpected"), type="negative")
        return

    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_Layout_{safe_name}_{date_str}.pdf"
    ui.download(pdf_bytes, filename=filename, media_type="application/pdf")


def _on_download_layout_excel(summary: CalculationSummary, project_name: str) -> None:
    """Generate Excel workbook (including layout sheet) and trigger download."""
    locale = get_locale()
    xlsx_bytes = generate_report_xlsx(summary, project_name, locale=locale)
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_Layout_{safe_name}_{date_str}.xlsx"
    ui.download(
        xlsx_bytes,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------


def _build_settings_panel(
    constraints: PlacementConstraints,
    vm_data: list[dict[str, Any]],
    results_container: ui.column,
) -> None:
    """Render the Advanced Settings collapsible panel."""

    def _on_ds_capacity_change(e: object) -> None:
        app.storage.tab["layout_max_ds_mib"] = int(e.value)  # type: ignore[attr-defined]
        _rebuild_layout(results_container, vm_data)

    def _on_max_vms_change(e: object) -> None:
        app.storage.tab["layout_max_vms"] = int(e.value)  # type: ignore[attr-defined]
        _rebuild_layout(results_container, vm_data)

    def _on_iops_budget_change(e: object) -> None:
        val = e.value  # type: ignore[attr-defined]
        if val is not None:
            app.storage.tab["layout_iops_budget"] = float(val)
            _rebuild_layout(results_container, vm_data)

    def _on_snapshot_change(e: object) -> None:
        app.storage.tab["layout_snapshot_pct"] = float(e.value)  # type: ignore[attr-defined]
        _rebuild_layout(results_container, vm_data)

    def _on_growth_change(e: object) -> None:
        app.storage.tab["layout_growth_pct"] = float(e.value)  # type: ignore[attr-defined]
        _rebuild_layout(results_container, vm_data)

    tb_options = {
        2 * 1024 * 1024: "2 TB",
        4 * 1024 * 1024: "4 TB",
        8 * 1024 * 1024: "8 TB",
        16 * 1024 * 1024: "16 TB",
        32 * 1024 * 1024: "32 TB",
        64 * 1024 * 1024: "64 TB",
    }

    with (
        ui.expansion(
            t("layout_page.settings_title"),
            icon="settings",
            caption=t("layout_page.settings_subtitle"),
        ).classes("w-full border border-gray-200 rounded-lg"),
        ui.column().classes("w-full gap-4 p-2"),
    ):
        # 1. Max DS capacity — dropdown
        ui.select(
            options=tb_options,
            value=int(constraints.max_ds_capacity_mib),
            label=t("layout_page.max_ds_capacity"),
            on_change=_on_ds_capacity_change,
        ).classes("w-full").tooltip(t("tooltip.max_ds_capacity"))

        # 2. Max VMs per DS — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.max_vms_per_ds")).classes("text-sm")
                max_vms_label = ui.label(str(constraints.max_vms_per_ds)).classes("text-sm font-mono w-8 text-right")
            max_vms_slider = (
                ui.slider(
                    min=5,
                    max=50,
                    step=1,
                    value=constraints.max_vms_per_ds,
                )
                .classes("w-full")
                .props("label-always")
                .tooltip(t("tooltip.max_vms_per_ds"))
            )
            max_vms_label.bind_text_from(max_vms_slider, "value", backward=str)
            max_vms_slider.on("change", _on_max_vms_change)

        # 3. IOPS budget — number input
        ui.number(
            label=t("layout_page.iops_budget"),
            value=constraints.iops_budget_per_ds,
            min=10_000,
            max=1_000_000,
            step=10_000,
            on_change=_on_iops_budget_change,
        ).classes("w-full").tooltip(t("tooltip.iops_budget"))

        # 4. Snapshot reserve % — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.snapshot_reserve")).classes("text-sm")
                snap_label = ui.label(f"{constraints.snapshot_reserve_pct:.0f}%").classes(
                    "text-sm font-mono w-8 text-right"
                )
            snap_slider = (
                ui.slider(
                    min=0,
                    max=30,
                    step=1,
                    value=int(constraints.snapshot_reserve_pct),
                )
                .classes("w-full")
                .props("label-always")
                .tooltip(t("tooltip.snapshot_reserve"))
            )
            snap_label.bind_text_from(snap_slider, "value", backward=lambda v: f"{v}%")
            snap_slider.on("change", _on_snapshot_change)

        # 5. Growth margin % — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.growth_margin")).classes("text-sm")
                growth_label = ui.label(f"{constraints.growth_margin_pct:.0f}%").classes(
                    "text-sm font-mono w-8 text-right"
                )
            growth_slider = (
                ui.slider(
                    min=0,
                    max=40,
                    step=1,
                    value=int(constraints.growth_margin_pct),
                )
                .classes("w-full")
                .props("label-always")
                .tooltip(t("tooltip.growth_margin"))
            )
            growth_label.bind_text_from(growth_slider, "value", backward=lambda v: f"{v}%")
            growth_slider.on("change", _on_growth_change)


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


@ui.page("/layout")
async def layout_page() -> None:
    """Layout recommendations page with three datastore strategies."""
    await ui.context.client.connected()

    from store_predict.ui.state import load_filtered_session_data

    _df = load_filtered_session_data()
    vm_data: list[dict[str, Any]] | None = None
    if _df is not None and not _df.empty:
        vm_data = _df.to_dict(orient="records")  # type: ignore[assignment]
        assert vm_data is not None  # narrowing; guarded by `if _df is not None`
        for _row in vm_data:
            for _k, _v in _row.items():
                if isinstance(_v, float) and _v != _v:
                    _row[_k] = None

    if not vm_data:
        with (
            layout("StorePredict - Layout"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("grid_view", size="3rem").classes("text-gray-400")
            ui.label(t("layout_page.no_data")).classes("text-xl text-gray-500")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return

    constraints = _load_constraints()
    summary = calculate(vm_data)
    proposals = generate_all_proposals(summary, constraints)
    project_name: str = str(app.storage.tab.get("project_name", ""))

    with layout("StorePredict - Layout"), ui.column().classes("w-full p-4 gap-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(t("layout_page.title")).classes("text-2xl font-bold")
            with ui.row().classes("gap-2"):
                pdf_btn = ui.button(
                    t("layout_page.download_pdf"),
                    icon="picture_as_pdf",
                ).classes("bg-blue-700 text-white")
                excel_btn = ui.button(
                    t("layout_page.download_excel"),
                    icon="table_view",
                ).classes("bg-green-700 text-white")

        async def _on_pdf() -> None:
            pdf_btn.disable()
            try:
                await _on_download_layout_pdf(summary, project_name)
            finally:
                pdf_btn.enable()

        def _on_excel() -> None:
            excel_btn.disable()
            try:
                _on_download_layout_excel(summary, project_name)
            finally:
                excel_btn.enable()

        pdf_btn.on("click", _on_pdf)
        excel_btn.on("click", _on_excel)

        # Results container — holds comparison table; updated on settings change
        results_container = ui.column().classes("w-full")

        # Advanced Settings panel — must be built after results_container is defined
        _build_settings_panel(constraints, vm_data, results_container)

        # Initial render of results
        with results_container:
            _render_results(proposals)
