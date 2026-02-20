"""Tests for logo UI wiring: validation integration, tab storage pattern, and PDF with logo."""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from PIL import Image as PilImage

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.services.pdf_report import generate_report_pdf, validate_logo


# ---------------------------------------------------------------------------
# Test image helpers
# ---------------------------------------------------------------------------
def _make_rgba_png_bytes(size: tuple[int, int] = (80, 40)) -> bytes:
    """Create a minimal RGBA PNG image and return raw bytes."""
    img = PilImage.new("RGBA", size, (0, 94, 173, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes(size: tuple[int, int] = (80, 40)) -> bytes:
    """Create a minimal JPEG image and return raw bytes."""
    img = PilImage.new("RGB", size, (0, 94, 173))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_summary() -> CalculationSummary:
    """Build a minimal 1-group CalculationSummary for PDF generation tests."""
    vm = VMCalculation(
        vm_name="test-vm",
        workload_category="Virtual Machines",
        provisioned_mib=1024.0,
        in_use_mib=512.0,
        drr=5.0,
        required_mib=204.8,
    )
    grp = WorkloadGroupResult(
        category="Virtual Machines",
        vm_count=1,
        total_provisioned_mib=1024.0,
        total_in_use_mib=512.0,
        avg_drr=5.0,
        total_required_mib=204.8,
    )
    return CalculationSummary(
        vm_calculations=[vm],
        workload_groups=[grp],
        total_vms=1,
        total_provisioned_mib=1024.0,
        total_in_use_mib=512.0,
        total_required_mib=204.8,
        weighted_avg_drr=5.0,
        avg_vm_size_mib=1024.0,
        avg_vm_cpus=2.0,
        avg_vm_memory_mib=2048.0,
        total_cpus=2,
        total_memory_mib=2048.0,
        largest_vm_name="test-vm",
        largest_vm_provisioned_mib=1024.0,
        has_performance_data=False,
    )


# ---------------------------------------------------------------------------
# TestLogoValidationWiring
# ---------------------------------------------------------------------------
class TestLogoValidationWiring:
    def test_validate_logo_accepts_png(self) -> None:
        """Valid RGBA PNG accepted without exception."""
        content = _make_rgba_png_bytes()
        validate_logo(content, "company.png")  # should not raise

    def test_validate_logo_accepts_jpeg(self) -> None:
        """Valid JPEG accepted without exception."""
        content = _make_jpeg_bytes()
        validate_logo(content, "company.jpg")  # should not raise

    def test_validate_logo_rejects_gif_extension(self) -> None:
        """Valid PNG bytes with .gif extension raise IngestionError."""
        content = _make_rgba_png_bytes()
        with pytest.raises(IngestionError):
            validate_logo(content, "logo.gif")

    def test_validate_logo_rejects_oversized(self) -> None:
        """File exceeding 200 KB raises IngestionError mentioning 200."""
        oversized = b"X" * (201 * 1024)
        with pytest.raises(IngestionError, match="200"):
            validate_logo(oversized, "logo.png")


# ---------------------------------------------------------------------------
# TestBase64RoundTrip
# ---------------------------------------------------------------------------
class TestBase64RoundTrip:
    def test_encode_decode_roundtrip_png(self) -> None:
        """PNG bytes survive base64 encode → decode roundtrip unchanged."""
        original = _make_rgba_png_bytes()
        b64_str = base64.b64encode(original).decode("ascii")
        decoded = base64.b64decode(b64_str)
        assert decoded == original

    def test_encode_decode_roundtrip_jpeg(self) -> None:
        """JPEG bytes survive base64 encode → decode roundtrip unchanged."""
        original = _make_jpeg_bytes()
        b64_str = base64.b64encode(original).decode("ascii")
        decoded = base64.b64decode(b64_str)
        assert decoded == original

    def test_empty_b64_returns_none_bytes(self) -> None:
        """Empty string input using the tab storage decode guard returns None."""
        company_logo_b64 = ""
        company_logo_bytes: bytes | None = base64.b64decode(company_logo_b64) if company_logo_b64 else None
        assert company_logo_bytes is None


# ---------------------------------------------------------------------------
# TestPdfDownloadWithCompanyLogo
# ---------------------------------------------------------------------------
class TestPdfDownloadWithCompanyLogo:
    def test_pdf_generated_with_company_logo(self) -> None:
        """PDF with RGBA PNG company logo starts with PDF magic bytes."""
        summary = _make_summary()
        result = generate_report_pdf(summary, "Logo Test", company_logo_bytes=_make_rgba_png_bytes())
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_generated_with_jpeg_company_logo(self) -> None:
        """PDF with JPEG company logo starts with PDF magic bytes."""
        summary = _make_summary()
        result = generate_report_pdf(summary, "JPEG Logo Test", company_logo_bytes=_make_jpeg_bytes())
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_generated_without_company_logo(self) -> None:
        """PDF without company logo still generates valid PDF (regression guard)."""
        summary = _make_summary()
        result = generate_report_pdf(summary, "No Logo Test", company_logo_bytes=None)
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_bytes_differ_with_and_without_logo(self) -> None:
        """PDF with company logo is larger than PDF without — proves logo is embedded."""
        summary_with = _make_summary()
        summary_without = _make_summary()
        with_logo = generate_report_pdf(
            summary_with, "With Logo", company_logo_bytes=_make_rgba_png_bytes()
        )
        without_logo = generate_report_pdf(summary_without, "Without Logo", company_logo_bytes=None)
        assert len(with_logo) > len(without_logo), (
            f"PDF with logo ({len(with_logo)} bytes) should be larger than "
            f"PDF without logo ({len(without_logo)} bytes)"
        )
