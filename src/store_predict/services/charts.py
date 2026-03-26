"""ECharts option dicts for web UI report page visualizations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from store_predict.i18n import t

if TYPE_CHECKING:
    from store_predict.pipeline.calculation import CalculationSummary, WorkloadGroupResult

__all__ = [
    "echart_before_after_options",
    "echart_drr_bar_options",
    "echart_pie_options",
    "echart_sankey_options",
]

# Dell brand palette
DELL_BLUE = "#007DB8"
LIGHT_BLUE = "#40A8D8"
GREY = "#6C757D"
LIGHT_GREY = "#CED4DA"
DARK_GREY = "#ADB5BD"
DELL_PALETTE = [DELL_BLUE, LIGHT_BLUE, GREY, DARK_GREY, LIGHT_GREY, "#DEE2E6"]


def echart_sankey_options(summary: CalculationSummary) -> dict[str, Any]:
    """Return ECharts Sankey option dict for the data-reduction flow chart.

    Falls back to a before/after bar chart when fewer than 2 workload groups
    are present (Sankey requires at least 2 intermediate nodes to be meaningful).

    When the same workload category appears with different DRR values (due to
    the (category, drr) groupby key), node names get a DRR suffix to avoid
    ECharts Sankey node name collisions (e.g. "Database (5.0x)").
    """
    if len(summary.workload_groups) < 2:
        return echart_before_after_options(summary)

    provisioned_label = t("chart.provisioned")
    required_label = t("chart.required")

    # Detect categories that appear more than once (different DRR values)
    from collections import Counter

    cat_counts = Counter(grp.category for grp in summary.workload_groups)

    def _node_name(grp: WorkloadGroupResult) -> str:
        """Return unique node name, adding DRR suffix only on collision."""
        if cat_counts[grp.category] > 1:
            return f"{grp.category} ({grp.drr:.1f}x)"
        return grp.category

    nodes = [{"name": provisioned_label, "itemStyle": {"color": DELL_BLUE}}]
    for grp in summary.workload_groups:
        nodes.append({"name": _node_name(grp), "itemStyle": {"color": LIGHT_GREY}})
    nodes.append({"name": required_label, "itemStyle": {"color": LIGHT_BLUE}})

    links = []
    for grp in summary.workload_groups:
        links.append(
            {
                "source": provisioned_label,
                "target": _node_name(grp),
                "value": round(grp.total_provisioned_mib / 1024, 1),
            }
        )
        links.append(
            {
                "source": _node_name(grp),
                "target": required_label,
                "value": round(grp.total_required_mib / 1024, 1),
            }
        )

    return {
        "color": DELL_PALETTE,
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "type": "sankey",
                "layout": "none",
                "data": nodes,
                "links": links,
                "lineStyle": {"color": "gradient", "curveness": 0.5},
                "emphasis": {"focus": "adjacency"},
            }
        ],
    }


def echart_pie_options(summary: CalculationSummary) -> dict[str, Any]:
    """Return ECharts donut-pie option dict for workload capacity distribution."""
    data = [
        {"value": round(grp.total_provisioned_mib / 1024, 1), "name": grp.category} for grp in summary.workload_groups
    ]

    subtitle = "" if len(summary.workload_groups) >= 2 else t("chart.single_category")

    return {
        "color": DELL_PALETTE,
        "tooltip": {"trigger": "item"},
        "legend": {"orient": "vertical", "left": "left"},
        "title": {"subtext": subtitle},
        "series": [
            {
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": data,
            }
        ],
    }


def echart_drr_bar_options(summary: CalculationSummary) -> dict[str, Any]:
    """Return ECharts bar option dict showing average DRR per workload category."""
    categories = [grp.category for grp in summary.workload_groups]
    values = [round(grp.avg_drr, 2) for grp in summary.workload_groups]

    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"rotate": 30, "overflow": "truncate", "width": 80},
        },
        "yAxis": {"type": "value", "name": t("chart.drr_axis")},
        "series": [
            {
                "type": "bar",
                "data": values,
                "itemStyle": {"color": DELL_BLUE},
            }
        ],
    }


def echart_before_after_options(summary: CalculationSummary) -> dict[str, Any]:
    """Return ECharts grouped-bar option dict comparing provisioned vs required capacity."""
    categories = [grp.category for grp in summary.workload_groups]
    provisioned = [round(grp.total_provisioned_mib / 1024, 1) for grp in summary.workload_groups]
    required = [round(grp.total_required_mib / 1024, 1) for grp in summary.workload_groups]

    return {
        "tooltip": {"trigger": "axis"},
        "legend": {},
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"rotate": 30, "overflow": "truncate", "width": 80},
        },
        "yAxis": {"type": "value", "name": t("chart.gib_axis")},
        "series": [
            {"name": t("chart.provisioned"), "type": "bar", "data": provisioned, "itemStyle": {"color": DELL_BLUE}},
            {"name": t("chart.required"), "type": "bar", "data": required, "itemStyle": {"color": LIGHT_BLUE}},
        ],
    }
