"""ReportLab Drawing builders and matplotlib Sankey flowable for PDF report page 2."""

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
    """Return a ReportLab Image with a Bezier-curve Sankey rendered via matplotlib Agg (headless).

    Uses matplotlib's non-interactive Agg backend — no display or browser required.
    Flow bands are cubic Bezier sigmoid curves for a professional appearance.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path as MplPath

    if not summary.workload_groups or summary.total_provisioned_mib == 0:
        return Spacer(width_pt, 0)

    groups = summary.workload_groups
    total_prov = summary.total_provisioned_mib
    total_req = summary.total_required_mib

    palette = ["#007DB8", "#40A8D8", "#6C757D", "#ADB5BD", "#CED4DA", "#5B8DB8"]

    # Build figure with Agg canvas (headless — no display needed)
    dpi = 150
    fig = Figure(figsize=(width_pt / 72, height_pt / 72), dpi=dpi, facecolor="white")
    FigureCanvasAgg(fig)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    # Normalised layout (0..1 coordinate space)
    node_w = 0.03
    left_x = 0.05
    right_x = 0.92
    mid_x = (left_x + right_x + node_w) / 2.0 - node_w / 2.0
    usable_h = 0.78
    offset_y = 0.11
    scale = usable_h / total_prov

    prov_h = total_prov * scale
    req_h = total_req * scale
    left_y0 = offset_y + (usable_h - prov_h) / 2.0
    right_y0 = offset_y + (usable_h - req_h) / 2.0

    def _node(x: float, y0: float, h: float, color: str) -> None:
        ax.add_patch(Rectangle((x, y0), node_w, h, facecolor=color, edgecolor="none", zorder=3))

    def _label(x: float, y: float, text: str, size: float = 6.5, va: str = "bottom") -> None:
        ax.text(x, y, text, ha="center", va=va, fontsize=size, color="#333333", zorder=5)

    def _hex_rgba(hx: str, alpha: float) -> tuple[float, float, float, float]:
        return (int(hx[1:3], 16) / 255, int(hx[3:5], 16) / 255, int(hx[5:7], 16) / 255, alpha)

    def _flow_band(x0: float, yb0: float, h0: float, x1: float, yb1: float, h1: float, color: str) -> None:
        """Cubic Bezier sigmoid band connecting two vertical segments."""
        cx = (x0 + x1) / 2.0
        verts = [
            (x0, yb0),
            (cx, yb0), (cx, yb1), (x1, yb1),        # bottom edge: cubic Bezier
            (x1, yb1 + h1),
            (cx, yb1 + h1), (cx, yb0 + h0), (x0, yb0 + h0),  # top edge: cubic Bezier
            (x0, yb0),
        ]
        codes = [
            MplPath.MOVETO,
            MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
            MplPath.LINETO,
            MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
            MplPath.CLOSEPOLY,
        ]
        ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=_hex_rgba(color, 0.35), edgecolor="none", zorder=2))

    # Left node — total provisioned
    _node(left_x, left_y0, prov_h, "#007DB8")
    _label(left_x + node_w / 2, left_y0 + prov_h + 0.03, "Provisioned")
    _label(left_x + node_w / 2, left_y0 - 0.04, f"{total_prov / 1024:.0f} GiB", size=6.0, va="top")

    # Right node — total required
    _node(right_x, right_y0, req_h, "#40A8D8")
    _label(right_x + node_w / 2, right_y0 + req_h + 0.03, "Required")
    _label(right_x + node_w / 2, right_y0 - 0.04, f"{total_req / 1024:.0f} GiB", size=6.0, va="top")

    # Mid nodes + Bezier flow bands
    cur_left_top = left_y0 + prov_h
    cur_right_top = right_y0 + req_h

    for i, grp in enumerate(groups):
        color = palette[i % len(palette)]
        seg_prov_h = max(grp.total_provisioned_mib * scale, 0.005)
        seg_req_h = max(grp.total_required_mib * scale, 0.005)

        seg_left_y0 = cur_left_top - seg_prov_h
        seg_right_y0 = cur_right_top - seg_req_h
        seg_mid_y0 = seg_left_y0
        seg_mid_h = seg_prov_h

        _node(mid_x, seg_mid_y0, seg_mid_h, color)
        if seg_mid_h >= 0.04:
            txt_color = "white" if i < 2 else "#333333"
            ax.text(
                mid_x + node_w / 2, seg_mid_y0 + seg_mid_h / 2,
                grp.category[:12], ha="center", va="center",
                fontsize=5, color=txt_color, zorder=4,
            )

        _flow_band(left_x + node_w, seg_left_y0, seg_prov_h, mid_x, seg_mid_y0, seg_mid_h, color)
        _flow_band(mid_x + node_w, seg_mid_y0, seg_mid_h, right_x, seg_right_y0, seg_req_h, color)

        cur_left_top -= seg_prov_h
        cur_right_top -= seg_req_h

    # Render to PNG bytes and return as ReportLab Image
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    buf.seek(0)
    return Image(buf, width=width_pt, height=height_pt)
