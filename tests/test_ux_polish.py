"""Tests for Phase 12 UX polish: i18n keys, notify types, and structural patterns."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGES_DIR = Path("src/store_predict/ui/pages")
LOCALES_DIR = Path("src/store_predict/i18n/locales")


def _load_yaml(locale: str) -> dict:
    """Load a locale YAML and flatten to dotted keys."""
    raw = yaml.safe_load((LOCALES_DIR / f"{locale}.yaml").read_text())

    def _flatten(d: dict, prefix: str = "") -> dict:
        out: dict = {}
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
        return out

    return _flatten(raw)


def _page_source(name: str) -> str:
    return (PAGES_DIR / f"{name}.py").read_text()


# ---------------------------------------------------------------------------
# UX-01 / UX-02: i18n keys exist in both locales
# ---------------------------------------------------------------------------

REQUIRED_KEYS = [
    "error.unexpected",
    "error.logo_upload_failed",
    "upload.processing",
    "llm.error",
]


@pytest.mark.parametrize("locale", ["en", "fr"])
@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_required_i18n_key_present(locale: str, key: str) -> None:
    """All new UX-polish i18n keys must exist in both locales."""
    flat = _load_yaml(locale)
    assert key in flat, f"Missing key '{key}' in {locale}.yaml"
    assert flat[key], f"Key '{key}' in {locale}.yaml is empty"


@pytest.mark.parametrize("locale", ["en", "fr"])
def test_i18n_yaml_is_valid(locale: str) -> None:
    """Locale YAML files must parse without error."""
    content = (LOCALES_DIR / f"{locale}.yaml").read_text()
    data = yaml.safe_load(content)
    assert isinstance(data, dict)
    assert len(data) > 0


# ---------------------------------------------------------------------------
# UX-02: Raw exception strings not exposed to users
# ---------------------------------------------------------------------------


def test_upload_no_raw_exception_string() -> None:
    """upload.py must not contain raw f'Unexpected error: {exc}' pattern."""
    source = _page_source("upload")
    assert "Unexpected error:" not in source, (
        "upload.py still exposes raw exception text to user — use t('error.unexpected')"
    )


def test_report_logo_error_uses_i18n() -> None:
    """_handle_logo_upload must use t('error.logo_upload_failed') not str(exc)."""
    source = _page_source("report")
    # The logo upload except block must reference the i18n key
    assert "error.logo_upload_failed" in source, "report.py _handle_logo_upload must use t('error.logo_upload_failed')"


# ---------------------------------------------------------------------------
# UX-03: Canonical notify() types
# ---------------------------------------------------------------------------

VALID_NOTIFY_TYPES = {"positive", "negative", "warning", "info"}


def _extract_notify_types(source: str) -> list[str]:
    """Extract type= values from ui.notify() and ui.notification() calls."""
    # Match type="..." in notify calls
    return re.findall(r'ui\.noti(?:fy|fication)\([^)]*type=["\'](\w+)["\']', source)


@pytest.mark.parametrize("page", ["upload", "review", "report"])
def test_notify_types_are_canonical(page: str) -> None:
    """All ui.notify/ui.notification type values must be canonical."""
    source = _page_source(page)
    found_types = _extract_notify_types(source)
    invalid = [t for t in found_types if t not in VALID_NOTIFY_TYPES]
    assert not invalid, f"{page}.py has non-canonical notify types: {invalid}. Use: {VALID_NOTIFY_TYPES}"


# ---------------------------------------------------------------------------
# UX-04: Navigation CTAs use button (not link) for no-data states
# ---------------------------------------------------------------------------


def test_review_no_data_uses_button_not_link() -> None:
    """review.py no-data state must use ui.button for CTA, not ui.link."""
    source = _page_source("review")
    # In the no-data early return block, there should be no ui.link
    # Parse to find the no-data section (before the return)
    no_data_section = source.split("if df is None:")[1].split("return")[0] if "if df is None:" in source else ""
    assert "ui.button" in no_data_section, "review.py no-data state must use ui.button CTA"
    assert "ui.link" not in no_data_section, "review.py no-data state must not use ui.link"


def test_report_no_data_uses_button_not_link() -> None:
    """report.py no-data state must use ui.button for CTA, not ui.link."""
    source = _page_source("report")
    no_data_section = source.split("if not vm_data:")[1].split("return")[0] if "if not vm_data:" in source else ""
    assert "ui.button" in no_data_section, "report.py no-data state must use ui.button CTA"
    assert "ui.link" not in no_data_section, "report.py no-data state must not use ui.link"


# ---------------------------------------------------------------------------
# UX-01: Spinner / progress present in upload.py
# ---------------------------------------------------------------------------


def test_upload_has_spinner() -> None:
    """upload.py must use ui.spinner for visual upload feedback."""
    source = _page_source("upload")
    assert "ui.spinner" in source, "upload.py must include ui.spinner for upload feedback"


def test_upload_has_run_io_bound() -> None:
    """upload.py must wrap blocking I/O in run.io_bound."""
    source = _page_source("upload")
    assert "run.io_bound" in source, "upload.py must wrap ingest_file/classify_dataframe in run.io_bound"


def test_upload_has_persistent_llm_notification() -> None:
    """upload.py must use ui.notification (persistent) for LLM classification, not ui.notify."""
    source = _page_source("upload")
    assert "ui.notification" in source, "upload.py must use ui.notification with spinner=True for LLM classification"
