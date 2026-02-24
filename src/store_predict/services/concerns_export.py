"""Standalone export module for health check concerns.

Provides generate_concerns_pdf() and generate_concerns_csv() functions,
independent of the main sizing report pipeline. Pure service module with
zero UI imports.
"""

from __future__ import annotations

import csv
import io
import os
from datetime import UTC, datetime

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from store_predict.pipeline.health_checks import HealthCheckResult, Severity

__all__ = ["generate_concerns_csv", "generate_concerns_pdf"]

# ---------------------------------------------------------------------------
# Font registration (same pattern as pdf_report.py)
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONT_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("VeraBd", os.path.join(_FONT_DIR, "VeraBd.ttf")))

# ---------------------------------------------------------------------------
# Severity colour map
# ---------------------------------------------------------------------------
_SEVERITY_COLORS: dict[Severity, str] = {
    Severity.CRITICAL: "#dc2626",
    Severity.WARNING: "#f59e0b",
    Severity.INFO: "#3b82f6",
}

_CSV_HEADER = ["severity", "check_id", "title", "detail", "remediation", "affected_count", "cluster"]


# ---------------------------------------------------------------------------
# CSV generator
# ---------------------------------------------------------------------------


def generate_concerns_csv(health_result: HealthCheckResult) -> bytes:
    """Generate a CSV export of all health findings.

    Returns UTF-8 with BOM bytes (Excel-compatible). The header row is always
    present; an empty findings tuple produces a header-only CSV without error.

    Args:
        health_result: Aggregated health check findings.

    Returns:
        CSV as UTF-8-BOM bytes.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_HEADER)

    for finding in health_result.findings:
        writer.writerow(
            [
                finding.severity.value,
                finding.check_id,
                finding.title,
                finding.detail,
                finding.remediation,
                str(finding.affected_count),
                finding.cluster,
            ]
        )

    return buf.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# PDF generator
# ---------------------------------------------------------------------------


def generate_concerns_pdf(
    health_result: HealthCheckResult,
    project_name: str = "",
    locale: str = "fr",
) -> bytes:
    """Generate a standalone PDF report of health check findings.

    Produces a branded A4 PDF with a cover header, severity summary bar,
    severity legend, and one section per finding with remediation hint.
    Works independently of the main sizing report pipeline.

    Args:
        health_result: Aggregated health check findings.
        project_name: Customer / project label for the header. Optional.
        locale: Language hint (currently unused for PDF text — strings are
            in English as this is an internal engineering document).

    Returns:
        PDF document as bytes.
    """
    buf = io.BytesIO()
    margin = 20 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title="Health Check Concerns Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ConcernTitle",
        parent=styles["Heading1"],
        fontName="VeraBd",
        fontSize=18,
        spaceAfter=4,
        textColor=colors.HexColor("#1e3a5f"),
    )
    subtitle_style = ParagraphStyle(
        "ConcernSubtitle",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=11,
        spaceAfter=2,
        textColor=colors.HexColor("#374151"),
    )
    legend_style = ParagraphStyle(
        "ConcernLegend",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=9,
        spaceAfter=4,
        textColor=colors.HexColor("#6b7280"),
        italics=True,
    )
    body_style = ParagraphStyle(
        "ConcernBody",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10,
        leading=14,
    )
    remediation_style = ParagraphStyle(
        "ConcernRemediation",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
    )

    story = []

    # --- Header ---
    story.append(Paragraph("Health Check Concerns Report", title_style))
    if project_name:
        story.append(Paragraph(f"Project: {project_name}", subtitle_style))
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    story.append(Paragraph(f"Generated: {date_str}", subtitle_style))
    story.append(Spacer(1, 12))

    # --- Summary bar ---
    critical_count = health_result.critical_count
    warning_count = health_result.warning_count
    info_count = health_result.info_count

    summary_parts = []
    if critical_count > 0:
        summary_parts.append(
            Paragraph(
                f'<font color="#dc2626"><b>{critical_count} Critical</b></font>',
                body_style,
            )
        )
    if warning_count > 0:
        summary_parts.append(
            Paragraph(
                f'<font color="#f59e0b"><b>{warning_count} Warning</b></font>',
                body_style,
            )
        )
    if info_count > 0:
        summary_parts.append(
            Paragraph(
                f'<font color="#3b82f6"><b>{info_count} Info</b></font>',
                body_style,
            )
        )

    if summary_parts:
        for part in summary_parts:
            story.append(part)
    else:
        story.append(Paragraph("No concerns found — environment looks healthy.", body_style))

    story.append(Spacer(1, 6))

    # --- Severity legend ---
    story.append(
        Paragraph(
            "<i>Severity levels: Critical = immediate action required; "
            "Warning = review recommended; Info = informational note.</i>",
            legend_style,
        )
    )
    story.append(Spacer(1, 10))

    # --- Findings ---
    for finding in health_result.findings:
        sev_color_hex = _SEVERITY_COLORS.get(finding.severity, "#6b7280")
        sev_color = colors.HexColor(sev_color_hex)
        sev_label = finding.severity.value.upper()

        # Row 1: severity badge + title
        badge_cell = Paragraph(
            f'<font color="white"><b>{sev_label}</b></font>',
            ParagraphStyle(
                "Badge",
                parent=styles["Normal"],
                fontName="VeraBd",
                fontSize=9,
                textColor=colors.white,
            ),
        )
        title_text = finding.title
        title_cell = Paragraph(title_text, body_style)

        # Cluster annotation
        cluster_note = f" ({finding.cluster})" if finding.cluster else ""
        if cluster_note:
            title_cell = Paragraph(f"{title_text}{cluster_note}", body_style)

        # Row 2: detail + remediation (spans both columns)
        detail_text = finding.detail
        remediation_text = f"<i>Remediation: {finding.remediation}</i>" if finding.remediation else ""
        combined = detail_text
        if remediation_text:
            combined = f"{detail_text}<br/><br/>{remediation_text}"
        detail_cell = Paragraph(combined, remediation_style)

        affected_note = ""
        if finding.affected_count > 0:
            affected_note = f"Affected: {finding.affected_count} VM(s)"

        # Build table: 2 columns (badge col narrow, title col wide)
        page_width = A4[0] - 2 * margin
        badge_col_width = 70
        title_col_width = page_width - badge_col_width

        table_data = [
            [badge_cell, title_cell],
            ["", detail_cell],
        ]
        if affected_note:
            table_data.append(["", Paragraph(affected_note, legend_style)])

        finding_table = Table(
            table_data,
            colWidths=[badge_col_width, title_col_width],
        )
        finding_table.setStyle(
            TableStyle(
                [
                    # Badge background
                    ("BACKGROUND", (0, 0), (0, 0), sev_color),
                    ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    # Left border colour on all rows
                    ("LINEAFTER", (-1, 0), (-1, -1), 0, colors.white),
                    ("LINEBEFORE", (0, 0), (0, -1), 4, sev_color),
                    # Table outline
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#f3f4f6")),
                    # Padding
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    # Row 2+ spans (detail)
                    ("SPAN", (0, 1), (0, 1)),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fafafa")),
                    ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(finding_table)
        story.append(Spacer(1, 8))

    # --- Build PDF ---
    doc.build(story)
    return buf.getvalue()
