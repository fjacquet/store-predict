"""Clickable confidence-triage chips that filter the VM review grid.

Surfaces how many VMs landed in each classification confidence tier and lets the
engineer isolate the ones needing attention (``default``/Unknown) with one click.
Filtering is delegated to AG Grid's ``setFilterModel`` on the
``classification_confidence`` column, so it composes with the grid's own filters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

from store_predict.i18n import t

if TYPE_CHECKING:
    from collections.abc import Iterable

# (confidence value, Quasar color, chip text color). None = the "All" reset chip.
_TIERS: tuple[tuple[str | None, str, str], ...] = (
    (None, "primary", "white"),
    ("override", "positive", "white"),
    ("semantic", "info", "white"),
    ("default", "warning", "dark"),
)


def build_confidence_filters(row_data: Iterable[dict[str, Any]], grid: ui.aggrid) -> ui.row:
    """Build a row of clickable chips filtering *grid* by classification confidence.

    Each chip shows its tier's VM count; clicking applies an AG Grid equals-filter
    on ``classification_confidence`` (the "All" chip clears it). Returns the row.
    """
    counts = {"override": 0, "semantic": 0, "default": 0}
    total = 0
    for record in row_data:
        total += 1
        value = record.get("classification_confidence")
        if value in counts:
            counts[value] += 1

    chips: dict[str | None, ui.chip] = {}

    def _select(active: str | None) -> None:
        for key, chip in chips.items():
            if key == active:
                chip.props(remove="outline")
            else:
                chip.props("outline")

    async def _apply(active: str | None) -> None:
        _select(active)
        model: dict[str, Any] = (
            {}
            if active is None
            else {"classification_confidence": {"filterType": "text", "type": "equals", "filter": active}}
        )
        await grid.run_grid_method("setFilterModel", model)

    row = ui.row().classes("w-full items-center gap-2 flex-wrap")
    with row:
        ui.label(t("review.filter_label")).classes("text-xs font-semibold uppercase tracking-wide mr-1").style(
            "color:var(--sp-muted)"
        )
        for value, color, text_color in _TIERS:
            label = t("review.filter_all") if value is None else value
            count = total if value is None else counts[value]
            chip = ui.chip(f"{label} · {count}", color=color).props(f"clickable text-color={text_color}")
            chip.on("click", lambda v=value: _apply(v))
            chips[value] = chip

    _select(None)  # "All" active by default (grid shows everything)
    return row
