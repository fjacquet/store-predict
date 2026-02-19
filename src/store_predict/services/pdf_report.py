"""PDF report generator for StorePredict sizing reports.

Produces a branded one-page PDF from a CalculationSummary using ReportLab
Platypus with Vera fonts for full French character support.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

    from store_predict.pipeline.calculation import CalculationSummary

__all__ = ["format_storage", "generate_report_pdf", "sanitize_filename"]

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONT_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("VeraBd", os.path.join(_FONT_DIR, "VeraBd.ttf")))

# Brand colour
_BRAND_BLUE = colors.HexColor("#1e3a5f")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def format_storage(mib: float) -> str:
    """Convert MiB to a human-readable GiB string, with TiB if >= 1024 GiB."""
    gib = mib / 1024.0
    if gib >= 1024.0:
        tib = gib / 1024.0
        return f"{gib:.1f} GiB ({tib:.1f} TiB)"
    return f"{gib:.1f} GiB"


def sanitize_filename(name: str) -> str:
    """Replace non-alphanumeric characters with underscores.

    Returns ``"report"`` for empty input.
    """
    if not name or not name.strip():
        return "report"
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


# ---------------------------------------------------------------------------
# Header callback
# ---------------------------------------------------------------------------
def _draw_header(
    canvas: Canvas,
    doc: SimpleDocTemplate,
    project_name: str,
) -> None:
    """Draw branded header bar on the first page."""
    canvas.saveState()
    width, height = A4

    # Dark blue bar
    bar_height = 50
    canvas.setFillColor(_BRAND_BLUE)
    canvas.rect(0, height - bar_height, width, bar_height, fill=1, stroke=0)

    # White title
    canvas.setFillColor(colors.white)
    canvas.setFont("VeraBd", 18)
    canvas.drawString(20 * mm, height - 35, "StorePredict Sizing Report")

    # Project name + date below bar
    canvas.setFillColor(colors.black)
    canvas.setFont("Vera", 11)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    canvas.drawString(20 * mm, height - bar_height - 18, f"{project_name}  |  {date_str}")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_report_pdf(summary: CalculationSummary, project_name: str) -> bytes:
    """Generate a branded PDF sizing report and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label for the header.

    Returns:
        PDF document as ``bytes``.
    """
    buf = BytesIO()
    margin = 20 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin + 55,  # extra room for header bar
        bottomMargin=margin,
        title=f"StorePredict Report - {project_name}",
    )

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SPHeading",
        parent=styles["Heading2"],
        fontName="VeraBd",
        fontSize=13,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "SPBody",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10,
        leading=14,
    )

    story: list[object] = []

    # --- Summary section ---------------------------------------------------
    story.append(Paragraph("Summary", heading_style))
    summary_lines = [
        f"<b>Total VMs:</b> {summary.total_vms}",
        f"<b>Provisioned:</b> {format_storage(summary.total_provisioned_mib)}",
        f"<b>In Use:</b> {format_storage(summary.total_in_use_mib)}",
        f"<b>Weighted Avg DRR:</b> {summary.weighted_avg_drr:.2f}",
        f"<b>Required Capacity:</b> {format_storage(summary.total_required_mib)}",
    ]
    for line in summary_lines:
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 10))

    # --- Workload breakdown table ------------------------------------------
    story.append(Paragraph("Workload Breakdown", heading_style))

    header = ["Category", "VMs", "Provisioned (GiB)", "Avg DRR", "Required (GiB)"]
    table_data: list[list[str]] = [header]

    for grp in summary.workload_groups:
        table_data.append(
            [
                grp.category,
                str(grp.vm_count),
                f"{grp.total_provisioned_mib / 1024:.1f}",
                f"{grp.avg_drr:.2f}",
                f"{grp.total_required_mib / 1024:.1f}",
            ]
        )

    # Totals row
    table_data.append(
        [
            "TOTAL",
            str(summary.total_vms),
            f"{summary.total_provisioned_mib / 1024:.1f}",
            f"{summary.weighted_avg_drr:.2f}",
            f"{summary.total_required_mib / 1024:.1f}",
        ]
    )

    col_widths = [180, 50, 100, 70, 100]
    table = Table(table_data, colWidths=col_widths)

    # Style
    style_cmds: list[tuple[object, ...]] = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "VeraBd"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Body
        ("FONTNAME", (0, 1), (-1, -2), "Vera"),
        ("FONTSIZE", (0, 1), (-1, -2), 9),
        # Totals row (last)
        ("FONTNAME", (0, -1), (-1, -1), "VeraBd"),
        ("FONTSIZE", (0, -1), (-1, -1), 9),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    # Alternating row colours (skip header row 0 and totals row -1)
    for i in range(1, len(table_data) - 1):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f0f0f0")))

    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    # --- Build PDF ---------------------------------------------------------
    def on_first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _draw_header(canvas, doc, project_name)

    doc.build(story, onFirstPage=on_first_page)
    return buf.getvalue()
