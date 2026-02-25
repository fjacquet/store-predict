"""ReportLab Drawing builders and Plotly Sankey PNG flowable for PDF report page 2."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.platypus import Flowable, Image, Spacer

if TYPE_CHECKING:
    from store_predict.pipeline.calculation import CalculationSummary

__all__ = [
    "make_before_after_bar_drawing",
    "make_drr_bar_drawing",
    "make_pie_drawing",
    "make_sankey_image_flowable",
]

# Dell brand colours as ReportLab Color objects
DELL_BLUE_RL = colors.HexColor("#007DB8")
LIGHT_BLUE_RL = colors.HexColor("#40A8D8")
GREY_RL = colors.HexColor("#6C757D")
DARK_GREY_RL = colors.HexColor("#ADB5BD")
LIGHT_GREY_RL = colors.HexColor("#CED4DA")
PALE_GREY_RL = colors.HexColor("#DEE2E6")
DELL_PALETTE_RL = [DELL_BLUE_RL, LIGHT_BLUE_RL, GREY_RL, DARK_GREY_RL, LIGHT_GREY_RL, PALE_GREY_RL]


def make_drr_bar_drawing(summary: CalculationSummary, width: int = 400, height: int = 180) -> Drawing:
    """Return a ReportLab Drawing with a vertical bar chart of DRR per workload category."""
    d: Drawing = Drawing(width, height)
    if not summary.workload_groups:
        return d

    bc = VerticalBarChart()
    bc.x = 40
    bc.y = 20
    bc.width = width - 60
    bc.height = height - 40

    categories = [grp.category[:20] for grp in summary.workload_groups]
    bc.data = [tuple(round(grp.avg_drr, 2) for grp in summary.workload_groups)]
    bc.categoryAxis.categoryNames = categories
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.bars[0].fillColor = DELL_BLUE_RL
    bc.valueAxis.valueMin = 0

    d.add(bc)
    return d


def make_before_after_bar_drawing(summary: CalculationSummary, width: int = 500, height: int = 160) -> Drawing:
    """Return a ReportLab Drawing with grouped bars comparing provisioned vs required capacity."""
    d: Drawing = Drawing(width, height)
    if not summary.workload_groups:
        return d

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 20
    bc.width = width - 70
    bc.height = height - 40

    provisioned_tuple = tuple(round(grp.total_provisioned_mib / 1024, 1) for grp in summary.workload_groups)
    required_tuple = tuple(round(grp.total_required_mib / 1024, 1) for grp in summary.workload_groups)
    bc.data = [provisioned_tuple, required_tuple]

    categories = [grp.category[:20] for grp in summary.workload_groups]
    bc.categoryAxis.categoryNames = categories
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.bars[0].fillColor = DELL_BLUE_RL
    bc.bars[1].fillColor = LIGHT_BLUE_RL
    bc.valueAxis.valueMin = 0

    d.add(bc)
    return d


def make_pie_drawing(summary: CalculationSummary, width: int = 250, height: int = 200) -> Drawing:
    """Return a ReportLab Drawing with a pie chart of provisioned capacity by workload category."""
    d: Drawing = Drawing(width, height)
    if not summary.workload_groups:
        return d

    pc = Pie()
    pc.x = 60
    pc.y = 20
    pc.width = 130
    pc.height = 130
    pc.data = [grp.total_provisioned_mib for grp in summary.workload_groups]
    pc.labels = [grp.category[:15] for grp in summary.workload_groups]

    for i in range(len(pc.data)):
        pc.slices[i].fillColor = DELL_PALETTE_RL[i % len(DELL_PALETTE_RL)]

    d.add(pc)
    return d


def make_sankey_image_flowable(summary: CalculationSummary, width_pt: int = 500, height_pt: int = 200) -> Flowable:
    """Return a ReportLab Image flowable containing a Plotly Sankey diagram as a PNG.

    plotly and kaleido are imported lazily to avoid startup cost when the PDF chart
    page is not used.
    """
    import plotly.graph_objects as go
    import plotly.io as pio

    if not summary.workload_groups or summary.total_provisioned_mib == 0:
        return Spacer(width_pt, 0)

    groups = summary.workload_groups
    n = len(groups)

    # Nodes: Provisioned (0), workload categories (1..n), Required (n+1)
    labels = ["Provisioned"] + [grp.category[:20] for grp in groups] + ["Required"]
    node_colors = ["#007DB8"] + ["#CED4DA"] * n + ["#40A8D8"]

    # Links: Provisioned → each category (provisioned GiB), each category → Required (required GiB)
    link_sources = [0] * n + list(range(1, n + 1))
    link_targets = list(range(1, n + 1)) + [n + 1] * n
    link_values = [grp.total_provisioned_mib / 1024 for grp in groups] + [
        grp.total_required_mib / 1024 for grp in groups
    ]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="#cccccc", width=0.5),
                label=labels,
                color=node_colors,
            ),
            link=dict(
                source=link_sources,
                target=link_targets,
                value=link_values,
                color="rgba(0, 125, 184, 0.25)",
            ),
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=11, color="#333333"),
    )

    png_bytes = pio.to_image(fig, format="png", width=int(width_pt * 2), height=int(height_pt * 2), scale=1)
    return Image(BytesIO(png_bytes), width=width_pt, height=height_pt)
