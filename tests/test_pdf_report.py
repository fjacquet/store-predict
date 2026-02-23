"""Tests for the PDF report generator service."""

from __future__ import annotations

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services.pdf_report import (
    format_storage,
    generate_report_pdf,
    sanitize_filename,
)


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
        in_use = prov_mib * 0.6  # assume 60 % utilisation
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


# ---------------------------------------------------------------------------
# PDF generation tests
# ---------------------------------------------------------------------------
class TestPdfGeneratesBytes:
    def test_pdf_generates_bytes(self) -> None:
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        result = generate_report_pdf(summary, "Test Project")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_pdf_with_french_chars(self) -> None:
        summary = _make_summary(
            [
                ("Base de donnees", 2, 20480.0, 4.0),
            ]
        )
        result = generate_report_pdf(summary, "Evaluation pre-vente")
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_pdf_with_empty_summary(self) -> None:
        summary = _make_summary()
        result = generate_report_pdf(summary, "Empty Project")
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_pdf_with_many_groups(self) -> None:
        cats = [(f"Category-{i}", 2, 5120.0, 3.0 + i * 0.1) for i in range(20)]
        summary = _make_summary(cats)
        result = generate_report_pdf(summary, "Large Project")
        assert isinstance(result, bytes)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------
class TestSanitizeFilename:
    def test_slash_and_spaces(self) -> None:
        assert sanitize_filename("My Project/v2") == "My_Project_v2"

    def test_spaces_only(self) -> None:
        assert sanitize_filename("projet evaluation") == "projet_evaluation"

    def test_empty_string(self) -> None:
        assert sanitize_filename("") == "report"

    def test_whitespace_only(self) -> None:
        assert sanitize_filename("   ") == "report"


class TestFormatStorage:
    def test_small_value(self) -> None:
        assert format_storage(512.0) == "0.5 GiB"

    def test_large_value_with_tib(self) -> None:
        assert format_storage(1048576.0) == "1024.0 GiB (1.0 TiB)"

    def test_zero(self) -> None:
        assert format_storage(0.0) == "0.0 GiB"

    def test_just_below_tib_threshold(self) -> None:
        # 1023 GiB = 1023 * 1024 MiB
        assert format_storage(1023.0 * 1024) == "1023.0 GiB"


# ---------------------------------------------------------------------------
# Layout page tests
# ---------------------------------------------------------------------------
class TestPdfLayoutPage:
    def test_layout_page_locale_differs(self) -> None:
        """PDF with layout page should differ between EN and FR locales."""
        summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        en_bytes = generate_report_pdf(summary, "Layout Test", locale="en")
        fr_bytes = generate_report_pdf(summary, "Layout Test", locale="fr")
        assert en_bytes != fr_bytes

    def test_layout_page_skipped_when_empty(self) -> None:
        """PDF with empty summary should still be valid, no layout page rendered."""
        summary = _make_summary()  # total_vms == 0
        result = generate_report_pdf(summary, "Empty Project")
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        assert len(result) > 0

    def test_layout_page_present_with_data(self) -> None:
        """PDF with VM data should produce a larger file than empty (layout page included)."""
        empty_summary = _make_summary()
        full_summary = _make_summary(
            [
                ("Database/Microsoft SQL", 3, 30720.0, 5.0),
                ("Virtual Machines", 2, 10240.0, 5.0),
            ]
        )
        empty_bytes = generate_report_pdf(empty_summary, "Empty")
        full_bytes = generate_report_pdf(full_summary, "Full")
        # Full report has more pages (including layout page), so it should be larger
        assert len(full_bytes) > len(empty_bytes)


# ---------------------------------------------------------------------------
# PDF findings pages tests
# ---------------------------------------------------------------------------
from store_predict.pipeline.health_checks import HealthCheckResult, HealthFinding, Severity  # noqa: E402


class TestPdfFindingsPages:
    """Tests for health findings sections in the PDF report."""

    def _make_health_result(self) -> HealthCheckResult:
        findings = (
            HealthFinding(
                check_id="data_quality.missing_os",
                severity=Severity.WARNING,
                title="health.missing_os.title",
                detail="health.missing_os.detail",
                affected_count=5,
                affected_vms=("vm1",),
            ),
            HealthFinding(
                check_id="best_practice.tools_not_installed",
                severity=Severity.CRITICAL,
                title="health.tools_not_installed.title",
                detail="health.tools_not_installed.detail",
                affected_count=2,
                affected_vms=("vm2",),
            ),
        )
        return HealthCheckResult(findings=findings, total_vms_checked=10, has_data=True)

    def test_pdf_with_findings_larger_than_without(self) -> None:
        summary = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        health_result = self._make_health_result()
        pdf_without = generate_report_pdf(summary, "Test")
        pdf_with = generate_report_pdf(summary, "Test", health_result=health_result)
        # PDF with findings is larger (extra table on page 1 + appendix page)
        assert len(pdf_with) > len(pdf_without)

    def test_pdf_with_none_health_result_same_size(self) -> None:
        """PDF with health_result=None should be the same size as PDF without the parameter.

        Note: ReportLab PDFs are not byte-for-byte reproducible across calls (internal
        IDs vary), so we compare file sizes which are stable for equivalent content.
        """
        summary = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        pdf_no_param = generate_report_pdf(summary, "Test")
        pdf_none_param = generate_report_pdf(summary, "Test", health_result=None)
        # Allow 1% tolerance for any minor non-deterministic differences
        assert abs(len(pdf_no_param) - len(pdf_none_param)) < len(pdf_no_param) * 0.01

    def test_pdf_with_empty_findings_same_size(self) -> None:
        """PDF with empty findings should be the same size as PDF without health_result.

        Note: ReportLab PDFs are not byte-for-byte reproducible across calls (internal
        IDs vary), so we compare file sizes which are stable for equivalent content.
        """
        summary = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        empty_health = HealthCheckResult(findings=(), total_vms_checked=10, has_data=True)
        pdf_no_param = generate_report_pdf(summary, "Test")
        pdf_empty = generate_report_pdf(summary, "Test", health_result=empty_health)
        # Allow 1% tolerance for any minor non-deterministic differences
        assert abs(len(pdf_no_param) - len(pdf_empty)) < len(pdf_no_param) * 0.01
