"""Tests for the Excel report generator service."""

from __future__ import annotations

import io
import zipfile

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services.excel_report import generate_report_xlsx


def _make_summary(
    categories: list[tuple[str, int, float, float]] | None = None,
) -> CalculationSummary:
    """Build a CalculationSummary from simple parameters.

    Each tuple in *categories* is ``(name, vm_count, provisioned_mib, drr)``.
    """
    if categories is None:
        categories = []

    vm_calcs: list[VMCalculation] = []
    groups: list[WorkloadGroupResult] = []

    for cat_name, count, prov_mib, drr in categories:
        in_use = prov_mib * 0.6  # assume 60% utilisation
        req = prov_mib / max(drr, 0.1)
        for i in range(count):
            vm_calcs.append(
                VMCalculation(
                    vm_name=f"{cat_name}-VM{i + 1}",
                    workload_category=cat_name,
                    provisioned_mib=prov_mib / count,
                    in_use_mib=in_use / count,
                    drr=drr,
                    required_mib=req / count,
                )
            )
        groups.append(
            WorkloadGroupResult(
                category=cat_name,
                vm_count=count,
                total_provisioned_mib=prov_mib,
                total_in_use_mib=in_use,
                avg_drr=drr,
                total_required_mib=req,
            )
        )

    total_prov = sum(g.total_provisioned_mib for g in groups)
    total_in_use = sum(g.total_in_use_mib for g in groups)
    total_req = sum(g.total_required_mib for g in groups)
    weighted_drr = total_prov / total_req if total_req > 0 else 0.0

    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=len(vm_calcs),
        total_provisioned_mib=total_prov,
        total_in_use_mib=total_in_use,
        total_required_mib=total_req,
        weighted_avg_drr=weighted_drr,
    )


def _make_perf_summary() -> CalculationSummary:
    """Build a CalculationSummary with performance data (has_performance_data=True)."""
    vm_calcs = [
        VMCalculation(
            vm_name="SQL-VM1",
            workload_category="Database/Microsoft SQL",
            provisioned_mib=20480.0,
            in_use_mib=12288.0,
            drr=5.0,
            required_mib=4096.0,
            peak_iops=5000.0,
            avg_iops=2500.0,
            peak_throughput_mbs=250.0,
            iops_8k_equivalent=2812.5,
        ),
        VMCalculation(
            vm_name="SQL-VM2",
            workload_category="Database/Microsoft SQL",
            provisioned_mib=10240.0,
            in_use_mib=6144.0,
            drr=5.0,
            required_mib=2048.0,
            peak_iops=3000.0,
            avg_iops=1500.0,
            peak_throughput_mbs=150.0,
            iops_8k_equivalent=1687.5,
        ),
    ]
    groups = [
        WorkloadGroupResult(
            category="Database/Microsoft SQL",
            vm_count=2,
            total_provisioned_mib=30720.0,
            total_in_use_mib=18432.0,
            avg_drr=5.0,
            total_required_mib=6144.0,
        )
    ]
    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=2,
        total_provisioned_mib=30720.0,
        total_in_use_mib=18432.0,
        total_required_mib=6144.0,
        weighted_avg_drr=5.0,
        avg_vm_size_mib=15360.0,
        avg_vm_cpus=4.0,
        avg_vm_memory_mib=8192.0,
        total_cpus=8,
        total_memory_mib=16384.0,
        largest_vm_name="SQL-VM1",
        largest_vm_provisioned_mib=20480.0,
        total_avg_iops=4000.0,
        max_vm_peak_iops=5000.0,
        max_vm_peak_iops_name="SQL-VM1",
        peak_throughput_mbs=250.0,
        total_iops_8k_equivalent=4500.0,
        has_performance_data=True,
    )


# ---------------------------------------------------------------------------
# Excel bytes generation tests
# ---------------------------------------------------------------------------
class TestExcelGeneratesBytes:
    def test_returns_valid_xlsx_magic(self) -> None:
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        result = generate_report_xlsx(summary, "Test")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b"PK\x03\x04"

    def test_empty_summary_returns_bytes(self) -> None:
        summary = _make_summary()
        result = generate_report_xlsx(summary, "Empty Project")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"

    def test_many_groups_returns_bytes(self) -> None:
        cats = [(f"Category-{i}", 2, 5120.0, 3.0 + i * 0.1) for i in range(15)]
        summary = _make_summary(cats)
        result = generate_report_xlsx(summary, "Large Project")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b"PK\x03\x04"


# ---------------------------------------------------------------------------
# Locale tests
# ---------------------------------------------------------------------------
class TestExcelLocale:
    def test_en_and_fr_differ(self) -> None:
        summary = _make_summary([("Database/Microsoft SQL", 2, 20480.0, 5.0)])
        en_bytes = generate_report_xlsx(summary, "X", locale="en")
        fr_bytes = generate_report_xlsx(summary, "X", locale="fr")
        assert en_bytes != fr_bytes

    def test_default_locale_is_fr(self) -> None:
        summary = _make_summary([("Virtual Machines", 1, 10240.0, 5.0)])
        result = generate_report_xlsx(summary, "X")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"


# ---------------------------------------------------------------------------
# Performance guard tests
# ---------------------------------------------------------------------------
class TestExcelPerformanceGuard:
    def test_no_performance_data_still_generates(self) -> None:
        summary = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        assert summary.has_performance_data is False
        result = generate_report_xlsx(summary, "No Perf")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"

    def test_with_performance_data_generates(self) -> None:
        summary = _make_perf_summary()
        assert summary.has_performance_data is True
        result = generate_report_xlsx(summary, "With Perf")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"


# ---------------------------------------------------------------------------
# Sheet count / structure tests
# ---------------------------------------------------------------------------
class TestExcelSheetCount:
    def test_workbook_has_four_sheets(self) -> None:
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        xlsx_bytes = generate_report_xlsx(summary, "Sheet Count Test")
        zf = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
        names = zf.namelist()
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        assert "xl/worksheets/sheet3.xml" in names
        assert "xl/worksheets/sheet4.xml" in names


# ---------------------------------------------------------------------------
# Layout sheet tests
# ---------------------------------------------------------------------------
class TestExcelLayoutSheet:
    def test_layout_sheet_exists(self) -> None:
        """Workbook with VM data should have a fourth sheet (layout)."""
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        xlsx_bytes = generate_report_xlsx(summary, "Layout Sheet Test")
        zf = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
        assert "xl/worksheets/sheet4.xml" in zf.namelist()

    def test_layout_sheet_locale_differs(self) -> None:
        """Layout sheet content should differ between EN and FR locales."""
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        en_bytes = generate_report_xlsx(summary, "X", locale="en")
        fr_bytes = generate_report_xlsx(summary, "X", locale="fr")
        assert en_bytes != fr_bytes

    def test_layout_sheet_skipped_when_empty(self) -> None:
        """Empty summary (0 VMs) should produce a 3-sheet workbook (layout sheet skipped)."""
        summary = _make_summary()  # total_vms == 0
        xlsx_bytes = generate_report_xlsx(summary, "Empty Test")
        zf = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
        names = zf.namelist()
        assert "xl/worksheets/sheet3.xml" in names
        assert "xl/worksheets/sheet4.xml" not in names
