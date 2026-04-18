"""Excel report generator for StorePredict sizing reports.

Produces a styled three-sheet .xlsx workbook from a CalculationSummary using
XlsxWriter with BytesIO for in-memory generation.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import i18n as _i18n
import xlsxwriter

import store_predict.i18n  # noqa: F401 — ensures YAML load_path and config are initialised
from store_predict._sanitizers import safe_excel_cell

if TYPE_CHECKING:
    from xlsxwriter.format import Format

    from store_predict.pipeline.calculation import CalculationSummary
    from store_predict.pipeline.health_checks import HealthCheckResult

__all__ = ["generate_report_xlsx"]

_BRAND_BLUE = "#1e3a5f"
_BRAND_WHITE = "#FFFFFF"
_LIGHT_GREY = "#f0f0f0"


def generate_report_xlsx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    health_result: HealthCheckResult | None = None,
) -> bytes:
    """Generate a styled Excel workbook and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label, embedded as workbook title metadata.
        locale: Language for labels. Defaults to 'fr'.
        health_result: Optional health check results. When provided and has findings,
            a Findings worksheet is appended as the last sheet. Defaults to None
            (backward-compatible — no Findings sheet).

    Returns:
        .xlsx document as bytes (PK ZIP format).
    """
    _i18n.set("locale", locale)

    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"title": project_name})

    _font = "Open Sans"
    _font_light = "Open Sans Light"

    header_fmt = wb.add_format(
        {
            "bold": True,
            "font_name": _font,
            "bg_color": _BRAND_BLUE,
            "font_color": _BRAND_WHITE,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )
    bold_fmt = wb.add_format({"bold": True, "font_name": _font})
    number_fmt = wb.add_format({"font_name": _font_light, "num_format": "0.00", "align": "right"})
    int_fmt = wb.add_format({"font_name": _font_light, "num_format": "0", "align": "right"})
    alt_fmt = wb.add_format({"font_name": _font_light, "bg_color": _LIGHT_GREY})
    alt_right_fmt = wb.add_format(
        {"font_name": _font_light, "bg_color": _LIGHT_GREY, "num_format": "0.00", "align": "right"}
    )
    indent_fmt = wb.add_format({"font_name": _font_light, "indent": 2, "font_color": "#555555"})
    indent_num_fmt = wb.add_format(
        {"font_name": _font_light, "indent": 1, "font_color": "#555555", "num_format": "0.00", "align": "right"}
    )

    _write_summary_sheet(wb, summary, header_fmt, bold_fmt, number_fmt, int_fmt)
    _write_breakdown_sheet(wb, summary, header_fmt, number_fmt, int_fmt, alt_fmt, alt_right_fmt)
    _write_vm_detail_sheet(wb, summary, header_fmt, number_fmt, alt_fmt, alt_right_fmt)
    _write_layout_sheet(wb, summary, header_fmt, bold_fmt, number_fmt, indent_fmt, indent_num_fmt)
    _write_findings_sheet(wb, health_result, header_fmt, alt_fmt)

    wb.close()
    return buf.getvalue()


def _write_summary_sheet(
    wb: xlsxwriter.Workbook,
    summary: CalculationSummary,
    header_fmt: Format,
    bold_fmt: Format,
    number_fmt: Format,
    int_fmt: Format,
) -> None:
    """Write the Summary sheet with label-value pairs."""
    ws = wb.add_worksheet(_i18n.t("excel.sheet_summary"))

    # Header row
    ws.write_row(0, 0, [_i18n.t("excel.col_metric"), _i18n.t("excel.col_value")], header_fmt)

    row = 1

    def write_metric(label: str, value: object, fmt: object = None) -> None:
        nonlocal row
        ws.write(row, 0, label, bold_fmt)
        if fmt is not None:
            ws.write(row, 1, value, fmt)
        else:
            ws.write(row, 1, value)
        row += 1

    write_metric(_i18n.t("pdf.total_vms"), summary.total_vms, int_fmt)
    write_metric(_i18n.t("pdf.total_cpus"), summary.total_cpus, int_fmt)
    write_metric(_i18n.t("pdf.total_memory"), summary.total_memory_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.total_provisioned"), summary.total_provisioned_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.total_in_use"), summary.total_in_use_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.required_capacity"), summary.total_required_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.avg_cpus"), summary.avg_vm_cpus, number_fmt)
    write_metric(_i18n.t("pdf.avg_memory"), summary.avg_vm_memory_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.avg_storage"), summary.avg_vm_size_mib / 1024.0, number_fmt)
    write_metric(_i18n.t("pdf.weighted_drr"), summary.weighted_avg_drr, number_fmt)
    write_metric(_i18n.t("pdf.largest_vm"), safe_excel_cell(summary.largest_vm_name))

    if summary.has_performance_data:
        write_metric(_i18n.t("pdf.total_avg_iops"), summary.total_avg_iops, number_fmt)
        write_metric(
            _i18n.t("pdf.hottest_vm"),
            safe_excel_cell(f"{summary.max_vm_peak_iops_name} ({summary.max_vm_peak_iops:,.0f})"),
        )
        write_metric(_i18n.t("pdf.peak_throughput"), summary.peak_throughput_mbs, number_fmt)
        write_metric(_i18n.t("pdf.iops_8k"), summary.total_iops_8k_equivalent, number_fmt)

    ws.freeze_panes(1, 0)
    ws.autofit()


def _write_breakdown_sheet(
    wb: xlsxwriter.Workbook,
    summary: CalculationSummary,
    header_fmt: Format,
    number_fmt: Format,
    int_fmt: Format,
    alt_fmt: Format,
    alt_right_fmt: Format,
) -> None:
    """Write the Workload Breakdown sheet with category subtotals."""
    ws = wb.add_worksheet(_i18n.t("excel.sheet_breakdown"))

    headers = [
        _i18n.t("excel.col_category"),
        _i18n.t("excel.col_vms"),
        _i18n.t("excel.col_provisioned_gib"),
        _i18n.t("excel.col_avg_drr"),
        _i18n.t("excel.col_required_gib"),
    ]
    ws.write_row(0, 0, headers, header_fmt)

    for body_idx, grp in enumerate(summary.workload_groups):
        row = body_idx + 1
        is_even = body_idx % 2 == 0
        str_fmt = alt_fmt if is_even else None
        num_fmt = alt_right_fmt if is_even else number_fmt
        i_fmt = alt_right_fmt if is_even else int_fmt

        ws.write(row, 0, safe_excel_cell(grp.category), str_fmt)
        ws.write(row, 1, grp.vm_count, i_fmt)
        ws.write(row, 2, grp.total_provisioned_mib / 1024.0, num_fmt)
        ws.write(row, 3, grp.avg_drr, num_fmt)
        ws.write(row, 4, grp.total_required_mib / 1024.0, num_fmt)

    # Totals row
    totals_row = len(summary.workload_groups) + 1
    bold_int_fmt = wb.add_format({"bold": True, "font_name": "Open Sans", "num_format": "0", "align": "right"})
    bold_num_fmt = wb.add_format({"bold": True, "font_name": "Open Sans", "num_format": "0.00", "align": "right"})
    bold_fmt_cell = wb.add_format({"bold": True, "font_name": "Open Sans"})
    ws.write(totals_row, 0, "TOTAL", bold_fmt_cell)
    ws.write(totals_row, 1, summary.total_vms, bold_int_fmt)
    ws.write(totals_row, 2, summary.total_provisioned_mib / 1024.0, bold_num_fmt)
    ws.write(totals_row, 3, summary.weighted_avg_drr, bold_num_fmt)
    ws.write(totals_row, 4, summary.total_required_mib / 1024.0, bold_num_fmt)

    ws.freeze_panes(1, 0)
    ws.autofit()


def _write_vm_detail_sheet(
    wb: xlsxwriter.Workbook,
    summary: CalculationSummary,
    header_fmt: Format,
    number_fmt: Format,
    alt_fmt: Format,
    alt_right_fmt: Format,
) -> None:
    """Write the VM Detail sheet with one row per VMCalculation."""
    ws = wb.add_worksheet(_i18n.t("excel.sheet_vm_detail"))

    headers = [
        _i18n.t("excel.col_vm_name"),
        _i18n.t("excel.col_workload"),
        _i18n.t("excel.col_drr"),
        _i18n.t("excel.col_provisioned_gib"),
        _i18n.t("excel.col_in_use_gib"),
        _i18n.t("excel.col_required_gib"),
    ]
    if summary.has_performance_data:
        headers.extend(
            [
                _i18n.t("excel.col_peak_iops"),
                _i18n.t("excel.col_avg_iops"),
                _i18n.t("excel.col_peak_mbs"),
                _i18n.t("excel.col_iops_8k"),
            ]
        )
    ws.write_row(0, 0, headers, header_fmt)

    for body_idx, vm in enumerate(summary.vm_calculations):
        row = body_idx + 1
        is_even = body_idx % 2 == 0
        str_fmt = alt_fmt if is_even else None
        num_fmt = alt_right_fmt if is_even else number_fmt

        ws.write(row, 0, safe_excel_cell(vm.vm_name), str_fmt)
        ws.write(row, 1, safe_excel_cell(vm.workload_category), str_fmt)
        ws.write(row, 2, vm.drr, num_fmt)
        ws.write(row, 3, vm.provisioned_mib / 1024.0, num_fmt)
        ws.write(row, 4, vm.in_use_mib / 1024.0, num_fmt)
        ws.write(row, 5, vm.required_mib / 1024.0, num_fmt)

        if summary.has_performance_data:
            ws.write(row, 6, vm.peak_iops, num_fmt)
            ws.write(row, 7, vm.avg_iops, num_fmt)
            ws.write(row, 8, vm.peak_throughput_mbs, num_fmt)
            ws.write(row, 9, vm.iops_8k_equivalent, num_fmt)

    ws.freeze_panes(1, 0)
    ws.autofit()


def _write_layout_sheet(
    wb: xlsxwriter.Workbook,
    summary: CalculationSummary,
    header_fmt: Format,
    bold_fmt: Format,
    number_fmt: Format,
    indent_fmt: Format,
    indent_num_fmt: Format,
) -> None:
    """Write the Layout Recommendations sheet with strategy comparison and per-strategy detail."""
    if summary.total_vms == 0:
        return

    from store_predict.pipeline.layout_engine import generate_all_proposals
    from store_predict.services.pdf_report import _layout_metric_rows

    proposals = generate_all_proposals(summary)

    ws = wb.add_worksheet(_i18n.t("excel.sheet_layout"))

    # --- Comparison summary at top ---
    ws.write(0, 0, _i18n.t("layout_page.metric"), header_fmt)
    ws.write(0, 1, _i18n.t("strategy.consolidation"), header_fmt)
    ws.write(0, 2, _i18n.t("strategy.performance"), header_fmt)
    ws.write(0, 3, _i18n.t("strategy.uniform"), header_fmt)

    row = 1
    for metric_key, c_val, p_val, u_val in _layout_metric_rows(proposals):
        ws.write(row, 0, _i18n.t(f"metrics.{metric_key}"), bold_fmt)
        ws.write(row, 1, c_val)
        ws.write(row, 2, p_val)
        ws.write(row, 3, u_val)
        row += 1

    row += 1  # blank separator

    # --- Per-strategy detail sub-tables ---
    proposal_by_name = {p.strategy_name: p for p in proposals}
    for strategy_name in ("consolidation", "performance", "uniform"):
        proposal = proposal_by_name[strategy_name]
        ws.write(row, 0, _i18n.t(f"strategy.{strategy_name}"), bold_fmt)
        row += 1

        ds_headers = [
            _i18n.t("ds.name"),
            _i18n.t("ds.raw_cap"),
            _i18n.t("ds.used"),
            _i18n.t("ds.util"),
            _i18n.t("ds.vms"),
            _i18n.t("ds.iops"),
            _i18n.t("ds.workloads"),
        ]
        ws.write_row(row, 0, ds_headers, header_fmt)
        row += 1

        for ds in proposal.datastores:
            ws.write(row, 0, safe_excel_cell(ds.name))
            ws.write(row, 1, ds.raw_capacity_mib / (1024 * 1024), number_fmt)  # TiB
            ws.write(row, 2, ds.used_capacity_mib / (1024 * 1024), number_fmt)  # TiB
            ws.write(row, 3, ds.utilization_pct, number_fmt)
            ws.write(row, 4, ds.vm_count)
            ws.write(row, 5, ds.total_iops, number_fmt)
            ws.write(row, 6, safe_excel_cell(", ".join(sorted(ds.workload_types))))
            row += 1

            # VM detail rows (indented)
            for vm in ds.assigned_vms:
                ws.write(row, 0, safe_excel_cell(vm.vm_name), indent_fmt)
                ws.write(row, 1, vm.provisioned_mib / (1024 * 1024), indent_num_fmt)  # TiB
                ws.write(row, 2, vm.required_mib / (1024 * 1024), indent_num_fmt)  # TiB
                ws.write(row, 3, None)
                ws.write(row, 4, None)
                ws.write(row, 5, None)
                ws.write(row, 6, safe_excel_cell(vm.workload_category), indent_fmt)
                row += 1

        row += 1  # blank separator between strategies

    ws.freeze_panes(1, 0)
    ws.autofit()


def _write_findings_sheet(
    wb: xlsxwriter.Workbook,
    health_result: HealthCheckResult | None,
    header_fmt: Format,
    alt_fmt: Format,
) -> None:
    """Write the Findings sheet with one row per HealthFinding.

    Skipped entirely if health_result is None or has no findings.
    """
    if health_result is None or not health_result.has_data or not health_result.findings:
        return

    from store_predict.pipeline.health_checks import Severity

    ws = wb.add_worksheet(_i18n.t("excel.sheet_findings"))

    headers = [
        _i18n.t("excel.col_finding"),
        _i18n.t("excel.col_severity"),
        _i18n.t("excel.col_category"),
        _i18n.t("excel.col_affected_vms"),
        _i18n.t("excel.col_detail"),
        _i18n.t("excel.col_cluster"),
    ]
    ws.write_row(0, 0, headers, header_fmt)

    # Severity order for sorting
    _sev_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    sorted_findings = sorted(
        health_result.findings,
        key=lambda f: (_sev_order.get(f.severity, 3), f.check_id),
    )

    # Category mapping from check_id prefix — reuse pdf.findings_category_* keys
    _cat_map = {
        "data_quality": "pdf.findings_category_data_quality",
        "sizing_risk": "pdf.findings_category_sizing_risk",
        "best_practice": "pdf.findings_category_best_practice",
    }

    # Severity label mapping
    _sev_label = {
        Severity.CRITICAL: "pdf.findings_severity_critical",
        Severity.WARNING: "pdf.findings_severity_warning",
        Severity.INFO: "pdf.findings_severity_info",
    }

    for body_idx, finding in enumerate(sorted_findings):
        row = body_idx + 1
        is_even = body_idx % 2 == 0
        str_fmt = alt_fmt if is_even else None

        prefix = finding.check_id.split(".")[0] if "." in finding.check_id else finding.check_id
        cat_key = _cat_map.get(prefix, f"pdf.findings_category_{prefix}")
        try:
            cat_str = _i18n.t(cat_key)
        except Exception:
            cat_str = prefix

        sev_str = _i18n.t(_sev_label.get(finding.severity, "pdf.findings_severity_info"))
        title_str = _i18n.t(finding.title)
        detail_str = _i18n.t(
            finding.detail,
            count=finding.affected_count,
            pct=round(finding.affected_count * 100 / max(health_result.total_vms_checked, 1), 1),
        )

        ws.write(row, 0, safe_excel_cell(title_str), str_fmt)
        ws.write(row, 1, sev_str, str_fmt)
        ws.write(row, 2, cat_str, str_fmt)
        ws.write(row, 3, finding.affected_count, str_fmt)
        ws.write(row, 4, safe_excel_cell(detail_str), str_fmt)
        ws.write(row, 5, safe_excel_cell(finding.cluster or ""), str_fmt)

    ws.freeze_panes(1, 0)
    ws.autofit()
