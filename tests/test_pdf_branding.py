"""Tests for PDF logo preprocessing, validation, and branding integration."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from PIL import Image as PilImage

from store_predict.pipeline.errors import IngestionError
from store_predict.services.pdf_report import (
    _PNG_MAGIC,
    _preprocess_logo,
    generate_report_pdf,
    validate_logo,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from store_predict.pipeline.calculation import CalculationSummary


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def _make_png_bytes(mode: str = "RGBA", size: tuple[int, int] = (100, 50)) -> bytes:
    """Create a minimal PNG image in the given PIL mode and return raw bytes."""
    if "A" in mode:
        color: tuple[int, ...] = (255, 0, 0, 128)
    else:
        color = (255, 0, 0)
    img = PilImage.new(mode, size, color=color)
    if mode == "P":
        img = img.convert("P")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes(size: tuple[int, int] = (100, 50)) -> bytes:
    """Create a minimal JPEG image and return raw bytes."""
    img = PilImage.new("RGB", size, color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# TestPreprocessLogo
# ---------------------------------------------------------------------------
class TestPreprocessLogo:
    def test_rgba_passthrough(self) -> None:
        """RGBA PNG input stays a valid PNG with PNG magic bytes."""
        raw = _make_png_bytes(mode="RGBA")
        result = _preprocess_logo(raw)
        assert isinstance(result, bytes)
        assert result.startswith(_PNG_MAGIC), "Output must start with PNG magic bytes"

    def test_palette_mode_converted(self) -> None:
        """Palette-mode (P) PNG → RGBA PNG; no black background risk."""
        raw = _make_png_bytes(mode="P")
        result = _preprocess_logo(raw)
        out_img = PilImage.open(BytesIO(result))
        assert out_img.mode == "RGBA", f"Expected RGBA, got {out_img.mode}"

    def test_rgb_passthrough(self) -> None:
        """RGB PNG input stays as valid PNG output (RGB is safe for ReportLab)."""
        raw = _make_png_bytes(mode="RGB")
        result = _preprocess_logo(raw)
        assert result.startswith(_PNG_MAGIC), "Output must be a valid PNG"
        out_img = PilImage.open(BytesIO(result))
        assert out_img.mode in ("RGB", "RGBA"), f"Unexpected mode: {out_img.mode}"

    def test_jpeg_to_png(self) -> None:
        """JPEG input is re-encoded as PNG (starts with PNG magic bytes)."""
        raw = _make_jpeg_bytes()
        result = _preprocess_logo(raw)
        assert result.startswith(_PNG_MAGIC), "JPEG input must be re-encoded as PNG"


# ---------------------------------------------------------------------------
# TestValidateLogo
# ---------------------------------------------------------------------------
class TestValidateLogo:
    def test_valid_png_accepted(self) -> None:
        """Valid RGBA PNG with .png extension passes without raising."""
        raw = _make_png_bytes(mode="RGBA")
        validate_logo(raw, "logo.png")  # should not raise

    def test_valid_jpeg_accepted(self) -> None:
        """Valid JPEG with .jpg extension passes without raising."""
        raw = _make_jpeg_bytes()
        validate_logo(raw, "logo.jpg")  # should not raise

    def test_invalid_extension_rejected(self) -> None:
        """Valid PNG bytes with .gif extension raise IngestionError about PNG or JPEG."""
        raw = _make_png_bytes()
        with pytest.raises(IngestionError, match="PNG or JPEG"):
            validate_logo(raw, "logo.gif")

    def test_oversized_file_rejected(self) -> None:
        """File exceeding 200 KB raises IngestionError about size."""
        oversized = b"X" * (201 * 1024)
        with pytest.raises(IngestionError, match="too large"):
            validate_logo(oversized, "logo.png")

    def test_wrong_magic_bytes_rejected(self) -> None:
        """PNG file with wrong magic bytes raises IngestionError."""
        fake_png = b"FAKEPNG\r\n\x1a\n" + b"\x00" * 100
        with pytest.raises(IngestionError):
            validate_logo(fake_png, "logo.png")

    def test_oversized_dimensions_rejected(self) -> None:
        """PNG with dimensions > 2000px raises IngestionError with dimension info."""
        raw = _make_png_bytes(mode="RGBA", size=(2001, 100))
        with pytest.raises(IngestionError, match=r"2001"):
            validate_logo(raw, "logo.png")


# ---------------------------------------------------------------------------
# TestGenerateReportPdfWithLogos
# ---------------------------------------------------------------------------
class TestGenerateReportPdfWithLogos:
    def test_pdf_with_dell_logo_only(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """PDF with Dell logo only generates valid PDF bytes."""
        summary = make_summary()
        result = generate_report_pdf(summary, "Test", dell_logo_bytes=_make_png_bytes())
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_with_company_logo_only(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """PDF with company logo only generates valid PDF bytes."""
        summary = make_summary()
        result = generate_report_pdf(summary, "Test", company_logo_bytes=_make_png_bytes())
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_with_both_logos(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """PDF with both logos generates valid PDF bytes of reasonable size."""
        summary = make_summary()
        result = generate_report_pdf(
            summary,
            "Test",
            dell_logo_bytes=_make_png_bytes(),
            company_logo_bytes=_make_png_bytes(),
        )
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"
        assert len(result) > 5000, f"PDF too small ({len(result)} bytes)"

    def test_pdf_with_palette_logo_no_crash(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """Palette-mode (P) PNG as company logo does not crash — preprocess handles it."""
        summary = make_summary()
        palette_png = _make_png_bytes(mode="P")
        result = generate_report_pdf(summary, "Test", company_logo_bytes=palette_png)
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_with_no_logos_unchanged(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """PDF with no logos generates valid PDF (regression guard)."""
        summary = make_summary()
        result = generate_report_pdf(summary, "Test", dell_logo_bytes=None, company_logo_bytes=None)
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"

    def test_pdf_stays_one_page(self, make_summary: Callable[[], CalculationSummary]) -> None:
        """PDF with both logos stays within single-page size bounds."""
        summary = make_summary()
        result = generate_report_pdf(
            summary,
            "Test",
            dell_logo_bytes=_make_png_bytes(),
            company_logo_bytes=_make_png_bytes(),
        )
        assert result[:5] == b"%PDF-", "Output must be a valid PDF"
        # Single-page summary PDF should be well under 500 KB
        assert len(result) < 500_000, f"PDF unexpectedly large ({len(result)} bytes)"
        # Verify basic PDF structure
        assert b"endobj" in result
