"""Layout recommendations page -- side-by-side comparison of three datastore strategies."""

from __future__ import annotations

from typing import Any

from nicegui import app, ui

from store_predict.i18n import t
from store_predict.pipeline.calculation import calculate
from store_predict.pipeline.layout_engine import generate_all_proposals
from store_predict.pipeline.layout_models import LayoutProposal, PlacementConstraints
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
# Results rendering (comparison + placeholder for plan 16-02 detail tabs)
# ---------------------------------------------------------------------------


def _render_results(proposals: list[LayoutProposal]) -> None:
    """Render comparison table inside the results container."""
    _build_comparison_table(proposals)


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

    with ui.expansion(
        t("layout_page.settings_title"),
        icon="settings",
        caption=t("layout_page.settings_subtitle"),
    ).classes("w-full border border-gray-200 rounded-lg"), ui.column().classes("w-full gap-4 p-2"):
        # 1. Max DS capacity — dropdown
        ui.select(
            options=tb_options,
            value=int(constraints.max_ds_capacity_mib),
            label=t("layout_page.max_ds_capacity"),
            on_change=_on_ds_capacity_change,
        ).classes("w-full")

        # 2. Max VMs per DS — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.max_vms_per_ds")).classes("text-sm")
                max_vms_label = ui.label(str(constraints.max_vms_per_ds)).classes(
                    "text-sm font-mono w-8 text-right"
                )
            max_vms_slider = ui.slider(
                min=5,
                max=50,
                step=1,
                value=constraints.max_vms_per_ds,
            ).classes("w-full").props("label-always")
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
        ).classes("w-full")

        # 4. Snapshot reserve % — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.snapshot_reserve")).classes("text-sm")
                snap_label = ui.label(f"{constraints.snapshot_reserve_pct:.0f}%").classes(
                    "text-sm font-mono w-8 text-right"
                )
            snap_slider = ui.slider(
                min=0,
                max=30,
                step=1,
                value=int(constraints.snapshot_reserve_pct),
            ).classes("w-full").props("label-always")
            snap_label.bind_text_from(snap_slider, "value", backward=lambda v: f"{v}%")
            snap_slider.on("change", _on_snapshot_change)

        # 5. Growth margin % — slider
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("layout_page.growth_margin")).classes("text-sm")
                growth_label = ui.label(f"{constraints.growth_margin_pct:.0f}%").classes(
                    "text-sm font-mono w-8 text-right"
                )
            growth_slider = ui.slider(
                min=0,
                max=40,
                step=1,
                value=int(constraints.growth_margin_pct),
            ).classes("w-full").props("label-always")
            growth_label.bind_text_from(growth_slider, "value", backward=lambda v: f"{v}%")
            growth_slider.on("change", _on_growth_change)


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


@ui.page("/layout")
async def layout_page() -> None:
    """Layout recommendations page with three datastore strategies."""
    await ui.context.client.connected()

    vm_data: list[dict[str, Any]] | None = app.storage.tab.get("vm_data")

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

    with layout("StorePredict - Layout"), ui.column().classes("w-full p-4 gap-4"):
        ui.label(t("layout_page.title")).classes("text-2xl font-bold")

        # Results container — holds comparison table; updated on settings change
        results_container = ui.column().classes("w-full")

        # Advanced Settings panel — must be built after results_container is defined
        _build_settings_panel(constraints, vm_data, results_container)

        # Initial render of results
        with results_container:
            _render_results(proposals)
