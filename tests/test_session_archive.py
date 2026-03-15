"""Tests for session_archive module — round-trip and error cases."""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.session_archive import (
    SESSION_ZIP_SENTINEL,
    is_session_zip,
    restore_session_zip,
    save_session_zip,
)

# ---------------------------------------------------------------------------
# Test fixtures / shared data
# ---------------------------------------------------------------------------

SAMPLE_VM_DATA = [
    {
        "vm_name": "vm-sql-01",
        "workload_category": "Database",
        "workload_subcategory": "Microsoft SQL",
        "drr": 5.0,
        "provisioned_mib": 204800.0,
        "in_use_mib": 102400.0,
        "row_index": 0,
    },
    {
        "vm_name": "vm-web-02",
        "workload_category": "Virtual Machines",
        "workload_subcategory": "Windows Server",
        "drr": 5.0,
        "provisioned_mib": 51200.0,
        "in_use_mib": 25600.0,
        "row_index": 1,
    },
    {
        "vm_name": "vm-vdi-03",
        "workload_category": "VDI",
        "workload_subcategory": "Full Clone",
        "drr": 3.0,
        "provisioned_mib": 40960.0,
        "in_use_mib": 20480.0,
        "row_index": 2,
    },
]

SAMPLE_SESSION_DATA: dict[str, object] = {
    "vm_data": SAMPLE_VM_DATA,
    "project_name": "Test-DC-2026",
    "storage_model": "powerstore",
    "selected_datacenters": ["DC1"],
    "selected_clusters": ["Cluster-A"],
    # Layout keys
    "layout_max_ds_mib": 8192.0,
    "layout_max_vms": 20,
    "layout_iops_budget": 50000.0,
    "layout_snapshot_pct": 10.0,
    "layout_growth_pct": 25.0,
}

SAMPLE_ORIGINAL_FILE_BYTES = b"FAKE_XLSX_CONTENT_FOR_TESTING"
SAMPLE_ORIGINAL_FILENAME = "test_rvtools.xlsx"


def _make_archive() -> bytes:
    """Helper: build a session archive from SAMPLE_SESSION_DATA."""
    return save_session_zip(
        session_data=SAMPLE_SESSION_DATA,
        original_file_bytes=SAMPLE_ORIGINAL_FILE_BYTES,
        original_filename=SAMPLE_ORIGINAL_FILENAME,
    )


def _make_zip_without_session_json() -> bytes:
    """Helper: build a zip that has no session.json (simulates LiveOptics .zip)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("some_data_file.xlsx", b"FAKE_LIVEOPTICS_DATA")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests: save_session_zip
# ---------------------------------------------------------------------------


def test_save_returns_zip_bytes() -> None:
    """save_session_zip returns non-empty bytes that is_session_zip recognises."""
    result = _make_archive()
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert is_session_zip(result) is True


# ---------------------------------------------------------------------------
# Tests: restore round-trips
# ---------------------------------------------------------------------------


def test_restore_round_trip_vm_data() -> None:
    """Restored vm_data equals original vm_data list."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["vm_data"] == SAMPLE_VM_DATA


def test_restore_round_trip_project_name() -> None:
    """Restored project_name equals original."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["project_name"] == "Test-DC-2026"


def test_restore_round_trip_layout_config() -> None:
    """Restored layout keys equal originals including type coercion."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["layout_max_ds_mib"] == 8192.0
    assert restored["layout_max_vms"] == 20
    assert isinstance(restored["layout_max_ds_mib"], float)
    assert isinstance(restored["layout_max_vms"], int)


def test_restore_original_file_bytes() -> None:
    """Restored _restored_original_bytes equals the original file bytes."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["_restored_original_bytes"] == SAMPLE_ORIGINAL_FILE_BYTES


def test_restore_original_filename() -> None:
    """Restored _restored_original_filename equals the original filename."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["_restored_original_filename"] == SAMPLE_ORIGINAL_FILENAME


# ---------------------------------------------------------------------------
# Tests: is_session_zip
# ---------------------------------------------------------------------------


def test_is_session_zip_returns_false_for_non_zip() -> None:
    """is_session_zip returns False for non-zip bytes."""
    assert is_session_zip(b"not a zip") is False


def test_is_session_zip_returns_false_for_liveoptics_zip() -> None:
    """is_session_zip returns False for a valid zip with no session.json."""
    liveoptics_zip = _make_zip_without_session_json()
    assert is_session_zip(liveoptics_zip) is False


# ---------------------------------------------------------------------------
# Tests: restore_session_zip error cases
# ---------------------------------------------------------------------------


def test_restore_raises_ingestion_error_on_bad_zip() -> None:
    """restore_session_zip raises IngestionError on garbage bytes."""
    with pytest.raises(IngestionError):
        restore_session_zip(b"garbage bytes not a zip")


def test_restore_raises_ingestion_error_on_missing_session_json() -> None:
    """restore_session_zip raises IngestionError when session.json absent."""
    bad_zip = _make_zip_without_session_json()
    with pytest.raises(IngestionError):
        restore_session_zip(bad_zip)


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


def test_restore_round_trip_storage_model() -> None:
    """Restored storage_model equals original."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["storage_model"] == "powerstore"


def test_restore_round_trip_selected_datacenters() -> None:
    """Restored selected_datacenters equals original list."""
    archive = _make_archive()
    restored = restore_session_zip(archive)
    assert restored["selected_datacenters"] == ["DC1"]


def test_session_zip_sentinel_value() -> None:
    """SESSION_ZIP_SENTINEL is 'session.json' as documented."""
    assert SESSION_ZIP_SENTINEL == "session.json"


def test_restore_raises_ingestion_error_on_wrong_schema_version() -> None:
    """restore_session_zip raises IngestionError when schema_version != 1."""
    buf = io.BytesIO()
    bad_snapshot = {
        "schema_version": 99,
        "original_filename": "test.xlsx",
        "vm_data": [],
        "project_name": "",
        "storage_model": "powerstore",
        "selected_datacenters": [],
        "selected_clusters": [],
        "layout": {},
    }
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(SESSION_ZIP_SENTINEL, json.dumps(bad_snapshot))
    with pytest.raises(IngestionError):
        restore_session_zip(buf.getvalue())
