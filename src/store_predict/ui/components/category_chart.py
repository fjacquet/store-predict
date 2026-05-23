"""Workload-category distribution donut (ECharts) for the review summary.

Uses NiceGUI's bundled ECharts (``ui.echart`` — no extra dependency) with a
categorical palette anchored on the Midnight Executive identity, matching the
sibling vAtlas tool's chart language. Counts active (non-ignored) VMs per
workload category. Legend text uses a mid-slate readable in light and dark.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from nicegui import ui

from store_predict.i18n import t

# Categorical palette: brand navy/gold/ice first, then distinct accents.
_PALETTE = (
    "#3245B7",  # navy primary
    "#F9B935",  # gold
    "#819AE9",  # light navy
    "#4AA342",  # green
    "#EF8700",  # orange
    "#1E2761",  # deep navy
    "#B0C2F9",  # ice
    "#DF202E",  # red
    "#2CC6B0",  # teal
    "#64748B",  # slate
)


def build_category_chart(row_data: list[dict[str, Any]]) -> ui.echart:
    """Build a donut of active-VM counts per workload category."""
    counts = Counter(
        str(row.get("workload_category", "—")) for row in row_data if not row.get("is_ignored", False)
    )
    data = [{"name": name, "value": value} for name, value in counts.most_common()]
    option: dict[str, Any] = {
        "color": list(_PALETTE),
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {
            "type": "scroll",
            "orient": "vertical",
            "right": "2%",
            "top": "middle",
            "textStyle": {"color": "#94A3B8", "fontSize": 11},
            "pageTextStyle": {"color": "#94A3B8"},
        },
        "series": [
            {
                "name": t("review.filter_label"),
                "type": "pie",
                "radius": ["46%", "72%"],
                "center": ["30%", "50%"],
                "avoidLabelOverlap": True,
                "itemStyle": {"borderWidth": 1, "borderColor": "transparent"},
                "label": {"show": False},
                "data": data,
            }
        ],
    }
    return ui.echart(option).classes("w-full").style("height:240px")
