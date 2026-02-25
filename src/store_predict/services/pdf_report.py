"""PDF report generator for StorePredict sizing reports.

Produces a branded PDF from a CalculationSummary using ReportLab Platypus
with Open Sans Light/SemiBold (falls back to Vera in test environments).
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from store_predict.i18n import t
from store_predict.services.pdf_charts import (
    make_before_after_bar_drawing,
    make_drr_bar_drawing,
    make_pie_drawing,
    make_sankey_image_flowable,
)

if TYPE_CHECKING:
    from reportlab.pdfgen.canvas import Canvas

    from store_predict.pipeline.calculation import CalculationSummary
    from store_predict.pipeline.health_checks import HealthCheckResult
    from store_predict.pipeline.layout_models import LayoutProposal

__all__ = ["_layout_metric_rows", "format_storage", "generate_report_pdf", "sanitize_filename", "validate_logo"]

# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")


def _register_fonts() -> tuple[str, str]:
    """Register Open Sans Light/SemiBold; fall back to Vera if not bundled."""
    light = _DATA_DIR / "OpenSansLight.ttf"
    bold = _DATA_DIR / "OpenSansSemiBold.ttf"
    if light.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("AppFont", str(light)))
        pdfmetrics.registerFont(TTFont("AppFontBd", str(bold)))
        return "AppFont", "AppFontBd"
    pdfmetrics.registerFont(TTFont("AppFont", os.path.join(_FONT_DIR, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("AppFontBd", os.path.join(_FONT_DIR, "VeraBd.ttf")))
    return "AppFont", "AppFontBd"


_FONT_REGULAR, _FONT_BOLD = _register_fonts()

# Brand colour
_BRAND_BLUE = colors.HexColor("#1e3a5f")

# Logo constraints
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_MAX_LOGO_BYTES = 200 * 1024  # 200 KB — keeps tab storage safe
_MAX_LOGO_DIMENSION = 2000  # pixels — reject absurd resolution
_LOGO_HEIGHT_PT = 36  # points — fits in 50pt bar with padding
_LOGO_WIDTH_PT = 80  # points — max display width


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


def _fmt_kpi_storage(mib: float) -> str:
    """Compact single-unit storage label for KPI cards (no wrapping)."""
    gib = mib / 1024.0
    if gib >= 1024.0:
        return f"{gib / 1024.0:.1f} TiB"
    return f"{gib:.0f} GiB"


def sanitize_filename(name: str) -> str:
    """Replace non-alphanumeric characters with underscores.

    Returns ``"report"`` for empty input.
    """
    if not name or not name.strip():
        return "report"
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


# ---------------------------------------------------------------------------
# Layout report helpers
# ---------------------------------------------------------------------------


def _fmt_tib(mib: float) -> str:
    """Format MiB as a TiB string with 2 decimal places."""
    return f"{mib / (1024 * 1024):.2f}"


def _fmt_pct(pct: float) -> str:
    """Format a percentage value with 1 decimal place."""
    return f"{pct:.1f}"


def _layout_metric_rows(proposals: list[LayoutProposal]) -> list[tuple[str, str, str, str]]:
    """Build display rows for the strategy comparison table (PDF and Excel shared).

    Returns a list of tuples: (metric_key, consolidation_val, performance_val, uniform_val).
    Values are pre-formatted strings ready for display.
    """
    p = {prop.strategy_name: prop for prop in proposals}
    c = p["consolidation"].metrics
    perf = p["performance"].metrics
    u = p["uniform"].metrics
    return [
        ("ds_count", str(c.total_ds_count), str(perf.total_ds_count), str(u.total_ds_count)),
        (
            "raw_capacity",
            _fmt_tib(c.total_raw_capacity_mib),
            _fmt_tib(perf.total_raw_capacity_mib),
            _fmt_tib(u.total_raw_capacity_mib),
        ),
        (
            "usable_capacity",
            _fmt_tib(c.total_usable_capacity_mib),
            _fmt_tib(perf.total_usable_capacity_mib),
            _fmt_tib(u.total_usable_capacity_mib),
        ),
        (
            "used_capacity",
            _fmt_tib(c.total_used_capacity_mib),
            _fmt_tib(perf.total_used_capacity_mib),
            _fmt_tib(u.total_used_capacity_mib),
        ),
        (
            "avg_utilization",
            _fmt_pct(c.avg_utilization_pct),
            _fmt_pct(perf.avg_utilization_pct),
            _fmt_pct(u.avg_utilization_pct),
        ),
        (
            "min_utilization",
            _fmt_pct(c.min_utilization_pct),
            _fmt_pct(perf.min_utilization_pct),
            _fmt_pct(u.min_utilization_pct),
        ),
        (
            "max_utilization",
            _fmt_pct(c.max_utilization_pct),
            _fmt_pct(perf.max_utilization_pct),
            _fmt_pct(u.max_utilization_pct),
        ),
        ("avg_vm_density", f"{c.avg_vm_density:.1f}", f"{perf.avg_vm_density:.1f}", f"{u.avg_vm_density:.1f}"),
        ("max_vm_density", str(c.max_vm_density), str(perf.max_vm_density), str(u.max_vm_density)),
        ("total_iops", f"{c.total_iops_placed:,.0f}", f"{perf.total_iops_placed:,.0f}", f"{u.total_iops_placed:,.0f}"),
        (
            "max_iops_ds",
            f"{c.max_iops_single_ds:,.0f}",
            f"{perf.max_iops_single_ds:,.0f}",
            f"{u.max_iops_single_ds:,.0f}",
        ),
        (
            "iops_headroom",
            _fmt_pct(c.iops_headroom_pct),
            _fmt_pct(perf.iops_headroom_pct),
            _fmt_pct(u.iops_headroom_pct),
        ),
        ("isolation_score", f"{c.isolation_score:.2f}", f"{perf.isolation_score:.2f}", f"{u.isolation_score:.2f}"),
        (
            "snapshot_rating",
            c.snapshot_granularity_rating,
            perf.snapshot_granularity_rating,
            u.snapshot_granularity_rating,
        ),
        ("oversized_vms", str(c.oversized_vm_count), str(perf.oversized_vm_count), str(u.oversized_vm_count)),
    ]


# ---------------------------------------------------------------------------
# Header callback
# ---------------------------------------------------------------------------
def _draw_header(
    canvas: Canvas,
    _doc: SimpleDocTemplate,
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
    canvas.setFont(_FONT_BOLD, 18)
    canvas.drawString(x_title, height - 35, report_title)

    # Project name + date below bar
    canvas.setFillColor(colors.black)
    canvas.setFont(_FONT_REGULAR, 11)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    canvas.drawString(20 * mm, height - bar_height - 18, f"{project_name}  |  {date_str}")

    canvas.restoreState()


def _draw_footer(canvas: Canvas, _doc: SimpleDocTemplate) -> None:
    """Draw a page number footer with a thin rule."""
    canvas.saveState()
    width, _ = A4
    margin = 20 * mm
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.line(margin, 18, width - margin, 18)
    canvas.setFont(_FONT_REGULAR, 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(width / 2, 6, str(canvas.getPageNumber()))
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Health findings helpers
# ---------------------------------------------------------------------------


def _category_label(check_id: str) -> str:
    """Map check_id prefix to a translated category label."""
    prefix = check_id.split(".")[0] if "." in check_id else check_id
    key_map = {
        "data_quality": "pdf.findings_category_data_quality",
        "sizing_risk": "pdf.findings_category_sizing_risk",
        "best_practice": "pdf.findings_category_best_practice",
    }
    return t(key_map.get(prefix, f"pdf.findings_category_{prefix}"))


# ---------------------------------------------------------------------------
# Layout detail helper
# ---------------------------------------------------------------------------
def _build_ds_detail_pages(
    story: list[Flowable],
    proposals: list[LayoutProposal],
) -> None:
    """Append per-strategy datastore detail pages to *story*."""
    styles = getSampleStyleSheet()
    subheading_style = ParagraphStyle(
        "DSSubHeading",
        parent=styles["Heading3"],
        fontName=_FONT_BOLD,
        fontSize=10,
        textColor=_BRAND_BLUE,
        spaceAfter=4,
    )
    body_style_ds = ParagraphStyle("DSBody", parent=styles["Normal"], fontName=_FONT_REGULAR, fontSize=9, leading=13)
    strategy_order = ["consolidation", "performance", "uniform"]
    strategy_keys = {
        "consolidation": "strategy.consolidation",
        "performance": "strategy.performance",
        "uniform": "strategy.uniform",
    }
    by_name = {p.strategy_name: p for p in proposals}

    # A4 usable width: 595 - 2x20 mm = 595 - 113 = 482 pt
    ds_col_widths = [100, 55, 55, 40, 30, 55, 147]  # sum = 482
    ds_header = [
        t("ds.name"),
        t("ds.raw_cap"),
        t("ds.used"),
        t("ds.util"),
        t("ds.vms"),
        t("ds.iops"),
        t("ds.workloads"),
    ]

    for strategy_name in strategy_order:
        proposal = by_name.get(strategy_name)
        if proposal is None:
            continue

        story.append(PageBreak())
        story.append(Paragraph(t(strategy_keys[strategy_name]), subheading_style))
        story.append(Paragraph(t(f"strategy.{strategy_name}_desc"), body_style_ds))
        story.append(Spacer(1, 8))

        if not proposal.datastores:
            story.append(Paragraph(t("layout_page.no_datastores"), body_style_ds))
            continue

        # Datastore summary table
        story.append(Paragraph(t("pdf.ds_detail_heading"), subheading_style))
        story.append(Spacer(1, 4))

        ds_data: list[list[str]] = [ds_header]
        for ds in proposal.datastores:
            ds_data.append(
                [
                    ds.name,
                    _fmt_tib(ds.raw_capacity_mib),
                    _fmt_tib(ds.used_capacity_mib),
                    f"{ds.utilization_pct:.1f}%",
                    str(ds.vm_count),
                    f"{ds.total_iops:,.0f}",
                    ", ".join(sorted(ds.workload_types)),
                ]
            )

        ds_table = Table(ds_data, colWidths=ds_col_widths)
        ds_style: list[Any] = [
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (5, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (6, 0), (6, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("WORDWRAP", (6, 1), (6, -1), True),
        ]
        for r_idx, ds in enumerate(proposal.datastores, start=1):
            if ds.utilization_pct > 80:
                ds_style.append(("TEXTCOLOR", (3, r_idx), (3, r_idx), colors.HexColor("#c0392b")))
                ds_style.append(("FONTNAME", (3, r_idx), (3, r_idx), _FONT_BOLD))
            elif ds.utilization_pct > 60:
                ds_style.append(("TEXTCOLOR", (3, r_idx), (3, r_idx), colors.HexColor("#e67e22")))
            if r_idx % 2 == 0:
                ds_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor("#f0f0f0")))
        ds_table.setStyle(TableStyle(ds_style))
        story.append(ds_table)

        # Per-datastore VM lists: DS name as spanning header, VMs in 3-column grid
        story.append(Spacer(1, 10))
        n_cols = 3
        col_w = 482 / n_cols
        for ds in proposal.datastores:
            if not ds.assigned_vms:
                continue
            vm_names = [vm.vm_name for vm in ds.assigned_vms]
            # Header row: DS name spans all columns
            ds_rows: list[list[str]] = [[ds.name, "", ""]]
            for i in range(0, len(vm_names), n_cols):
                chunk = vm_names[i : i + n_cols]
                while len(chunk) < n_cols:
                    chunk.append("")
                ds_rows.append(chunk)
            vm_table = Table(ds_rows, colWidths=[col_w] * n_cols)
            vm_style: list[Any] = [
                # DS name header spanning all columns
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0e8f4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), _BRAND_BLUE),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("LEFTPADDING", (0, 0), (-1, 0), 4),
                # VM name rows
                ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("TOPPADDING", (0, 1), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
                ("LEFTPADDING", (0, 1), (-1, -1), 3),
                ("RIGHTPADDING", (0, 1), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#7EB8D8")),
            ]
            vm_table.setStyle(TableStyle(vm_style))
            story.append(vm_table)
            story.append(Spacer(1, 4))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _make_kpi_cards(kpis: list[tuple[str, str]]) -> Table:
    """Return a full-width KPI card strip with brand-blue background."""
    n = len(kpis)
    col_w = 462.0 / n
    label_style = ParagraphStyle(
        "KPILabel",
        fontName=_FONT_REGULAR,
        fontSize=8,
        textColor=colors.HexColor("#7EB8D8"),
        alignment=1,
    )
    value_style = ParagraphStyle(
        "KPIValue",
        fontName=_FONT_BOLD,
        fontSize=17,
        textColor=colors.white,
        alignment=1,
    )
    labels = [Paragraph(lbl, label_style) for lbl, _ in kpis]
    values = [Paragraph(val, value_style) for _, val in kpis]
    tbl = Table([labels, values], colWidths=[col_w] * n)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _BRAND_BLUE),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.HexColor("#2a5580")),
            ]
        )
    )
    return tbl


def generate_report_pdf(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    dell_logo_bytes: bytes | None = None,
    company_logo_bytes: bytes | None = None,
    health_result: HealthCheckResult | None = None,
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
        health_result: Optional HealthCheckResult for findings pages. When provided,
            a health findings summary table is added to page 1, and a dedicated
            findings detail appendix page is appended.  ``None`` = no findings sections.

    Returns:
        PDF document as ``bytes``.
    """
    # Set process-global locale before any t() calls.
    # Safe: generate_report_pdf() is fully synchronous — no coroutine interleaving.
    _i18n.set("locale", locale)

    # Dell logo only shown when caller explicitly provides bytes
    # (we do not auto-inject the bundled dell_logo.png)

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
        parent=styles["Normal"],
        fontName=_FONT_BOLD,
        fontSize=13,
        textColor=_BRAND_BLUE,
        spaceBefore=10,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "SPBody",
        parent=styles["Normal"],
        fontName=_FONT_REGULAR,
        fontSize=10,
        leading=14,
    )

    story: list[Flowable] = []

    # --- Totals section ----------------------------------------------------
    story.append(Paragraph(t("report.totals_heading"), heading_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))
    story.append(
        _make_kpi_cards(
            [
                (t("pdf.total_vms"), str(summary.total_vms)),
                (t("pdf.total_cpus"), f"{summary.total_cpus:,}"),
                (t("pdf.total_memory"), _fmt_kpi_storage(summary.total_memory_mib)),
            ]
        )
    )
    story.append(Spacer(1, 3))
    story.append(
        _make_kpi_cards(
            [
                (t("pdf.total_provisioned"), _fmt_kpi_storage(summary.total_provisioned_mib)),
                (t("pdf.total_in_use"), _fmt_kpi_storage(summary.total_in_use_mib)),
                (t("pdf.required_capacity"), _fmt_kpi_storage(summary.total_required_mib)),
            ]
        )
    )
    story.append(Spacer(1, 10))

    # --- Averages section --------------------------------------------------
    story.append(Paragraph(t("report.averages_heading"), heading_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))
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
        story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))
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
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))

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
    style_cmds: list[Any] = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Body
        ("FONTNAME", (0, 1), (-1, -2), _FONT_REGULAR),
        ("FONTSIZE", (0, 1), (-1, -2), 9),
        # Totals row (last)
        ("FONTNAME", (0, -1), (-1, -1), _FONT_BOLD),
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

    # --- Health findings summary table (HEXP-01) -----------------------
    if health_result is not None and health_result.has_data:
        health_block: list[Flowable] = [
            Spacer(1, 8),
            Paragraph(t("pdf.findings_summary_heading"), heading_style),
            HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6),
        ]
        if not health_result.findings:
            health_block.append(Paragraph(t("pdf.findings_no_findings"), body_style))
        else:
            _sev_label = {
                "critical": t("pdf.findings_severity_critical"),
                "warning": t("pdf.findings_severity_warning"),
                "info": t("pdf.findings_severity_info"),
            }
            findings_summary_data: list[list[str]] = [[t("pdf.findings_col_severity"), t("pdf.findings_col_count")]]
            for sev_key, label in _sev_label.items():
                count = sum(1 for f in health_result.findings if f.severity == sev_key)
                if count > 0:
                    findings_summary_data.append([label, str(count)])
            if len(findings_summary_data) > 1:
                sev_table = Table(findings_summary_data, colWidths=[120, 60])
                _sev_colors = {
                    "critical": colors.HexColor("#c0392b"),
                    "warning": colors.HexColor("#e67e22"),
                    "info": colors.HexColor("#2980b9"),
                }
                sev_style: list[Any] = [
                    ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
                # Color code severity labels
                for r_idx, row_data in enumerate(findings_summary_data[1:], start=1):
                    sev_name = next((k for k, v in _sev_label.items() if v == row_data[0]), None)
                    if sev_name and sev_name in _sev_colors:
                        sev_style.append(("TEXTCOLOR", (0, r_idx), (0, r_idx), _sev_colors[sev_name]))
                        sev_style.append(("FONTNAME", (0, r_idx), (0, r_idx), _FONT_BOLD))
                sev_table.setStyle(TableStyle(sev_style))
                health_block.append(sev_table)
        story.append(KeepTogether(health_block))

    # --- Page 2: Charts ----------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph(t("pdf.charts_heading"), heading_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))

    # Sankey (full width)
    story.append(make_sankey_image_flowable(summary, width_pt=480, height_pt=180))
    story.append(Spacer(1, 10))

    # Pie + DRR bar side by side via a two-column Table
    chart_row: list[list[Any]] = [
        [
            make_pie_drawing(summary, width=230, height=180),
            make_drr_bar_drawing(summary, width=230, height=180),
        ]
    ]
    chart_table = Table(chart_row, colWidths=[240, 240])
    story.append(chart_table)
    story.append(Spacer(1, 10))

    # Before/after bar (full width)
    story.append(make_before_after_bar_drawing(summary, width=480, height=150))

    # --- Page 3: Layout Recommendations ------------------------------------
    if summary.total_vms > 0:
        from store_predict.pipeline.layout_engine import generate_all_proposals

        proposals = generate_all_proposals(summary)
        story.append(PageBreak())
        story.append(Paragraph(t("pdf.layout_heading"), heading_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))

        layout_header = [
            t("layout_page.metric"),
            t("strategy.consolidation"),
            t("strategy.performance"),
            t("strategy.uniform"),
        ]
        layout_data: list[list[str]] = [layout_header]
        for metric_key, c_val, p_val, u_val in _layout_metric_rows(proposals):
            layout_data.append([t(f"metrics.{metric_key}"), c_val, p_val, u_val])

        layout_col_widths = [160, 100, 100, 100]
        layout_table = Table(layout_data, colWidths=layout_col_widths)
        layout_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(layout_table)
        _build_ds_detail_pages(story, proposals)

    # --- Page N: Findings detail appendix (HEXP-02) --------------------
    if health_result is not None and health_result.has_data and health_result.findings:
        story.append(PageBreak())
        story.append(Paragraph(t("pdf.findings_detail_heading"), heading_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND_BLUE, spaceAfter=6))
        detail_header = [
            t("pdf.findings_col_severity"),
            t("pdf.findings_col_category"),
            t("pdf.findings_col_finding"),
            t("pdf.findings_col_count"),
        ]
        detail_data: list[list[str]] = [detail_header]
        _sev_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_findings = sorted(
            health_result.findings,
            key=lambda f: (_sev_order.get(str(f.severity), 3), f.check_id),
        )
        for finding in sorted_findings:
            sev_str = t(f"pdf.findings_severity_{finding.severity}")
            cat_str = _category_label(finding.check_id)
            title_str = t(finding.title)
            detail_data.append([sev_str, cat_str, title_str, str(finding.affected_count)])
        detail_col_widths = [70, 110, 230, 60]
        detail_table = Table(detail_data, colWidths=detail_col_widths)
        _sev_colors_detail = {
            "critical": colors.HexColor("#c0392b"),
            "warning": colors.HexColor("#e67e22"),
            "info": colors.HexColor("#2980b9"),
        }
        detail_style: list[Any] = [
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("WORDWRAP", (2, 1), (2, -1), True),
        ]
        for r_idx, row_data in enumerate(detail_data[1:], start=1):
            sev_name = next(
                (k for k in _sev_colors_detail if t(f"pdf.findings_severity_{k}") == row_data[0]),
                None,
            )
            if sev_name:
                detail_style.append(("TEXTCOLOR", (0, r_idx), (0, r_idx), _sev_colors_detail[sev_name]))
                detail_style.append(("FONTNAME", (0, r_idx), (0, r_idx), _FONT_BOLD))
            if r_idx % 2 == 0:
                detail_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor("#f0f0f0")))
        detail_table.setStyle(TableStyle(detail_style))
        story.append(detail_table)

    # --- Build PDF ---------------------------------------------------------
    report_title = t("pdf.report_title")

    def on_first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _draw_header(canvas, doc, project_name, report_title, dell_logo_preprocessed, company_logo_preprocessed)
        _draw_footer(canvas, doc)

    def on_later_pages(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _draw_header(canvas, doc, project_name, report_title, dell_logo_preprocessed, company_logo_preprocessed)
        _draw_footer(canvas, doc)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    return buf.getvalue()
