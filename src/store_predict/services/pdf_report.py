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

import i18n as _i18n
import reportlab
from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from store_predict.config import DELL_LOGO_PATH
from store_predict.i18n import t

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

    from store_predict.pipeline.calculation import CalculationSummary

__all__ = ["format_storage", "generate_report_pdf", "sanitize_filename", "validate_logo"]

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONT_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("VeraBd", os.path.join(_FONT_DIR, "VeraBd.ttf")))

# Brand colour
_BRAND_BLUE = colors.HexColor("#1e3a5f")

# Logo constraints
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_MAX_LOGO_BYTES = 200 * 1024        # 200 KB — keeps tab storage safe
_MAX_LOGO_DIMENSION = 2000          # pixels — reject absurd resolution
_LOGO_HEIGHT_PT = 36                # points — fits in 50pt bar with padding
_LOGO_WIDTH_PT = 80                 # points — max display width


# ---------------------------------------------------------------------------
# Logo helpers
# ---------------------------------------------------------------------------
def _preprocess_logo(raw_bytes: bytes) -> bytes:
    """Normalize any image to RGBA PNG for black-background-safe ReportLab embedding."""
    src = PilImage.open(BytesIO(raw_bytes))
    img: PilImage.Image = src if src.mode in ("RGBA", "RGB") else src.convert("RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def validate_logo(content: bytes, filename: str) -> None:
    """Validate a logo image for format, size, and dimensions.

    Raises:
        IngestionError: If the logo fails any validation check.
    """
    from store_predict.pipeline.errors import IngestionError

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("png", "jpg", "jpeg"):
        raise IngestionError(
            f"Logo must be PNG or JPEG, got '.{ext}'",
            details=f"filename={filename}",
        )

    if len(content) > _MAX_LOGO_BYTES:
        raise IngestionError(
            f"Logo file too large (max {_MAX_LOGO_BYTES // 1024} KB)",
            details=f"size={len(content)}",
        )

    if ext == "png" and not content.startswith(_PNG_MAGIC):
        raise IngestionError(
            "Logo file has invalid PNG magic bytes",
            details=f"filename={filename}",
        )
    if ext in ("jpg", "jpeg") and not content.startswith(_JPEG_MAGIC):
        raise IngestionError(
            "Logo file has invalid JPEG magic bytes",
            details=f"filename={filename}",
        )

    img = PilImage.open(BytesIO(content))
    w, h = img.size
    if w > _MAX_LOGO_DIMENSION or h > _MAX_LOGO_DIMENSION:
        raise IngestionError(
            f"Logo dimensions too large ({w}x{h}px, max {_MAX_LOGO_DIMENSION}px per side)",
            details=f"filename={filename}",
        )


def _load_dell_logo() -> bytes | None:
    """Load Dell partner logo bytes from package data, or return None if missing."""
    try:
        return DELL_LOGO_PATH.read_bytes()
    except FileNotFoundError:
        return None


# Load at module level so Docker paths work without absolute paths at runtime
_DELL_LOGO_BYTES: bytes | None = _load_dell_logo()


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
    report_title: str,
    dell_logo_bytes: bytes | None = None,
    company_logo_bytes: bytes | None = None,
) -> None:
    """Draw branded header bar on the first page."""
    canvas.saveState()
    width, height = A4

    # Dark blue bar
    bar_height = 50
    canvas.setFillColor(_BRAND_BLUE)
    canvas.rect(0, height - bar_height, width, bar_height, fill=1, stroke=0)

    # Draw Dell logo right-aligned in the bar
    if dell_logo_bytes:
        dell_reader = ImageReader(BytesIO(dell_logo_bytes))
        canvas.drawImage(
            dell_reader,
            width - _LOGO_WIDTH_PT - 10,
            height - bar_height + 7,
            width=_LOGO_WIDTH_PT,
            height=_LOGO_HEIGHT_PT,
            mask="auto",
            preserveAspectRatio=True,
        )

    # Draw company logo left-aligned in the bar
    if company_logo_bytes:
        company_reader = ImageReader(BytesIO(company_logo_bytes))
        canvas.drawImage(
            company_reader,
            10,
            height - bar_height + 7,
            width=_LOGO_WIDTH_PT,
            height=_LOGO_HEIGHT_PT,
            mask="auto",
            preserveAspectRatio=True,
        )

    # White title — shift right if company logo present to avoid overlap
    x_title = 100 if company_logo_bytes else 20 * mm
    canvas.setFillColor(colors.white)
    canvas.setFont("VeraBd", 18)
    canvas.drawString(x_title, height - 35, report_title)

    # Project name + date below bar
    canvas.setFillColor(colors.black)
    canvas.setFont("Vera", 11)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    canvas.drawString(20 * mm, height - bar_height - 18, f"{project_name}  |  {date_str}")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_report_pdf(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    dell_logo_bytes: bytes | None = None,
    company_logo_bytes: bytes | None = None,
) -> bytes:
    """Generate a branded PDF sizing report and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label for the header.
        locale: Language for report labels, e.g. ``"fr"`` or ``"en"``.
            Defaults to ``"fr"`` (French is the primary use-case language).
        dell_logo_bytes: Raw bytes of the Dell partner logo PNG/JPEG.
            Defaults to the bundled dell_logo.png if not provided.
        company_logo_bytes: Raw bytes of the customer company logo PNG/JPEG.
            Displayed left-aligned in the header bar.  ``None`` = no logo.

    Returns:
        PDF document as ``bytes``.
    """
    # Set process-global locale before any t() calls.
    # Safe: generate_report_pdf() is fully synchronous — no coroutine interleaving.
    _i18n.set("locale", locale)

    # Default Dell logo to bundled asset when caller does not override
    dell_logo_bytes = dell_logo_bytes if dell_logo_bytes is not None else _DELL_LOGO_BYTES

    # Preprocess logos to RGBA PNG for transparent rendering in ReportLab
    dell_logo_preprocessed = _preprocess_logo(dell_logo_bytes) if dell_logo_bytes else None
    company_logo_preprocessed = _preprocess_logo(company_logo_bytes) if company_logo_bytes else None

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

    # --- Totals section ----------------------------------------------------
    story.append(Paragraph(t("report.totals_heading"), heading_style))
    totals_lines = [
        f"<b>{t('pdf.total_vms')}</b> {summary.total_vms}",
        f"<b>{t('pdf.total_cpus')}</b> {summary.total_cpus:,}",
        f"<b>{t('pdf.total_memory')}</b> {format_storage(summary.total_memory_mib)}",
        f"<b>{t('pdf.total_provisioned')}</b> {format_storage(summary.total_provisioned_mib)}",
        f"<b>{t('pdf.total_in_use')}</b> {format_storage(summary.total_in_use_mib)}",
        f"<b>{t('pdf.required_capacity')}</b> {format_storage(summary.total_required_mib)}",
    ]
    for line in totals_lines:
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 10))

    # --- Averages section --------------------------------------------------
    story.append(Paragraph(t("report.averages_heading"), heading_style))
    avg_lines = [
        f"<b>{t('pdf.avg_cpus')}</b> {summary.avg_vm_cpus:.1f}",
        f"<b>{t('pdf.avg_memory')}</b> {format_storage(summary.avg_vm_memory_mib)}",
        f"<b>{t('pdf.avg_storage')}</b> {format_storage(summary.avg_vm_size_mib)}",
        f"<b>{t('pdf.weighted_drr')}</b> {summary.weighted_avg_drr:.2f}",
        f"<b>{t('pdf.largest_vm')}</b> {summary.largest_vm_name}"
        f" ({format_storage(summary.largest_vm_provisioned_mib)})",
    ]
    for line in avg_lines:
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 10))

    # --- Performance Summary section (only if data available) --------------
    if summary.has_performance_data:
        story.append(Paragraph(t("pdf.performance_heading"), heading_style))
        perf_lines = [
            f"<b>{t('pdf.total_avg_iops')}</b> {summary.total_avg_iops:,.0f}",
            f"<b>{t('pdf.hottest_vm')}</b> {summary.max_vm_peak_iops:,.0f} ({summary.max_vm_peak_iops_name})",
            f"<b>{t('pdf.peak_throughput')}</b> {summary.peak_throughput_mbs:,.1f} MB/s",
            f"<b>{t('pdf.iops_8k')}</b> {summary.total_iops_8k_equivalent:,.0f}",
        ]
        for line in perf_lines:
            story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 10))

    # --- Workload breakdown table ------------------------------------------
    story.append(Paragraph(t("report.breakdown_heading"), heading_style))

    header = [
        t("pdf.table_category"),
        t("pdf.table_vms"),
        t("pdf.table_provisioned"),
        t("pdf.table_avg_drr"),
        t("pdf.table_required"),
    ]
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
            t("pdf.table_total"),
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
    report_title = t("pdf.report_title")

    def on_first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _draw_header(canvas, doc, project_name, report_title, dell_logo_preprocessed, company_logo_preprocessed)

    doc.build(story, onFirstPage=on_first_page)
    return buf.getvalue()
