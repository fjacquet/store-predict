"""Tests for server-side file upload validation."""

from __future__ import annotations

import io
import zipfile

import pytest

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.validation import validate_upload


def _ooxml_bytes() -> bytes:
    """Minimal OOXML archive carrying the `[Content_Types].xml` marker."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<?xml version='1.0'?><Types/>")
    return buf.getvalue()


# --- Valid files pass ---


def test_valid_xlsx_passes() -> None:
    """Valid xlsx content (ZIP with `[Content_Types].xml`) should pass validation."""
    validate_upload(_ooxml_bytes(), "workload.xlsx")


def test_valid_xlsx_uppercase_extension() -> None:
    """Extension check should be case-insensitive."""
    validate_upload(_ooxml_bytes(), "workload.XLSX")


def test_plain_zip_renamed_xlsx_rejected() -> None:
    """A plain zip without `[Content_Types].xml` must be rejected even with .xlsx name."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("payload.bin", b"not a real xlsx")
    with pytest.raises(IngestionError, match=r"valid \.xlsx file"):
        validate_upload(buf.getvalue(), "fake.xlsx")


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
