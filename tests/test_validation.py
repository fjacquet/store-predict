"""Tests for server-side file upload validation."""

from __future__ import annotations

import pytest

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.validation import validate_upload

# --- Valid files pass ---


def test_valid_xlsx_passes() -> None:
    """Valid xlsx content (ZIP magic bytes) should pass validation."""
    content = b"PK\x03\x04" + b"\x00" * 100
    validate_upload(content, "workload.xlsx")


def test_valid_xlsx_uppercase_extension() -> None:
    """Extension check should be case-insensitive."""
    content = b"PK\x03\x04" + b"\x00" * 100
    validate_upload(content, "workload.XLSX")


def test_valid_csv_passes() -> None:
    """Valid CSV content (UTF-8 text) should pass validation."""
    content = b"VM Name,OS,Provisioned MiB\nvm-01,Windows,1024\n"
    validate_upload(content, "export.csv")


def test_valid_csv_uppercase_extension() -> None:
    """Extension check should be case-insensitive for CSV."""
    content = b"VM Name,OS,Provisioned MiB\n"
    validate_upload(content, "export.CSV")


# --- Invalid extension ---


def test_exe_extension_rejected() -> None:
    """Executable file extension should be rejected."""
    with pytest.raises(IngestionError, match="Unsupported file type"):
        validate_upload(b"MZ\x90\x00", "malware.exe")


def test_txt_extension_rejected() -> None:
    """Unsupported text file extension should be rejected."""
    with pytest.raises(IngestionError, match="Unsupported file type"):
        validate_upload(b"hello world", "notes.txt")


def test_no_extension_rejected() -> None:
    """File without extension should be rejected."""
    with pytest.raises(IngestionError, match="Unsupported file type"):
        validate_upload(b"data", "noextension")


# --- Magic bytes mismatch ---


def test_xlsx_wrong_magic_bytes() -> None:
    """XLSX file with wrong magic bytes (not a ZIP) should be rejected."""
    content = b"\x00\x00\x00\x00" + b"\x00" * 100
    with pytest.raises(IngestionError, match=r"valid \.xlsx file"):
        validate_upload(content, "fake.xlsx")


def test_xlsx_too_short() -> None:
    """XLSX file shorter than 4 bytes should be rejected."""
    with pytest.raises(IngestionError, match=r"valid \.xlsx file"):
        validate_upload(b"PK", "tiny.xlsx")


# --- CSV content validation ---


def test_csv_binary_content_rejected() -> None:
    """CSV file with binary content (not valid UTF-8) should be rejected."""
    content = b"\x80\x81\x82\x83" * 100
    with pytest.raises(IngestionError, match="valid CSV file"):
        validate_upload(content, "binary.csv")
