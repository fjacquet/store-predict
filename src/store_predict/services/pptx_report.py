"""PowerPoint report generator for StorePredict sizing decks.

Produces a branded, editable .pptx from a CalculationSummary: a concise
customer-facing pitch deck followed by a technical appendix. Branding matches the
PDF deliverable. Charts that have a native PowerPoint equivalent (pie, column) are
editable; the Sankey is an embedded image.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any

import i18n as _i18n
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from store_predict.services import pptx_charts
from store_predict.services.pdf_report import _layout_metric_rows, format_storage

if TYPE_CHECKING:
    from pptx.slide import Slide

    from store_predict.pipeline.calculation import CalculationSummary
    from store_predict.pipeline.health_checks import HealthCheckResult

__all__ = ["generate_report_pptx"]


def t(key: str, **kwargs: object) -> str:
    """Translate via raw python-i18n using the process-global locale.

    Deliberately NOT the tab-scoped ``store_predict.i18n.t`` wrapper: this module
    runs inside ``run.io_bound`` (a worker thread with no NiceGUI request context),
    where that wrapper's ``get_locale()`` falls back to the default and would ignore
    the ``locale`` argument. ``generate_report_pptx`` sets the locale once via
    ``_i18n.set("locale", locale)``; this mirrors ``excel_report``.
    """
    return str(_i18n.t(key, **kwargs))


# Slide geometry (16:9) and brand colours (match the PDF deliverable).
_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)
_BRAND_NAVY = RGBColor.from_string("1E3A5F")
_WHITE = RGBColor.from_string("FFFFFF")
_DARK = RGBColor.from_string("333333")
_BLANK_LAYOUT = 6  # "Blank" layout in the default template


def _new_blank_slide(prs: Any) -> Slide:
    return prs.slides.add_slide(prs.slide_layouts[_BLANK_LAYOUT])


def _add_header_band(slide: Slide, heading: str) -> None:
    """Draw the brand navy band across the top with a white heading."""
    from pptx.enum.shapes import MSO_SHAPE

    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), _SLIDE_W, Inches(1.0))
    band.fill.solid()
    band.fill.fore_color.rgb = _BRAND_NAVY
    band.line.fill.background()
    band.shadow.inherit = False
    tf = band.text_frame
    tf.margin_left = Inches(0.4)
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = heading
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = _WHITE


def _add_text(
    slide: Slide,
    text: str,
    left: Inches,
    top: Inches,
    width: Inches,
    height: Inches,
    *,
    size: int = 18,
    bold: bool = False,
    color: RGBColor = _DARK,
    align: PP_ALIGN = PP_ALIGN.LEFT,
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_kpi_tile(slide: Slide, label: str, value: str, left: Inches, top: Inches, width: Inches) -> None:
    """A navy tile with a small label and a large value."""
    from pptx.enum.shapes import MSO_SHAPE

    tile = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(1.8))
    tile.fill.solid()
    tile.fill.fore_color.rgb = _BRAND_NAVY
    tile.line.fill.background()
    tile.shadow.inherit = False
    tf = tile.text_frame
    tf.word_wrap = True
    p_label = tf.paragraphs[0]
    p_label.alignment = PP_ALIGN.CENTER
    r_label = p_label.add_run()
    r_label.text = label
    r_label.font.size = Pt(12)
    r_label.font.color.rgb = RGBColor.from_string("9DBBD6")
    p_value = tf.add_paragraph()
    p_value.alignment = PP_ALIGN.CENTER
    r_value = p_value.add_run()
    r_value.text = value
    r_value.font.size = Pt(28)
    r_value.font.bold = True
    r_value.font.color.rgb = _WHITE


def _slide_title(prs: Any, project_name: str, company_logo_bytes: bytes | None) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.report_title"))
    _add_text(
        slide, project_name, Inches(0.6), Inches(2.6), Inches(12), Inches(1), size=40, bold=True, color=_BRAND_NAVY
    )
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    _add_text(slide, date_str, Inches(0.6), Inches(3.6), Inches(12), Inches(0.6), size=18)
    if company_logo_bytes:
        slide.shapes.add_picture(BytesIO(company_logo_bytes), Inches(10.8), Inches(0.15), height=Inches(0.7))


def _slide_exec_summary(prs: Any, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.exec_summary_heading"))
    tiles = [
        (t("stats.total_vms"), f"{summary.total_vms:,}"),
        (t("stats.total_provisioned"), format_storage(summary.total_provisioned_mib)),
        (t("stats.required_capacity"), format_storage(summary.total_required_mib)),
        (t("stats.avg_drr"), f"{summary.weighted_avg_drr:.1f}x"),
    ]
    top = Inches(2.6)
    width = Inches(2.95)
    for i, (label, value) in enumerate(tiles):
        _add_kpi_tile(slide, label, value, Inches(0.6 + i * 3.15), top, width)


def _slide_drr_story(prs: Any, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.drr_story_heading"))
    _add_text(
        slide,
        f"{summary.weighted_avg_drr:.1f}x",
        Inches(0.6),
        Inches(1.3),
        Inches(4),
        Inches(1.2),
        size=54,
        bold=True,
        color=_BRAND_NAVY,
    )
    _add_text(slide, t("pdf.weighted_drr"), Inches(0.6), Inches(2.5), Inches(4), Inches(0.6), size=16)
    pptx_charts.add_before_after_bar(slide, summary, Inches(4.8), Inches(1.4), Inches(8.0), Inches(5.4))


def _slide_workload_mix(prs: Any, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.workload_mix_heading"))
    pptx_charts.add_workload_pie(slide, summary, Inches(0.6), Inches(1.3), Inches(12), Inches(5.6))


def _slide_recommendation(prs: Any, summary: CalculationSummary, health_result: HealthCheckResult | None) -> None:
    from store_predict.pipeline.health_checks import Severity

    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.recommendation_heading"))
    _add_kpi_tile(
        slide,
        t("stats.required_capacity"),
        format_storage(summary.total_required_mib),
        Inches(0.6),
        Inches(2.0),
        Inches(5),
    )
    if health_result is not None and health_result.has_data and health_result.findings:
        n_crit = sum(1 for f in health_result.findings if f.severity == Severity.CRITICAL)
        n_warn = sum(1 for f in health_result.findings if f.severity == Severity.WARNING)
        lines = f"{t('pdf.findings_severity_critical')}: {n_crit}    {t('pdf.findings_severity_warning')}: {n_warn}"
        _add_text(slide, lines, Inches(0.6), Inches(4.2), Inches(11), Inches(0.8), size=18)


def _add_table(slide: Slide, rows: list[list[str]], left: Inches, top: Inches, width: Inches, height: Inches) -> None:
    """Add a styled table; row 0 is the navy header row."""
    n_rows = len(rows)
    n_cols = len(rows[0])
    table = slide.shapes.add_table(n_rows, n_cols, left, top, width, height).table
    for c in range(n_cols):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = _BRAND_NAVY
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = rows[0][c]
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = _WHITE
    for r in range(1, n_rows):
        for c in range(n_cols):
            cell = table.cell(r, c)
            run = cell.text_frame.paragraphs[0].add_run()
            run.text = rows[r][c]
            run.font.size = Pt(11)
            run.font.color.rgb = _DARK


def _slide_breakdown_table(prs: Any, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("report.breakdown_heading"))
    rows: list[list[str]] = [
        [
            t("pdf.table_category"),
            t("pdf.table_vms"),
            t("pdf.table_provisioned"),
            t("pdf.table_avg_drr"),
            t("pdf.table_required"),
        ]
    ]
    for grp in summary.workload_groups:
        rows.append(
            [
                grp.category,
                str(grp.vm_count),
                f"{grp.total_provisioned_mib / 1024:.1f}",
                f"{grp.avg_drr:.2f}",
                f"{grp.total_required_mib / 1024:.1f}",
            ]
        )
    rows.append(
        [
            t("pdf.table_total"),
            str(summary.total_vms),
            f"{summary.total_provisioned_mib / 1024:.1f}",
            f"{summary.weighted_avg_drr:.2f}",
            f"{summary.total_required_mib / 1024:.1f}",
        ]
    )
    _add_table(slide, rows, Inches(0.6), Inches(1.3), Inches(12), Inches(5.5))


def _slide_layout_strategies(prs: Any, summary: CalculationSummary) -> None:
    from store_predict.pipeline.layout_engine import generate_all_proposals

    proposals = generate_all_proposals(summary)
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.layout_heading"))
    rows: list[list[str]] = [
        [t("layout_page.metric"), t("strategy.consolidation"), t("strategy.performance"), t("strategy.uniform")]
    ]
    for metric_key, c_val, p_val, u_val in _layout_metric_rows(proposals):
        rows.append([t(f"metrics.{metric_key}"), c_val, p_val, u_val])
    _add_table(slide, rows, Inches(0.6), Inches(1.2), Inches(12), Inches(6.0))


def _slide_findings(prs: Any, health_result: HealthCheckResult) -> None:
    from store_predict.pipeline.health_checks import Severity

    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.findings_summary_heading"))
    sev_labels = {
        Severity.CRITICAL: t("pdf.findings_severity_critical"),
        Severity.WARNING: t("pdf.findings_severity_warning"),
        Severity.INFO: t("pdf.findings_severity_info"),
    }
    rows: list[list[str]] = [[t("pdf.findings_col_severity"), t("pdf.findings_col_count")]]
    for sev, label in sev_labels.items():
        count = sum(1 for f in health_result.findings if f.severity == sev)
        if count > 0:
            rows.append([label, str(count)])
    _add_table(slide, rows, Inches(0.6), Inches(1.3), Inches(6), Inches(3))


def _slide_charts(prs: Any, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.charts_heading"))
    pptx_charts.add_sankey_picture(slide, summary, Inches(0.6), Inches(1.2), Inches(12), Inches(2.6))
    pptx_charts.add_workload_pie(slide, summary, Inches(0.6), Inches(4.0), Inches(6), Inches(3.2))
    pptx_charts.add_drr_bar(slide, summary, Inches(6.8), Inches(4.0), Inches(6), Inches(3.2))


def generate_report_pptx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    company_logo_bytes: bytes | None = None,
    health_result: HealthCheckResult | None = None,
) -> bytes:
    """Generate a branded PPTX sizing deck and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label for the title slide.
        locale: Language for deck labels (e.g. "fr" or "en"). Defaults to "fr".
        company_logo_bytes: Optional customer logo (already validated upstream).
        health_result: Optional health findings; drives the findings slide.

    Returns:
        The .pptx document as bytes.
    """
    # Set the process-global locale before any t() call. Safe within one call (this
    # function is synchronous — no coroutine interleaving), matching pdf_report/
    # excel_report. NOTE: not thread-safe across *concurrent* report generations in
    # different locales (run.io_bound uses a thread pool); benign in the single-
    # container deployment. A lock or per-call locale= would be needed for multi-user.
    _i18n.set("locale", locale)

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    _slide_title(prs, project_name, company_logo_bytes)
    _slide_exec_summary(prs, summary)
    _slide_drr_story(prs, summary)
    _slide_workload_mix(prs, summary)
    _slide_recommendation(prs, summary, health_result)

    # --- Appendix ---
    _slide_breakdown_table(prs, summary)
    if summary.total_vms > 0:
        _slide_layout_strategies(prs, summary)
    if health_result is not None and health_result.has_data and health_result.findings:
        _slide_findings(prs, health_result)
    _slide_charts(prs, summary)

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
