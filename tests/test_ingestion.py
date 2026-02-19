"""Comprehensive tests for the ingestion pipeline.

Tests cover format detection, all three parsers, the orchestrator,
and column resolution. Uses real sample files per project convention (no mocks).
"""

from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import detect_format, ingest_file
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers import (
    CANONICAL_COLUMNS,
    parse_liveoptics_csv,
    parse_liveoptics_xlsx,
    parse_rvtools,
)
from store_predict.pipeline.parsers.columns import (
    REQUIRED_RVTOOLS_COLUMNS,
    RVTOOLS_ALIASES,
    resolve_columns,
)

# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


class TestDetectFormat:
    """Tests for detect_format() auto-detection logic."""

    def test_detect_rvtools_xlsx(self, rvtools_path: Path) -> None:
        assert detect_format(rvtools_path) == FileFormat.RVTOOLS

    def test_detect_liveoptics_xlsx(self, liveoptics_xlsx_path: Path) -> None:
        assert detect_format(liveoptics_xlsx_path) == FileFormat.LIVEOPTICS_XLSX

    def test_detect_liveoptics_csv(self, liveoptics_csv_path: Path) -> None:
        assert detect_format(liveoptics_csv_path) == FileFormat.LIVEOPTICS_CSV

    def test_detect_unsupported_extension(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("some content")
        with pytest.raises(IngestionError, match="Unsupported file type"):
            detect_format(txt_file)

    def test_detect_nonexistent_file(self) -> None:
        with pytest.raises(IngestionError, match="File not found"):
            detect_format(Path("/nonexistent/file.xlsx"))

    def test_detect_xlsx_unknown_sheets(self, tmp_path: Path) -> None:
        xlsx_file = tmp_path / "unknown.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "RandomSheet"
        wb.save(xlsx_file)
        wb.close()
        with pytest.raises(IngestionError, match=r"vInfo.*VMs"):
            detect_format(xlsx_file)


# ---------------------------------------------------------------------------
# RVTools parser
# ---------------------------------------------------------------------------


class TestParseRvtools:
    """Tests for parse_rvtools() against real sample data."""

    def test_rvtools_column_count(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert len(df.columns) == len(CANONICAL_COLUMNS)

    def test_rvtools_row_count(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert len(df) == 20

    def test_rvtools_canonical_columns(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_rvtools_template_detection(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert df["is_template"].dtype == bool
        # At least some non-template VMs
        assert (~df["is_template"]).any()

    def test_rvtools_source_format(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert (df["source_format"] == "rvtools").all()

    def test_rvtools_numeric_types(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        # pd.to_numeric may return int64 or float64 depending on whether NaN exists
        assert df["provisioned_mib"].dtype in ("float64", "int64")
        assert df["in_use_mib"].dtype in ("float64", "int64")

    def test_rvtools_no_nan_in_names(self, rvtools_path: Path) -> None:
        df = parse_rvtools(rvtools_path)
        assert df["vm_name"].isna().sum() == 0


# ---------------------------------------------------------------------------
# LiveOptics xlsx parser
# ---------------------------------------------------------------------------


class TestParseLiveopticsXlsx:
    """Tests for parse_liveoptics_xlsx() against real sample data."""

    def test_liveoptics_xlsx_row_count(self, liveoptics_xlsx_path: Path) -> None:
        df = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert len(df) == 610

    def test_liveoptics_xlsx_canonical_columns(self, liveoptics_xlsx_path: Path) -> None:
        df = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_liveoptics_xlsx_source_format(self, liveoptics_xlsx_path: Path) -> None:
        df = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert (df["source_format"] == "liveoptics_xlsx").all()

    def test_liveoptics_xlsx_schema_matches_rvtools(self, rvtools_path: Path, liveoptics_xlsx_path: Path) -> None:
        rv = parse_rvtools(rvtools_path)
        lo = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert list(rv.columns) == list(lo.columns)


# ---------------------------------------------------------------------------
# LiveOptics CSV parser
# ---------------------------------------------------------------------------


class TestParseLiveopticsCsv:
    """Tests for parse_liveoptics_csv() against CSV fixture."""

    def test_liveoptics_csv_parses(self, liveoptics_csv_path: Path) -> None:
        df = parse_liveoptics_csv(liveoptics_csv_path)
        assert len(df) > 0

    def test_liveoptics_csv_canonical_columns(self, liveoptics_csv_path: Path) -> None:
        df = parse_liveoptics_csv(liveoptics_csv_path)
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_liveoptics_csv_source_format(self, liveoptics_csv_path: Path) -> None:
        df = parse_liveoptics_csv(liveoptics_csv_path)
        assert (df["source_format"] == "liveoptics_csv").all()

    def test_liveoptics_csv_schema_matches_rvtools(self, rvtools_path: Path, liveoptics_csv_path: Path) -> None:
        rv = parse_rvtools(rvtools_path)
        lo = parse_liveoptics_csv(liveoptics_csv_path)
        assert list(rv.columns) == list(lo.columns)


# ---------------------------------------------------------------------------
# Orchestrator (ingest_file)
# ---------------------------------------------------------------------------


class TestIngestFile:
    """Tests for the ingest_file() orchestrator."""

    def test_ingest_rvtools_filters_templates(self, rvtools_path: Path) -> None:
        raw = parse_rvtools(rvtools_path)
        ingested = ingest_file(rvtools_path)
        # ingest_file filters templates, so should have fewer or equal rows
        assert len(ingested) <= len(raw)
        # If there are templates in raw, ingested should have fewer rows
        if raw["is_template"].any():
            assert len(ingested) < len(raw)

    def test_ingest_liveoptics_xlsx(self, liveoptics_xlsx_path: Path) -> None:
        df = ingest_file(liveoptics_xlsx_path)
        assert len(df) > 0
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_ingest_liveoptics_csv(self, liveoptics_csv_path: Path) -> None:
        df = ingest_file(liveoptics_csv_path)
        assert len(df) > 0
        assert list(df.columns) == CANONICAL_COLUMNS

    def test_ingest_all_formats_same_schema(
        self, rvtools_path: Path, liveoptics_xlsx_path: Path, liveoptics_csv_path: Path
    ) -> None:
        rv = ingest_file(rvtools_path)
        lo_xlsx = ingest_file(liveoptics_xlsx_path)
        lo_csv = ingest_file(liveoptics_csv_path)
        assert list(rv.columns) == list(lo_xlsx.columns) == list(lo_csv.columns)

    def test_ingest_no_templates_in_result(
        self, rvtools_path: Path, liveoptics_xlsx_path: Path, liveoptics_csv_path: Path
    ) -> None:
        for path in [rvtools_path, liveoptics_xlsx_path, liveoptics_csv_path]:
            df = ingest_file(path)
            assert not df["is_template"].any(), f"Templates found in {path.name}"


# ---------------------------------------------------------------------------
# Column resolution
# ---------------------------------------------------------------------------


class TestColumnResolution:
    """Tests for resolve_columns() utility."""

    def test_resolve_rvtools_aliases(self) -> None:
        df = pd.DataFrame(
            {
                "VM": ["vm1"],
                "Powerstate": ["poweredOn"],
                "Template": [False],
                "OS according to the VMware Tools": ["Windows"],
                "Provisioned MiB": [1024.0],
                "In Use MiB": [512.0],
                "Datacenter": ["DC1"],
                "Cluster": ["CL1"],
            }
        )
        result = resolve_columns(df, RVTOOLS_ALIASES, REQUIRED_RVTOOLS_COLUMNS)
        assert result["vm_name"] == "VM"
        assert result["os_name"] == "OS according to the VMware Tools"
        assert result["provisioned_mib"] == "Provisioned MiB"

    def test_resolve_missing_required_column(self) -> None:
        df = pd.DataFrame({"SomeColumn": [1]})
        with pytest.raises(IngestionError, match="Missing required columns"):
            resolve_columns(df, RVTOOLS_ALIASES, REQUIRED_RVTOOLS_COLUMNS)

    def test_resolve_strips_whitespace(self) -> None:
        df = pd.DataFrame(
            {
                "VM ": ["vm1"],
                "OS according to the VMware Tools ": ["Windows"],
                "Provisioned MiB ": [1024.0],
                "In Use MiB ": [512.0],
            }
        )
        result = resolve_columns(df, RVTOOLS_ALIASES, REQUIRED_RVTOOLS_COLUMNS)
        assert result["vm_name"] == "VM"
        assert result["provisioned_mib"] == "Provisioned MiB"
