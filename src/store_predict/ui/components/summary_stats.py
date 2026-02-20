"""Summary statistics cards component for VM data."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from store_predict.i18n import t


def build_summary_stats(row_data: list[dict[str, Any]]) -> ui.row:
    """Build a row of 4 summary statistic cards from VM row data.

    Cards displayed:
        1. Total VMs -- count of rows
        2. Total Provisioned -- sum of provisioned_mib, shown as GiB
        3. Avg DRR -- mean of drr values
        4. Effective Capacity -- sum of (provisioned_mib / drr) per row, as GiB

    Args:
        row_data: List of VM row dicts. Expected keys:
            ``provisioned_mib`` (default 0) and ``drr`` (default 5.0).

    Returns:
        A ``ui.row`` element containing the four stat cards.
    """
    total_vms = len(row_data)

    total_provisioned = sum(r.get("provisioned_mib", 0) for r in row_data)

    avg_drr = sum(r.get("drr", 5.0) for r in row_data) / total_vms if total_vms > 0 else 0.0

    total_effective = sum(r.get("provisioned_mib", 0) / r.get("drr", 5.0) for r in row_data)

    stats = [
        (t("stats.total_vms"), str(total_vms)),
        (t("stats.total_provisioned"), f"{total_provisioned / 1024:.1f} GiB"),
        (t("stats.avg_drr"), f"{avg_drr:.1f}x"),
        (t("stats.effective_capacity"), f"{total_effective / 1024:.1f} GiB"),
    ]

    row = ui.row().classes("w-full gap-4")
    with row:
        for label, value in stats:
            with ui.card().classes("flex-1 p-4"):
                ui.label(label).classes("text-sm text-gray-500 dark:text-gray-400")
                ui.label(value).classes("text-2xl font-bold")

    return row
