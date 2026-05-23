"""AG Grid VM table component with inline workload dropdown editor."""

from __future__ import annotations

import json
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

    # Inject the matching AG Grid locale pack for non-English locales. Self-hosted
    # from /public/vendor (offline — no CDN); the bundle exposes AG_GRID_LOCALE_<XX>
    # (FR/DE/IT all present). English uses AG Grid's built-in default.
    ag_locale_global = "" if locale == "en" else f"AG_GRID_LOCALE_{locale.upper()}"
    if ag_locale_global:
        ui.add_head_html('<script src="/public/vendor/ag-grid-locale.min.js" defer></script>')

    # Use full "Category / Subcategory" labels when available
    dropdown_values = subcategory_labels if subcategory_labels else workload_categories

    # Localized confidence labels (current locale), injected into the chip renderer below.
    conf_labels = json.dumps(
        {
            "override": t("confidence.override"),
            "semantic": t("confidence.semantic"),
            "default": t("confidence.default"),
        },
        ensure_ascii=False,
    )

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
            "minWidth": 230,
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
            "minWidth": 300,
        },
        {
            "field": "drr",
            "headerName": t("columns.drr"),
            "editable": True,
            "singleClickEdit": True,
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "floatingFilter": True,
            "minWidth": 90,
            "maxWidth": 110,
            ":valueFormatter": "params => params.value != null ? params.value.toFixed(1) : ''",
        },
        {
            "field": "provisioned_mib",
            "headerName": t("columns.provisioned_mib"),
            "sortable": True,
            "filter": "agNumberColumnFilter",
            "minWidth": 140,
            ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : ''",
        },
        {
            "field": "classification_confidence",
            "headerName": t("columns.confidence"),
            "sortable": True,
            "filter": "agTextColumnFilter",
            "minWidth": 140,
            # Render confidence as a colour-coded chip: green=deterministic
            # override, navy=semantic, amber=Unknown/review (legacy values mapped).
            # The raw value drives the colour class; the localized label is shown.
            ":cellRenderer": (
                "params => {"
                f" const labels = {conf_labels};"
                " const v = params.value || '';"
                " const m = {override:'override', semantic:'semantic', default:'default',"
                " rule_match:'override', os_fallback:'semantic', llm:'muted'};"
                " const k = m[v] || 'default';"
                " const text = labels[v] || v;"
                " return v ? `<span class=\"sp-chip sp-chip-${k}\">${text}</span>` : '';"
                "}"
            ),
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
            "hide": True,
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "cluster",
            "headerName": t("columns.cluster"),
            "hide": True,
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        {
            "field": "vm_folder",
            "headerName": t("columns.vm_folder"),
            "hide": True,
            "sortable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "tooltipField": "vm_folder",
            "minWidth": 240,
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

    # Apply the locale's text pack. The typeof guard keeps the grid working even
    # if the locale script hasn't finished loading yet.
    if ag_locale_global:
        grid_options[":localeText"] = f"typeof {ag_locale_global} !== 'undefined' ? {ag_locale_global} : undefined"

    grid = ui.aggrid(grid_options).classes("w-full").style("height: 600px")

    if on_cell_changed:
        grid.on("cellValueChanged", on_cell_changed, args=["colId", "data", "newValue"])
    if on_row_clicked:
        grid.on("rowClicked", on_row_clicked, args=["data", "rowIndex"])

    return grid
