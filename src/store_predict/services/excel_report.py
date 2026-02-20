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

if TYPE_CHECKING:
    from xlsxwriter.format import Format

    from store_predict.pipeline.calculation import CalculationSummary

__all__ = ["generate_report_xlsx"]

_BRAND_BLUE = "#1e3a5f"
_BRAND_WHITE = "#FFFFFF"
_LIGHT_GREY = "#f0f0f0"


def generate_report_xlsx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
) -> bytes:
    """Generate a styled Excel workbook and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label, embedded as workbook title metadata.
        locale: Language for labels. Defaults to 'fr'.

    Returns:
        .xlsx document as bytes (PK ZIP format).
    """
    _i18n.set("locale", locale)

    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"title": project_name})

    header_fmt = wb.add_format(
        {
            "bold": True,
            "bg_color": _BRAND_BLUE,
            "font_color": _BRAND_WHITE,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )
    bold_fmt = wb.add_format({"bold": True})
    number_fmt = wb.add_format({"num_format": "0.00", "align": "right"})
    int_fmt = wb.add_format({"num_format": "0", "align": "right"})
    alt_fmt = wb.add_format({"bg_color": _LIGHT_GREY})
    alt_right_fmt = wb.add_format({"bg_color": _LIGHT_GREY, "num_format": "0.00", "align": "right"})

    _write_summary_sheet(wb, summary, header_fmt, bold_fmt, number_fmt, int_fmt)
    _write_breakdown_sheet(wb, summary, header_fmt, number_fmt, int_fmt, alt_fmt, alt_right_fmt)
    _write_vm_detail_sheet(wb, summary, header_fmt, number_fmt, alt_fmt, alt_right_fmt)

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
    write_metric(_i18n.t("pdf.largest_vm"), summary.largest_vm_name)

    if summary.has_performance_data:
        write_metric(_i18n.t("pdf.total_avg_iops"), summary.total_avg_iops, number_fmt)
        write_metric(
            _i18n.t("pdf.hottest_vm"),
            f"{summary.max_vm_peak_iops_name} ({summary.max_vm_peak_iops:,.0f})",
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

        ws.write(row, 0, grp.category, str_fmt)
        ws.write(row, 1, grp.vm_count, i_fmt)
        ws.write(row, 2, grp.total_provisioned_mib / 1024.0, num_fmt)
        ws.write(row, 3, grp.avg_drr, num_fmt)
        ws.write(row, 4, grp.total_required_mib / 1024.0, num_fmt)

    # Totals row
    totals_row = len(summary.workload_groups) + 1
    bold_int_fmt = wb.add_format({"bold": True, "num_format": "0", "align": "right"})
    bold_num_fmt = wb.add_format({"bold": True, "num_format": "0.00", "align": "right"})
    bold_fmt_cell = wb.add_format({"bold": True})
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

        ws.write(row, 0, vm.vm_name, str_fmt)
        ws.write(row, 1, vm.workload_category, str_fmt)
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
