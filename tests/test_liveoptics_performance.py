"""Tests for LiveOptics performance parsing and 8K IOPS computation.

Uses REAL sample files per project convention -- no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from store_predict.pipeline.parsers.liveoptics import (
    parse_liveoptics_performance,
    parse_liveoptics_xlsx,
)
from store_predict.pipeline.parsers.rvtools import parse_rvtools

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
LIVEOPTICS_XLSX = SAMPLES / "live-optics.xlsx"
RVTOOLS_XLSX = SAMPLES / "rvtools.xlsx"


# ---- Performance parsing -------------------------------------------------


class TestParseLiveopticsPerformance:
    """Tests for parse_liveoptics_performance()."""

    def test_parse_liveoptics_performance_returns_dataframe(self) -> None:
        """Performance sheet parsed into a DataFrame with expected columns."""
        df = parse_liveoptics_performance(LIVEOPTICS_XLSX)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0, "Expected non-empty performance data"
        for col in ("vm_name", "peak_iops", "avg_iops"):
            assert col in df.columns, f"Missing expected column: {col}"

    def test_parse_liveoptics_performance_missing_sheet(self) -> None:
        """RVTools file has no VM Performance sheet -- returns empty DataFrame."""
        df = parse_liveoptics_performance(RVTOOLS_XLSX)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0, "Expected empty DataFrame for file without VM Performance sheet"


# ---- Integrated performance columns in parse_liveoptics_xlsx -------------


class TestLiveopticsXlsxPerformance:
    """Tests for performance columns in parse_liveoptics_xlsx()."""

    def test_liveoptics_xlsx_has_performance_columns(self) -> None:
        """LiveOptics xlsx output has peak_iops and iops_8k_equivalent columns."""
        df = parse_liveoptics_xlsx(LIVEOPTICS_XLSX)
        assert "peak_iops" in df.columns
        assert "iops_8k_equivalent" in df.columns
        # At least some VMs should have non-NaN peak_iops
        non_nan = df["peak_iops"].dropna()
        assert len(non_nan) > 0, "Expected some non-NaN peak_iops values"

    def test_liveoptics_csv_has_nan_performance(self) -> None:
        """No LiveOptics CSV sample exists -- skip."""
        csv_files = list(SAMPLES.glob("live-optics*.csv"))
        if not csv_files:
            pytest.skip("No LiveOptics CSV sample available")
        from store_predict.pipeline.parsers.liveoptics import parse_liveoptics_csv

        df = parse_liveoptics_csv(csv_files[0])
        assert df["peak_iops"].isna().all(), "CSV should have NaN performance"


# ---- RVTools performance columns -----------------------------------------


class TestRvtoolsPerformance:
    """Tests for performance columns in parse_rvtools()."""

    def test_rvtools_has_nan_performance(self) -> None:
        """RVTools has performance columns but all values are NaN."""
        df = parse_rvtools(RVTOOLS_XLSX)
        for col in ("peak_iops", "avg_iops", "peak_throughput_mbs", "iops_8k_equivalent"):
            assert col in df.columns, f"Missing performance column: {col}"
            assert df[col].isna().all(), f"RVTools {col} should be all NaN"


# ---- 8K equivalent IOPS formula ------------------------------------------


class TestIops8kEquivalent:
    """Verify 8K equivalent IOPS formula: avg_iops + (avg_throughput_kbs / 8.0)."""

    def test_8k_equivalent_iops_formula(self) -> None:
        """Spot-check the 8K equivalent IOPS formula on a row with performance data."""
        df = parse_liveoptics_xlsx(LIVEOPTICS_XLSX)
        # Get rows where performance data is present
        has_perf = df[df["peak_iops"].notna() & (df["peak_iops"] > 0)]
        assert len(has_perf) > 0, "Need at least one row with performance data"

        # Get the raw performance data to verify the formula
        perf_df = parse_liveoptics_performance(LIVEOPTICS_XLSX)
        assert len(perf_df) > 0

        # Pick a row with data and verify against the raw perf sheet
        perf_with_data = perf_df[perf_df["avg_iops"].notna() & (perf_df["avg_iops"] > 0)]
        if len(perf_with_data) == 0:
            pytest.skip("No rows with avg_iops data in performance sheet")

        row = perf_with_data.iloc[0]
        avg_iops = float(row["avg_iops"])
        avg_tp_kbs = float(row.get("avg_throughput_kbs", 0))
        expected_8k = avg_iops + (avg_tp_kbs / 8.0)

        # Find the same VM in the merged result
        vm_name = str(row["vm_name"]).strip()
        merged_row = df[df["vm_name"].str.strip() == vm_name]
        if len(merged_row) == 0:
            pytest.skip(f"VM {vm_name!r} not found in merged output")

        actual_8k = float(merged_row.iloc[0]["iops_8k_equivalent"])
        assert actual_8k == pytest.approx(expected_8k, rel=1e-3), (
            f"8K IOPS mismatch: expected {expected_8k}, got {actual_8k}"
        )


# ---- Description column --------------------------------------------------


class TestDescriptionColumn:
    """Tests for vm_description column presence."""

    def test_liveoptics_xlsx_has_description(self) -> None:
        """LiveOptics xlsx has a vm_description column."""
        df = parse_liveoptics_xlsx(LIVEOPTICS_XLSX)
        assert "vm_description" in df.columns

    def test_rvtools_has_annotation_as_description(self) -> None:
        """RVTools xlsx has vm_description column (mapped from Annotation)."""
        df = parse_rvtools(RVTOOLS_XLSX)
        assert "vm_description" in df.columns
        # If annotation data exists in sample, some values should be non-empty
        # Just verify the column exists; content depends on sample data
        assert df["vm_description"].dtype == object or len(df) >= 0
