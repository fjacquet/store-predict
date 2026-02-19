"""Review page -- inspect and edit VM workload classifications."""

from __future__ import annotations

from typing import Any

import pandas as pd
from nicegui import ui

from store_predict.config import DRR_CSV_PATH
from store_predict.services.drr_table import DRRTable
from store_predict.ui.components.summary_stats import build_summary_stats
from store_predict.ui.components.vm_table import create_vm_table
from store_predict.ui.components.workload_dialog import WorkloadDialog
from store_predict.ui.layout import layout
from store_predict.ui.state import (
    get_project_name,
    get_workload_options,
    load_session_data,
    save_session_data,
)


@ui.page("/review")
async def review_page() -> None:
    """Review classified VMs with editable workload assignments."""
    await ui.context.client.connected()
    df = load_session_data()
    if df is None:
        with (
            layout("StorePredict - Review"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
        ):
            ui.label("No data uploaded yet.").classes("text-xl text-gray-500")
            ui.link("Go to Upload", "/upload").classes("text-blue-600 underline text-lg")
        return

    # Load DRR reference data
    drr_table = DRRTable.from_csv(DRR_CSV_PATH)
    workload_options = get_workload_options()
    categories = drr_table.categories

    # Prepare row data for AG Grid
    row_data: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]

    with (
        layout("StorePredict - Review"),
        ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"),
    ):
        # Title row
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Review Classifications").classes("text-2xl font-bold")
            project = get_project_name()
            if project:
                ui.label(f"Project: {project}").classes("text-lg text-gray-500")

        # Summary stats container (will be rebuilt on changes)
        stats_container = ui.column().classes("w-full")
        with stats_container:
            build_summary_stats(row_data)

        # AG Grid table
        grid = create_vm_table(
            row_data,
            categories,
            on_cell_changed=lambda e: _handle_cell_change(
                e, row_data, drr_table, grid, stats_container
            ),
            on_row_clicked=lambda e: _handle_row_click(
                e, row_data, drr_table, workload_options, grid, stats_container
            ),
        )


def _rebuild_stats(stats_container: ui.column, row_data: list[dict[str, Any]]) -> None:
    """Clear and rebuild the summary stats in the container."""
    stats_container.clear()
    with stats_container:
        build_summary_stats(row_data)


def _handle_cell_change(
    e: object,
    row_data: list[dict[str, Any]],
    drr_table: DRRTable,
    grid: ui.aggrid,
    stats_container: ui.column,
) -> None:
    """Handle inline cell edit (workload category dropdown change)."""
    args = e.args  # type: ignore[attr-defined]
    col_id = args.get("colId", "")
    if col_id != "workload_category":
        return

    changed_data = args.get("data", {})
    vm_name = changed_data.get("vm_name", "")
    new_category = args.get("newValue", "")

    # Find first matching subcategory for the new category
    subcategory = ""
    for entry in drr_table.entries:
        if entry.category == new_category:
            subcategory = entry.subcategory
            break

    new_drr = drr_table.get_ratio(new_category, subcategory)

    # Update the row in row_data
    for row in row_data:
        if row.get("vm_name") == vm_name:
            row["workload_category"] = new_category
            row["workload_subcategory"] = subcategory
            row["drr"] = new_drr
            break

    # Refresh grid and stats
    grid.options["rowData"] = row_data
    grid.update()
    _rebuild_stats(stats_container, row_data)

    # Persist to session
    save_session_data(pd.DataFrame(row_data), get_project_name())


async def _handle_row_click(
    e: object,
    row_data: list[dict[str, Any]],
    drr_table: DRRTable,
    workload_options: list[dict[str, Any]],
    grid: ui.aggrid,
    stats_container: ui.column,
) -> None:
    """Handle row click -- open multi-select workload dialog."""
    args = e.args  # type: ignore[attr-defined]
    row = args.get("data", {})
    vm_name = row.get("vm_name", "")
    current_category = row.get("workload_category", "")

    # Build options list for dialog (label/value pairs)
    options_list = [{"label": opt["label"], "value": opt["label"]} for opt in workload_options]

    # Current selection as list of labels
    current_labels = []
    for opt in workload_options:
        if opt["category"] == current_category:
            current_labels.append(opt["label"])
            break

    dialog = WorkloadDialog(vm_name, current_labels, options_list)
    result = await dialog

    if result is None or len(result) == 0:
        return

    # Build workload tuples from selected labels for DRR lookup
    workload_tuples: list[tuple[str, str]] = []
    first_category = ""
    first_subcategory = ""
    for selected_label in result:
        for opt in workload_options:
            if opt["label"] == selected_label:
                cat = str(opt["category"])
                sub = str(opt["subcategory"])
                workload_tuples.append((cat, sub))
                if not first_category:
                    first_category = cat
                    first_subcategory = sub
                break

    # Calculate conservative DRR (minimum across selected workloads)
    conservative_drr = drr_table.get_conservative_ratio(workload_tuples)

    # Update the row
    display_category = (
        first_category if len(workload_tuples) == 1 else ", ".join(t[0] for t in workload_tuples)
    )
    for r in row_data:
        if r.get("vm_name") == vm_name:
            r["workload_category"] = display_category
            r["workload_subcategory"] = first_subcategory
            r["drr"] = conservative_drr
            break

    # Refresh grid and stats
    grid.options["rowData"] = row_data
    grid.update()
    _rebuild_stats(stats_container, row_data)

    # Persist to session
    save_session_data(pd.DataFrame(row_data), get_project_name())
