"""AG Grid VM table component with inline workload dropdown editor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

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
    # Use full "Category / Subcategory" labels when available
    dropdown_values = subcategory_labels if subcategory_labels else workload_categories

    column_defs = [
        {
            "field": "vm_name",
            "headerName": "VM Name",
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 200,
        },
        {
            "field": "os_name",
            "headerName": "OS",
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "vm_description",
            "headerName": "Description",
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "minWidth": 150,
        },
        {
            "field": "workload_category",
            "headerName": "Workload Category",
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": dropdown_values},
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "workload_subcategory",
            "headerName": "Subcategory",
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": dropdown_values},
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "drr",
            "headerName": "DRR",
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "floatingFilter": True,
            "valueFormatter": "value.toFixed(1)",
        },
        {
            "field": "provisioned_mib",
            "headerName": "Provisioned (MiB)",
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "valueFormatter": "Math.round(value).toLocaleString()",
        },
        {
            "field": "in_use_mib",
            "headerName": "In Use (MiB)",
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "valueFormatter": "Math.round(value).toLocaleString()",
        },
        {
            "field": "classification_confidence",
            "headerName": "Confidence",
            "sortable": True,
            "filter": "agTextColumnFilter",
        },
    ]

    # Insert performance columns before classification_confidence when data available
    if has_performance_data:
        perf_cols = [
            {
                "field": "peak_iops",
                "headerName": "Peak IOPS",
                "sortable": True,
                "filter": "agNumberColumnFilter",
                "valueFormatter": "value ? Math.round(value).toLocaleString() : ''",
            },
            {
                "field": "iops_8k_equivalent",
                "headerName": "8K Eq. IOPS",
                "sortable": True,
                "filter": "agNumberColumnFilter",
                "valueFormatter": "value ? Math.round(value).toLocaleString() : ''",
            },
            {
                "field": "peak_throughput_mbs",
                "headerName": "Peak MB/s",
                "sortable": True,
                "filter": "agNumberColumnFilter",
                "valueFormatter": "value ? value.toFixed(1) : ''",
            },
        ]
        # Insert before the last column (classification_confidence)
        column_defs = column_defs[:-1] + perf_cols + column_defs[-1:]

    grid = ui.aggrid(
        {
            "columnDefs": column_defs,
            "rowData": row_data,
            "pagination": True,
            "paginationPageSize": 50,
            "rowSelection": {
                "mode": "multiRow",
                "headerCheckbox": True,
                "enableClickSelection": False,
            },
            "getRowId": "params => params.data.vm_name",
            "stopEditingWhenCellsLoseFocus": True,
        }
    ).classes("w-full").style("height: 600px")

    if on_cell_changed:
        grid.on("cellValueChanged", on_cell_changed)
    if on_row_clicked:
        grid.on("rowClicked", on_row_clicked)

    return grid
