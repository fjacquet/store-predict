"""Unit tests for the i18n package: t() helper, locale management, and PDF locale."""

from __future__ import annotations

from typing import TYPE_CHECKING

from store_predict.i18n import t
from store_predict.i18n.locale import get_locale

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from store_predict.pipeline.calculation import CalculationSummary


# ---------------------------------------------------------------------------
# get_locale() — context-free safety
# ---------------------------------------------------------------------------


def test_get_locale_returns_default_outside_context() -> None:
    """get_locale() must return a valid locale code without a NiceGUI context.

    Called outside pytest-nicegui server context, app.storage.tab raises
    RuntimeError. The function must catch it and return the default locale.
    """
    locale = get_locale()
    assert locale in ("en", "fr"), f"Expected 'en' or 'fr', got {locale!r}"


# ---------------------------------------------------------------------------
# t() — translation lookup
# ---------------------------------------------------------------------------


def test_t_returns_english_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() returns the English string when locale is forced to 'en'."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    result = t("upload.title")
    assert result == "Upload Workload Data", f"Got: {result!r}"


def test_t_returns_french_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() returns the French string when locale is forced to 'fr'."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "fr")
    result = t("upload.title")
    assert result == "Téléchargement des données", f"Got: {result!r}"


def test_t_placeholder_substitution_english(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() substitutes %{count} placeholder correctly in English."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    result = t("upload.loaded_notify", count=42)
    assert "42" in result, f"Expected '42' in result, got: {result!r}"


def test_t_placeholder_substitution_french(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() substitutes %{count} placeholder correctly in French."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "fr")
    result = t("upload.loaded_notify", count=7)
    assert "7" in result, f"Expected '7' in result, got: {result!r}"


def test_t_review_label_with_name_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() correctly substitutes named %{name} placeholder in review.project_label."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    result = t("review.project_label", name="My-Project")
    assert "My-Project" in result, f"Expected project name in result, got: {result!r}"


def test_t_fallback_to_english_for_missing_fr_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """t() falls back to English when a key exists in en.yaml but not fr.yaml.

    python-i18n fallback='en' handles this automatically.
    This test verifies the fallback configuration is effective.
    Note: Both locale files should be complete, but the fallback must not crash.
    """
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "fr")
    # Use a key that definitely exists in EN — if FR is complete, returns FR;
    # if FR key missing, returns EN. Either way must not raise.
    result = t("layout.home")
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 0, "Expected non-empty string"


def test_t_layout_language_en_shows_fr(monkeypatch: pytest.MonkeyPatch) -> None:
    """When locale is 'en', layout.language shows 'FR' (the language to switch to)."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    result = t("layout.language")
    assert result == "FR", f"Expected 'FR', got {result!r}"


def test_t_layout_language_fr_shows_en(monkeypatch: pytest.MonkeyPatch) -> None:
    """When locale is 'fr', layout.language shows 'EN' (the language to switch to)."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "fr")
    result = t("layout.language")
    assert result == "EN", f"Expected 'EN', got {result!r}"


# ---------------------------------------------------------------------------
# PDF report — locale parameter
# ---------------------------------------------------------------------------


def test_pdf_report_generates_valid_bytes_fr(
    make_summary: Callable[[], CalculationSummary],
) -> None:
    """generate_report_pdf() with locale='fr' returns valid PDF bytes."""
    from store_predict.services.pdf_report import generate_report_pdf

    summary = make_summary()
    pdf_bytes = generate_report_pdf(summary, "Test-Project-FR", locale="fr")
    assert isinstance(pdf_bytes, bytes), "Expected bytes output"
    assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"
    # PDF magic bytes: all ReportLab outputs start with %PDF-
    assert pdf_bytes.startswith(b"%PDF-"), "Not a valid PDF"


def test_pdf_report_generates_valid_bytes_en(
    make_summary: Callable[[], CalculationSummary],
) -> None:
    """generate_report_pdf() with locale='en' returns valid PDF bytes."""
    from store_predict.services.pdf_report import generate_report_pdf

    summary = make_summary()
    pdf_bytes = generate_report_pdf(summary, "Test-Project-EN", locale="en")
    assert isinstance(pdf_bytes, bytes), "Expected bytes output"
    assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes.startswith(b"%PDF-"), "Not a valid PDF"


def test_pdf_report_fr_differs_from_en(
    make_summary: Callable[[], CalculationSummary],
) -> None:
    """PDF generated with locale='fr' differs from locale='en'.

    ReportLab uses CID font encoding, so text strings are not directly
    readable in raw PDF bytes. Instead, we verify the two locale outputs
    differ — confirming locale parameter actually affects the generated content.
    The CID-to-Unicode CMap embedded in the PDF encodes French characters
    (e.g., 'é' in 'Totaux', accented chars in French labels) differently
    from the ASCII-only English labels, producing distinct byte sequences.
    """
    from store_predict.services.pdf_report import generate_report_pdf

    summary = make_summary()
    pdf_fr = generate_report_pdf(summary, "Test", locale="fr")
    pdf_en = generate_report_pdf(summary, "Test", locale="en")
    # Both must be valid PDFs
    assert pdf_fr.startswith(b"%PDF-"), "FR PDF invalid"
    assert pdf_en.startswith(b"%PDF-"), "EN PDF invalid"
    # The two PDFs must differ because their label strings differ
    assert pdf_fr != pdf_en, "FR and EN PDFs are identical — locale parameter has no effect on output"


def test_pdf_report_default_locale_is_fr(
    make_summary: Callable[[], CalculationSummary],
) -> None:
    """generate_report_pdf() defaults to French when no locale is specified."""
    import inspect

    from store_predict.services.pdf_report import generate_report_pdf

    sig = inspect.signature(generate_report_pdf)
    assert sig.parameters["locale"].default == "fr", (
        f"Expected default locale 'fr', got {sig.parameters['locale'].default!r}"
    )
    # Also verify the default call produces valid PDF bytes
    summary = make_summary()
    pdf_bytes = generate_report_pdf(summary, "Test-Default")
    assert pdf_bytes.startswith(b"%PDF-"), "Not a valid PDF"
