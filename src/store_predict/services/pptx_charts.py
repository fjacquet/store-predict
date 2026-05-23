"""Native PowerPoint chart builders + Sankey picture for the PPTX report.

Charts that have a native PowerPoint equivalent (pie, column) are added as
editable charts so the engineer can restyle them in PowerPoint. The Sankey flow
diagram has no native chart type, so it is embedded as an image rendered by the
shared matplotlib renderer in ``pdf_charts``.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

from store_predict.i18n import t
from store_predict.services.pdf_charts import render_sankey_png

if TYPE_CHECKING:
    from pptx.slide import Slide
    from pptx.util import Length

    from store_predict.pipeline.calculation import CalculationSummary

__all__ = [
    "DELL_PALETTE_HEX",
    "add_before_after_bar",
    "add_drr_bar",
    "add_sankey_picture",
    "add_workload_pie",
]

# Dell-blue palette (matches pdf_charts.DELL_PALETTE_RL) as RGBColor.
DELL_PALETTE_HEX = ("007DB8", "40A8D8", "6C757D", "ADB5BD", "CED4DA", "DEE2E6")
_PALETTE = tuple(RGBColor.from_string(h) for h in DELL_PALETTE_HEX)
_NAVY = RGBColor.from_string("1E3A5F")
_LIGHT_BLUE = RGBColor.from_string("40A8D8")


def add_workload_pie(slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length) -> None:
    """Add an editable pie chart of provisioned capacity per workload category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series("GiB", tuple(grp.total_provisioned_mib / 1024 for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.PIE, x, y, cx, cy, data).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.RIGHT
    chart.legend.include_in_layout = False
    points = chart.series[0].points
    for idx, point in enumerate(points):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = _PALETTE[idx % len(_PALETTE)]


def add_drr_bar(slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length) -> None:
    """Add an editable column chart of average DRR per workload category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series("DRR", tuple(round(grp.avg_drr, 2) for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, data).chart
    chart.has_legend = False
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = _NAVY


def add_before_after_bar(
    slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length
) -> None:
    """Add an editable two-series column chart: provisioned vs required GiB per category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series(t("pptx.provisioned"), tuple(grp.total_provisioned_mib / 1024 for grp in summary.workload_groups))
    data.add_series(t("pptx.required"), tuple(grp.total_required_mib / 1024 for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, data).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = _NAVY
    chart.series[1].format.fill.solid()
    chart.series[1].format.fill.fore_color.rgb = _LIGHT_BLUE


def add_sankey_picture(slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length) -> None:
    """Embed the provisioned→required Sankey as a picture. No-op when there is no data."""
    # width_pt/height_pt only set the render aspect ratio; the picture is sized to (cx, cy).
    png = render_sankey_png(summary, width_pt=640, height_pt=240)
    if png is None:
        return
    slide.shapes.add_picture(BytesIO(png), x, y, width=cx, height=cy)
