"""AG Grid VM table component with inline workload dropdown editor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

from store_predict.i18n import t
from store_predict.i18n.locale import get_locale

if TYPE_CHECKING:
    from collections.abc import Callable


def create_vm_table(
    row_data: list[dict[str, Any]],
    workload_categories: list[str],
    on_cell_changed: Callable[..., Any] | None = None,
    on_row_clicked: Callable[..., Any] | None = None,
    subcategory_labels: list[str] | None = None,
    has_performance_data: bool = False,
) -> ui.aggrid:
    """Create an AG Grid table for VM data with inline workload editing.

    Args:
        row_data: List of VM row dicts with keys: vm_name, os_name,
            workload_category, workload_subcategory, drr, provisioned_mib,
            in_use_mib, classification_confidence.
        workload_categories: Sorted list of workload category strings
            for the inline dropdown editor.
        on_cell_changed: Optional callback for cellValueChanged events.
        on_row_clicked: Optional callback for rowClicked events.
        subcategory_labels: Optional list of "Category / Subcategory" labels
            for inline dropdown. When provided, the workload_category column
            uses these full labels instead of bare categories.

    Returns:
        The configured ui.aggrid instance.
    """
    locale = get_locale()

    # Inject AG Grid French locale pack via CDN when locale is 'fr'
    if locale == "fr":
        cdn_url = (
            "https://cdn.jsdelivr.net/npm/@ag-grid-community/locale@32.2.2/dist/umd/@ag-grid-community/locale.min.js"
        )
        ui.add_head_html(f'<script src="{cdn_url}" defer></script>')

    # Use full "Category / Subcategory" labels when available
    dropdown_values = subcategory_labels if subcategory_labels else workload_categories

    column_defs = [
        {
            "field": "vm_name",
            "headerName": t("columns.vm_name"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 200,
        },
        {
            "field": "os_name",
            "headerName": t("columns.os"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "vm_description",
            "headerName": t("columns.description"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 150,
        },
        {
            "field": "workload_category",
            "headerName": t("columns.workload_category"),
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": dropdown_values},
            "cellEditorPopup": True,
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 250,
        },
        {
            "field": "workload_subcategory",
            "headerName": t("columns.subcategory"),
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": dropdown_values},
            "cellEditorPopup": True,
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 250,
        },
        {
            "field": "drr",
            "headerName": t("columns.drr"),
            "editable": True,
            "singleClickEdit": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "floatingFilter": True,
            ":valueFormatter": "params => params.value != null ? params.value.toFixed(1) : ''",
        },
        {
            "field": "provisioned_mib",
            "headerName": t("columns.provisioned_mib"),
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : ''",
        },
        {
            "field": "in_use_mib",
            "headerName": t("columns.in_use_mib"),
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : ''",
        },
        {
            "field": "classification_confidence",
            "headerName": t("columns.confidence"),
            "sortable": True,
            "filter": "agTextColumnFilter",
        },
    ]

    # Insert performance columns before classification_confidence when data available
    if has_performance_data:
        perf_cols = [
            {
                "field": "peak_iops",
                "headerName": t("columns.peak_iops"),
                "sortable": True,
                "filter": "agNumberColumnFilter",
                ":valueFormatter": "params => params.value ? Math.round(params.value).toLocaleString() : ''",
            },
            {
                "field": "iops_8k_equivalent",
                "headerName": t("columns.iops_8k"),
                "sortable": True,
                "filter": "agNumberColumnFilter",
                ":valueFormatter": "params => params.value ? Math.round(params.value).toLocaleString() : ''",
            },
            {
                "field": "peak_throughput_mbs",
                "headerName": t("columns.peak_mbs"),
                "sortable": True,
                "filter": "agNumberColumnFilter",
                ":valueFormatter": "params => params.value ? params.value.toFixed(1) : ''",
            },
        ]
        # Insert before the last column (classification_confidence)
        column_defs = column_defs[:-1] + perf_cols + column_defs[-1:]

    grid_options: dict[str, Any] = {
        "columnDefs": column_defs,
        "rowData": row_data,
        "pagination": True,
        "paginationPageSize": 50,
        "rowSelection": {
            "mode": "multiRow",
            "headerCheckbox": True,
            "selectAll": "filtered",
            "enableClickSelection": False,
        },
        ":getRowId": "params => params.data.vm_name",
        "stopEditingWhenCellsLoseFocus": True,
    }

    # Apply French locale text when locale is 'fr'
    if locale == "fr":
        grid_options[":localeText"] = "AG_GRID_LOCALE_FR"

    grid = ui.aggrid(grid_options).classes("w-full").style("height: 600px")

    if on_cell_changed:
        grid.on("cellValueChanged", on_cell_changed)
    if on_row_clicked:
        grid.on("rowClicked", on_row_clicked)

    return grid
