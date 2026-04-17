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

    # Main columns — the 6 columns needed for classification review.
    # Supplementary columns (OS, description, in_use, performance) are shown
    # in the detail bar below the grid when a row is clicked.
    column_defs = [
        {
            "field": "vm_name",
            "headerName": t("columns.vm_name"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 200,
            # Explicit valueGetter required: AG Grid v34's default field-based
            # extraction fails silently for vm_name after NiceGUI's
            # update_grid() destroy/recreate cycle.  The data IS present in
            # row nodes (confirmed via forEachNode + getCellValue) but the
            # default cell renderer receives undefined for params.value.
            ":valueGetter": "params => params.data?.vm_name",
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
            "minWidth": 350,
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
            "minWidth": 350,
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
            "field": "classification_confidence",
            "headerName": t("columns.confidence"),
            "sortable": True,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "is_ignored",
            "headerName": t("columns.is_ignored"),
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agCheckboxCellEditor",
            "cellRenderer": "agCheckboxCellRenderer",
            "sortable": True,
            "filter": "agTextColumnFilter",
            "maxWidth": 110,
        },
        {
            "field": "datacenter",
            "headerName": t("columns.datacenter"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "cluster",
            "headerName": t("columns.cluster"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "num_cpus",
            "headerName": t("columns.num_cpus"),
            "hide": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? params.value.toLocaleString() : '\u2014'",
        },
        {
            "field": "memory_mib",
            "headerName": t("columns.memory_mib"),
            "hide": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '\u2014'",
        },
        {
            "field": "avg_iops",
            "headerName": t("columns.avg_iops"),
            "hide": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '\u2014'",
        },
        {
            "field": "peak_iops",
            "headerName": t("columns.peak_iops"),
            "hide": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '\u2014'",
        },
    ]

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
        ":getRowId": "params => String(params.data.row_index)",
        ":getRowStyle": "params => params.data && params.data.is_ignored ? {opacity:'0.45', fontStyle:'italic'} : null",
        "stopEditingWhenCellsLoseFocus": True,
        # Empty context prevents AG Grid v34 from injecting its internal
        # GridContext (circular refs) into event.context, which would break
        # NiceGUI's JSON serialisation of rowClicked / cellClicked events.
        "context": {},
    }

    # Apply French locale text when locale is 'fr'.
    # Use typeof guard so the grid still works if the CDN hasn't loaded yet.
    if locale == "fr":
        grid_options[":localeText"] = "typeof AG_GRID_LOCALE_FR !== 'undefined' ? AG_GRID_LOCALE_FR : undefined"

    grid = ui.aggrid(grid_options).classes("w-full").style("height: 600px")

    if on_cell_changed:
        grid.on("cellValueChanged", on_cell_changed, args=["colId", "data", "newValue"])
    if on_row_clicked:
        grid.on("rowClicked", on_row_clicked, args=["data", "rowIndex"])

    return grid
