"""Review page -- inspect and edit VM workload classifications."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from store_predict.config import DRR_CSV_PATH, StorageModel
from store_predict.i18n import t
from store_predict.services.drr_table import DRRTable, apply_storage_model
from store_predict.ui.components.summary_stats import build_summary_stats
from store_predict.ui.components.vm_table import create_vm_table
from store_predict.ui.components.workload_dialog import WorkloadDialog
from store_predict.ui.layout import layout
from store_predict.ui.state import (
    clear_session_data,
    get_project_name,
    get_scope_selection,
    get_storage_model,
    get_workload_options,
    load_filtered_session_data,
    load_rule_suggestions,
    save_filtered_rows,
    set_storage_model,
)

# Columns sent to AG Grid as rowData.  Trimmed from the full session record
# to reduce the JSON payload (~35% smaller) and avoid sending fields that
# the review page never displays.  The full record is preserved in session
# storage and written back on every cell-change save.
_GRID_COLS: frozenset[str] = frozenset(
    {
        "vm_name",
        "workload_category",
        "workload_subcategory",
        "drr",
        "provisioned_mib",
        "classification_confidence",
        "num_cpus",
        "memory_mib",
        "avg_iops",
        "peak_iops",
        "os_name",
        "vm_description",
        "in_use_mib",
        "iops_8k_equivalent",
        "peak_throughput_mbs",
        "datacenter",
        "cluster",
        "row_index",
    }
)


def _to_grid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a trimmed copy of *rows* containing only AG Grid-needed columns."""
    return [{k: v for k, v in row.items() if k in _GRID_COLS} for row in rows]


async def _on_quick_filter(e: Any, grid: ui.aggrid) -> None:
    """Apply AG Grid quickFilterText on each keystroke."""
    await grid.run_grid_method("setGridOption", "quickFilterText", e.value or "")


@ui.page("/review")
async def review_page() -> None:
    """Review classified VMs with editable workload assignments."""
    await ui.context.client.connected()
    df = load_filtered_session_data()
    if df is None:
        with (
            layout("StorePredict - Review"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("upload_file", size="3rem").classes("text-gray-400")
            ui.label(t("review.no_data")).classes("text-xl text-gray-500")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return

    # Load DRR reference data
    drr_table = DRRTable.from_csv(DRR_CSV_PATH)
    workload_options = get_workload_options()
    categories = drr_table.categories

    # Prepare row data for AG Grid — replace NaN with None for JSON serialization
    # pandas where() won't convert NaN to None in numeric columns, so post-process dicts
    row_data: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]
    for row in row_data:
        for key, val in row.items():
            if isinstance(val, float) and val != val:  # NaN check (NaN != NaN)
                row[key] = None

    # Apply stored storage model (re-apply in case user navigated back from report)
    apply_storage_model(row_data, get_storage_model(), drr_table)

    with (
        layout("StorePredict - Review"),
        ui.column().classes("w-full p-4 gap-4"),
    ):
        # Title row with scope indicator
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-3"):
                ui.label(t("review.title")).classes("text-2xl font-bold")
                # Scope badge — show which datacenters/clusters are active
                selected_dcs, selected_cls = get_scope_selection()
                if selected_dcs or selected_cls:
                    parts = []
                    if selected_dcs:
                        parts.append(f"{len(selected_dcs)} DC")
                    if selected_cls:
                        parts.append(f"{len(selected_cls)} CL")
                    scope_label = ", ".join(parts)
                    ui.badge(scope_label, color="blue").classes("text-xs").tooltip(
                        ", ".join(selected_dcs + selected_cls)
                    )
            project = get_project_name()
            if project:
                ui.label(t("review.project_label", name=project)).classes("text-lg text-gray-500")

        # Storage model selector — switches DRR calculation strategy
        current_model = get_storage_model()
        storage_toggle = (
            ui.toggle(
                {
                    StorageModel.POWERSTORE: t("storage_model.powerstore"),
                    StorageModel.POWERFLEX: t("storage_model.powerflex"),
                    StorageModel.POWERVAULT: t("storage_model.powervault"),
                },
                value=current_model,
            )
            .classes("mb-2")
            .tooltip(t("tooltip.storage_model"))
        )

        async def _on_model_change(new_model: StorageModel) -> None:
            set_storage_model(new_model)
            apply_storage_model(row_data, new_model, drr_table)
            save_filtered_rows(row_data, get_project_name())
            trimmed = _to_grid_rows(row_data)
            grid.options["rowData"] = trimmed
            grid.run_grid_method("setGridOption", "rowData", trimmed)
            _rebuild_stats(stats_container, row_data)

        storage_toggle.on_value_change(lambda e: _on_model_change(e.value))

        # Summary stats container (will be rebuilt on changes)
        stats_container = ui.column().classes("w-full")
        with stats_container:
            build_summary_stats(row_data)

        # Build "Category / Subcategory" labels for inline dropdown
        subcategory_labels = [f"{opt['category']} / {opt['subcategory']}" for opt in workload_options]

        # Detect performance data availability (None/empty from NaN replacement)
        def _has_iops(val: object) -> bool:
            if val is None or val == "":
                return False
            try:
                return float(val) > 0  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return False

        has_perf = any(_has_iops(r.get("peak_iops")) for r in row_data)

        # Detail bar — shows supplementary columns for the clicked VM
        detail_bar = ui.row().classes("w-full items-start gap-4 p-3 bg-gray-50 border rounded-lg min-h-12")
        with detail_bar:
            ui.label(t("detail_bar.placeholder")).classes("text-sm text-gray-400 italic")

        # AG Grid table — assigned first so toolbar closures can reference the name
        grid = create_vm_table(
            _to_grid_rows(row_data),
            categories,
            on_cell_changed=lambda e: _handle_cell_change(e, row_data, drr_table, grid, stats_container),
            on_row_clicked=lambda e: _handle_row_click(e, detail_bar, has_perf),
            subcategory_labels=subcategory_labels,
            has_performance_data=has_perf,
        )

        # Toolbar: quick filter + column visibility panel (placed after grid so
        # the grid variable is in scope for the closures — NiceGUI renders
        # elements in declaration order but fires callbacks after full page build)
        with ui.row().classes("w-full items-start gap-4 mb-2 flex-wrap"):
            # Quick filter input
            ui.input(
                placeholder=t("review.search_placeholder"),
                on_change=lambda e: _on_quick_filter(e, grid),
            ).classes("flex-1 max-w-sm").props("clearable dense outlined prepend-inner-icon=search").tooltip(
                t("tooltip.quick_filter")
            )

            # Column visibility panel (custom — AG Grid sidebar is Enterprise-only)
            toggleable_columns: list[tuple[str, str]] = [
                ("datacenter", "columns.datacenter"),
                ("cluster", "columns.cluster"),
                ("num_cpus", "columns.num_cpus"),
                ("memory_mib", "columns.memory_mib"),
                ("avg_iops", "columns.avg_iops"),
                ("peak_iops", "columns.peak_iops"),
            ]
            with ui.expansion(t("review.column_panel_title"), icon="view_column").classes("border rounded"):
                ui.label(t("review.column_panel_tip")).classes("text-xs text-gray-500 mb-2")
                with ui.row().classes("items-center gap-6 flex-wrap"):
                    for _field, _key in toggleable_columns:

                        async def _toggle_col(e: Any, f: str = _field) -> None:
                            await grid.run_grid_method("setColumnsVisible", [f], e.value)

                        ui.checkbox(t(_key), value=False, on_change=_toggle_col)

        # Bulk actions + navigation
        with ui.row().classes("w-full justify-between mt-4"):

            def _new_analysis() -> None:
                clear_session_data()
                ui.navigate.to("/upload")

            ui.button(
                t("review.new_analysis"),
                on_click=_new_analysis,
                icon="restart_alt",
            ).classes("bg-gray-200 text-gray-800").tooltip(t("tooltip.new_analysis"))
            ui.button(
                t("review.bulk_update"),
                on_click=lambda: _handle_bulk_update(
                    row_data,
                    drr_table,
                    workload_options,
                    grid,
                    stats_container,
                ),
                icon="edit",
            ).classes("bg-orange-700 text-white").tooltip(t("tooltip.bulk_update"))
            ui.button(
                t("review.generate_report"),
                on_click=lambda: ui.navigate.to("/report"),
            ).classes("bg-blue-700 text-white")

        # Proposed rule suggestions from LLM (shown only when suggestions exist)
        _build_rule_suggestions_panel()


def _rebuild_stats(stats_container: ui.column, row_data: list[dict[str, Any]]) -> None:
    """Clear and rebuild the summary stats in the container."""
    stats_container.clear()
    with stats_container:
        build_summary_stats(row_data)


def _build_rule_suggestions_panel() -> None:
    """Render a collapsible panel of LLM-proposed classification rules.

    Each suggestion shows a copy-pasteable ``ClassificationRule(...)`` snippet
    that the developer can add to ``build_default_rules`` in classification.py
    to avoid future LLM calls for the same keyword pattern.

    The panel is hidden when there are no suggestions this session.
    """
    suggestions = load_rule_suggestions()
    if not suggestions:
        return

    with ui.expansion(
        t("rule_suggestions.title"),
        icon="lightbulb",
        caption=t("rule_suggestions.subtitle"),
    ).classes("w-full border border-yellow-300 rounded-lg bg-yellow-50"):
        ui.label(t("rule_suggestions.description")).classes("text-sm text-gray-600 mb-2")

        for suggestion in suggestions:
            # Compute a safe rule name from the keyword (title-case)
            rule_name = suggestion.keyword.title()
            # Estimate a priority: database → 1xx range, else 3xx (infrastructure)
            # This is a hint only — the developer will adjust.
            priority_hint = 110 + len(suggestions) if "Database" in suggestion.category else 360

            snippet = (
                f"ClassificationRule(\n"
                f'    name="{rule_name}",\n'
                f'    category="{suggestion.category}",\n'
                f'    subcategory="{suggestion.subcategory}",\n'
                f"    priority={priority_hint},\n"
                f'    vm_name_patterns=_patterns("{suggestion.keyword}"),\n'
                f"),"
            )

            examples_str = ", ".join(suggestion.vm_examples[:3])
            badge_label = t("rule_suggestions.vm_count", count=suggestion.count)

            with ui.card().classes("w-full p-3 gap-2 bg-white border border-yellow-200"):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.badge(suggestion.keyword).classes("bg-yellow-500 text-white font-mono text-xs")
                        ui.label(f"→ {suggestion.category}").classes("text-sm font-semibold")
                        ui.badge(badge_label).classes("bg-gray-200 text-gray-700 text-xs")
                    ui.button(
                        t("rule_suggestions.copy"),
                        icon="content_copy",
                        on_click=lambda s=snippet: ui.run_javascript(f"navigator.clipboard.writeText({s!r})"),
                    ).classes("text-xs bg-gray-100 text-gray-700").props("flat dense")

                ui.label(t("rule_suggestions.examples", examples=examples_str)).classes("text-xs text-gray-500")
                ui.code(snippet, language="python").classes("w-full text-xs")


async def _handle_bulk_update(
    row_data: list[dict[str, Any]],
    drr_table: DRRTable,
    workload_options: list[dict[str, Any]],
    grid: ui.aggrid,
    stats_container: ui.column,
) -> None:
    """Apply a workload category to all selected rows."""
    selected = await grid.get_selected_rows()
    if not selected:
        ui.notify(t("review.no_rows_selected"), type="warning")
        return

    # Build options for the dialog (plain string labels)
    options_list = [str(opt["label"]) for opt in workload_options]
    dialog = WorkloadDialog(
        t("dialog.workloads_for", vm_name=f"{len(selected)} selected VMs"),
        [],
        options_list,
    )
    result = await dialog

    if result is None or len(result) == 0:
        return

    # Resolve selected label to category/subcategory
    selected_label = result[0]
    new_category = ""
    new_subcategory = ""
    for opt in workload_options:
        if opt["label"] == selected_label:
            new_category = str(opt["category"])
            new_subcategory = str(opt["subcategory"])
            break

    if not new_category:
        return

    new_drr = drr_table.get_ratio(new_category, new_subcategory)
    selected_ids = {int(r["row_index"]) for r in selected}

    # Update all selected rows
    for row in row_data:
        if int(row.get("row_index", -1)) in selected_ids:
            row["workload_category"] = new_category
            row["workload_subcategory"] = new_subcategory
            row["drr"] = new_drr

    # Capture filter/page state before update
    filter_model = await grid.run_grid_method("getFilterModel")
    current_page = await grid.run_grid_method("paginationGetCurrentPage")

    # Refresh grid and stats — keep Python-side options in sync so
    # any subsequent update_grid() cycle preserves the data.
    trimmed = _to_grid_rows(row_data)
    grid.options["rowData"] = trimmed
    grid.run_grid_method("setGridOption", "rowData", trimmed)
    _rebuild_stats(stats_container, row_data)

    # Restore filter/page state
    if filter_model:
        await grid.run_grid_method("setFilterModel", filter_model)
    if current_page is not None and current_page > 0:
        await grid.run_grid_method("paginationGoToPage", current_page)

    # Persist to session
    save_filtered_rows(row_data, get_project_name())
    ui.notify(
        t("review.updated_notify", count=len(selected_ids), category=new_category, subcategory=new_subcategory),
        type="positive",
    )


async def _handle_cell_change(
    e: object,
    row_data: list[dict[str, Any]],
    drr_table: DRRTable,
    grid: ui.aggrid,
    stats_container: ui.column,
) -> None:
    """Handle inline cell edit (workload dropdown or DRR manual edit).

    Parses "Category / Subcategory" labels and preserves filter/page state.
    Allows direct DRR editing for custom overrides.
    """
    args = e.args  # type: ignore[attr-defined]
    col_id = args.get("colId", "")
    changed_data = args.get("data", {})
    row_idx = int(changed_data.get("row_index", -1))
    new_value = args.get("newValue", "")

    if col_id == "drr":
        # Direct DRR edit — user overrides the ratio manually
        try:
            custom_drr = max(float(new_value), 0.1)
        except (TypeError, ValueError):
            return
        for row in row_data:
            if int(row.get("row_index", -2)) == row_idx:
                row["drr"] = custom_drr
                break
    elif col_id in ("workload_category", "workload_subcategory"):
        # Parse "Category / Subcategory" label format
        if " / " in new_value:
            new_category, subcategory = new_value.split(" / ", 1)
        else:
            new_category = new_value
            subcategory = ""
            for entry in drr_table.entries:
                if entry.category == new_category:
                    subcategory = entry.subcategory
                    break

        new_drr = drr_table.get_ratio(new_category, subcategory)
        for row in row_data:
            if int(row.get("row_index", -2)) == row_idx:
                row["workload_category"] = new_category
                row["workload_subcategory"] = subcategory
                row["drr"] = new_drr
                break
    else:
        return

    # Capture filter/page state before update
    filter_model = await grid.run_grid_method("getFilterModel")
    current_page = await grid.run_grid_method("paginationGetCurrentPage")

    # Refresh grid and stats — keep Python-side options in sync so
    # any subsequent update_grid() cycle preserves the data.
    trimmed = _to_grid_rows(row_data)
    grid.options["rowData"] = trimmed
    grid.run_grid_method("setGridOption", "rowData", trimmed)
    _rebuild_stats(stats_container, row_data)

    # Restore filter/page state after update
    if filter_model:
        await grid.run_grid_method("setFilterModel", filter_model)
    if current_page is not None and current_page > 0:
        await grid.run_grid_method("paginationGoToPage", current_page)

    # Persist to session
    save_filtered_rows(row_data, get_project_name())


def _update_detail_bar(detail_bar: ui.row, row: dict[str, Any], has_performance_data: bool) -> None:
    """Rebuild the detail bar with supplementary fields for the clicked VM."""

    def _fmt_mib(val: object) -> str:
        try:
            return f"{int(float(val)):,} MiB"  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "—"

    def _fmt_num(val: object) -> str:
        try:
            return f"{int(float(val)):,}"  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "—"

    def _fmt_mbs(val: object) -> str:
        try:
            return f"{float(val):.1f} MB/s"  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "—"

    detail_bar.clear()
    with detail_bar:
        fields: list[tuple[str, str]] = [
            (t("detail_bar.os"), str(row.get("os_name") or "—")),
            (t("detail_bar.description"), str(row.get("vm_description") or "—")),
            (t("columns.datacenter"), str(row.get("datacenter") or "—")),
            (t("columns.cluster"), str(row.get("cluster") or "—")),
            (t("detail_bar.in_use"), _fmt_mib(row.get("in_use_mib"))),
        ]
        if has_performance_data:
            fields += [
                (t("detail_bar.peak_iops"), _fmt_num(row.get("peak_iops"))),
                (t("detail_bar.iops_8k"), _fmt_num(row.get("iops_8k_equivalent"))),
                (t("detail_bar.peak_mbs"), _fmt_mbs(row.get("peak_throughput_mbs"))),
            ]
        for label, value in fields:
            with ui.column().classes("gap-0 min-w-28"):
                ui.label(label).classes("text-xs text-gray-500 font-medium uppercase tracking-wide")
                ui.label(value).classes("text-sm text-gray-800 font-mono truncate max-w-xs")


def _handle_row_click(
    e: object,
    detail_bar: ui.row,
    has_performance_data: bool = False,
) -> None:
    """Handle row click — update the detail bar with supplementary VM data."""
    args = e.args  # type: ignore[attr-defined]
    row = args.get("data", {})
    _update_detail_bar(detail_bar, row, has_performance_data)
