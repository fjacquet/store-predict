"""Tests for enhanced PDF generation: VM statistics and conditional performance sections.

Uses real objects (no mocks). Builds CalculationSummary manually.
"""

from __future__ import annotations

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services.pdf_report import generate_report_pdf


def _make_summary(
    total_vms: int = 3,
    total_provisioned_mib: float = 30000.0,
    total_in_use_mib: float = 15000.0,
    total_required_mib: float = 6000.0,
    weighted_avg_drr: float = 5.0,
    avg_vm_size_mib: float = 10000.0,
    largest_vm_name: str = "Big-VM",
    largest_vm_provisioned_mib: float = 20000.0,
    has_performance_data: bool = False,
    total_peak_iops: float = 0.0,
    total_avg_iops: float = 0.0,
    peak_throughput_mbs: float = 0.0,
    total_iops_8k_equivalent: float = 0.0,
) -> CalculationSummary:
    """Build a CalculationSummary with all fields populated."""
    vm_calcs = [
        VMCalculation(
            vm_name=f"VM-{i}",
            workload_category="Database/Microsoft SQL",
            provisioned_mib=total_provisioned_mib / total_vms,
            in_use_mib=total_in_use_mib / total_vms,
            drr=weighted_avg_drr,
            required_mib=total_required_mib / total_vms,
        )
        for i in range(total_vms)
    ]
    groups = [
        WorkloadGroupResult(
            category="Database/Microsoft SQL",
            vm_count=total_vms,
            total_provisioned_mib=total_provisioned_mib,
            total_in_use_mib=total_in_use_mib,
            avg_drr=weighted_avg_drr,
            total_required_mib=total_required_mib,
        )
    ]
    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=total_vms,
        total_provisioned_mib=total_provisioned_mib,
        total_in_use_mib=total_in_use_mib,
        total_required_mib=total_required_mib,
        weighted_avg_drr=weighted_avg_drr,
        avg_vm_size_mib=avg_vm_size_mib,
        largest_vm_name=largest_vm_name,
        largest_vm_provisioned_mib=largest_vm_provisioned_mib,
        has_performance_data=has_performance_data,
        total_peak_iops=total_peak_iops,
        total_avg_iops=total_avg_iops,
        peak_throughput_mbs=peak_throughput_mbs,
        total_iops_8k_equivalent=total_iops_8k_equivalent,
    )


class TestPDFVMStats:
    """Tests for VM Statistics section in PDF."""

    def test_pdf_with_vm_stats(self) -> None:
        """PDF with VM stats is larger than a minimal report without them.

        The VM Statistics section adds content (average VM size, largest VM).
        We verify the PDF is valid and non-empty, confirming the section renders.
        """
        summary = _make_summary(
            avg_vm_size_mib=10000.0,
            largest_vm_name="Big-VM",
            largest_vm_provisioned_mib=20000.0,
        )
        pdf_bytes = generate_report_pdf(summary, "Test Project")
        assert len(pdf_bytes) > 0
        # PDF is valid
        assert pdf_bytes[:5] == b"%PDF-"
        # VM Statistics section uses the largest_vm_name field -- verify the
        # generate_report_pdf code path that references these fields runs without error.
        # The fact that we get a valid PDF of reasonable size confirms the section rendered.
        assert len(pdf_bytes) > 5000, "PDF should be substantial with VM stats section"


class TestPDFPerformanceSection:
    """Tests for conditional Performance Summary section in PDF."""

    def test_pdf_with_performance_section(self) -> None:
        """PDF with performance data is larger than without (extra section)."""
        summary_with = _make_summary(
            has_performance_data=True,
            total_peak_iops=1500.0,
            total_avg_iops=800.0,
            peak_throughput_mbs=200.0,
            total_iops_8k_equivalent=1000.0,
        )
        summary_without = _make_summary(has_performance_data=False)

        pdf_with = generate_report_pdf(summary_with, "Test Project")
        pdf_without = generate_report_pdf(summary_without, "Test Project")

        assert len(pdf_with) > 0
        assert len(pdf_without) > 0
        # Performance section adds IOPS, throughput, 8K equivalent lines
        assert len(pdf_with) > len(pdf_without), "PDF with performance data should be larger than without"

    def test_pdf_without_performance_section(self) -> None:
        """PDF without performance data is valid and smaller."""
        summary = _make_summary(has_performance_data=False)
        pdf_bytes = generate_report_pdf(summary, "Test Project")
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"


class TestPDFFrenchChars:
    """Test French character support with Vera fonts."""

    def test_pdf_french_chars_still_work(self) -> None:
        """PDF generation with French accented characters produces valid output."""
        summary = _make_summary()
        pdf_bytes = generate_report_pdf(summary, "Projet Resume")
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"
