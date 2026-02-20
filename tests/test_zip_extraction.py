"""Tests for zip_extraction module.

All tests use real zipfile objects built in-memory — no mocks.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.zip_extraction import (
    _LIVEOPTICS_PATTERN,
    _MAX_UNCOMPRESSED_BYTES,
    extract_liveoptics_from_zip,
)


def _make_zip(member_name: str, member_bytes: bytes) -> bytes:
    """Return bytes of a ZIP archive containing one member."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, member_bytes)
    return buf.getvalue()


VALID_NAME = "LiveOptics_12345_VMWARE_01_02_2025.xlsx"
FAKE_XLSX = b"PK\x03\x04" + b"\x00" * 20  # minimal xlsx-like bytes


def test_happy_path_returns_xlsx_bytes():
    """ZIP with matching member returns its bytes and filename."""
    zip_bytes = _make_zip(VALID_NAME, FAKE_XLSX)
    result_bytes, result_name = extract_liveoptics_from_zip(zip_bytes)
    assert result_bytes == FAKE_XLSX
    assert result_name == VALID_NAME


def test_pattern_matches_valid_name():
    assert _LIVEOPTICS_PATTERN.search(VALID_NAME) is not None


def test_pattern_rejects_unrelated_name():
    assert _LIVEOPTICS_PATTERN.search("VMs_export.xlsx") is None


def test_no_matching_member_raises():
    zip_bytes = _make_zip("random_export.xlsx", FAKE_XLSX)
    with pytest.raises(IngestionError, match="No LiveOptics xlsx file found"):
        extract_liveoptics_from_zip(zip_bytes)


def test_invalid_zip_bytes_raises():
    with pytest.raises(IngestionError, match="not a valid ZIP archive"):
        extract_liveoptics_from_zip(b"this is not a zip file at all")


def test_multiple_members_takes_first():
    """When multiple matches exist, returns the first match."""
    name_a = "LiveOptics_001_VMWARE_01_01_2025.xlsx"
    name_b = "LiveOptics_002_VMWARE_02_02_2025.xlsx"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name_a, b"data_a")
        zf.writestr(name_b, b"data_b")
    _, returned_name = extract_liveoptics_from_zip(buf.getvalue())
    assert returned_name == name_a


def test_zip_bomb_guard_raises():
    """ZIP whose total uncompressed size exceeds limit is rejected."""
    # Build a zip where the central directory reports a huge file_size.
    # We create a real large-ish payload to trigger the guard.
    big_payload = b"A" * (_MAX_UNCOMPRESSED_BYTES + 1)
    zip_bytes = _make_zip(VALID_NAME, big_payload)
    with pytest.raises(IngestionError, match="exceeds the"):
        extract_liveoptics_from_zip(zip_bytes)
