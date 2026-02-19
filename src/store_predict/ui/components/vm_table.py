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

    Returns:
        The configured ui.aggrid instance.
    """
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
            "field": "workload_category",
            "headerName": "Workload Category",
            "editable": True,
            "singleClickEdit": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": workload_categories},
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "workload_subcategory",
            "headerName": "Subcategory",
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

    grid = ui.aggrid(
        {
            "columnDefs": column_defs,
            "rowData": row_data,
            "pagination": True,
            "paginationPageSize": 50,
            "rowSelection": {"mode": "singleRow"},
            "stopEditingWhenCellsLoseFocus": True,
            "domLayout": "autoHeight",
        }
    ).classes("w-full")

    if on_cell_changed:
        grid.on("cellValueChanged", on_cell_changed)
    if on_row_clicked:
        grid.on("rowClicked", on_row_clicked)

    return grid
