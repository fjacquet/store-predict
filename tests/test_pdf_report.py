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
        summary = _make_summary([
            ("Database/Microsoft SQL", 3, 30720.0, 5.0),
            ("Virtual Machines", 2, 10240.0, 5.0),
        ])
        result = generate_report_pdf(summary, "Test Project")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_pdf_with_french_chars(self) -> None:
        summary = _make_summary([
            ("Base de donnees", 2, 20480.0, 4.0),
        ])
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
