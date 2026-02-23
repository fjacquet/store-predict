"""Tests for datacenter/cluster scope filtering logic."""

from __future__ import annotations

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Pure filtering logic (extracted from state.py for testability)
# ---------------------------------------------------------------------------


def _apply_scope_filter(
    df: pd.DataFrame,
    selected_dcs: list[str],
    selected_clusters: list[str],
) -> pd.DataFrame:
    """Apply datacenter/cluster scope filter to a DataFrame.

    Mirrors the logic in load_filtered_session_data() but without
    NiceGUI session dependency.
    """
    if selected_dcs and "datacenter" in df.columns:
        df = df[df["datacenter"].isin(selected_dcs)]
    if selected_clusters and "cluster" in df.columns:
        df = df[df["cluster"].isin(selected_clusters)]
    return df


@pytest.fixture
def multi_dc_df() -> pd.DataFrame:
    """DataFrame with VMs across 3 datacenters and 4 clusters."""
    return pd.DataFrame(
        [
            {
                "vm_name": "SQL-01",
                "datacenter": "DC1",
                "cluster": "CL-A",
                "provisioned_mib": 10240,
                "workload_category": "Database/Microsoft SQL",
                "drr": 5.0,
            },
            {
                "vm_name": "SQL-02",
                "datacenter": "DC1",
                "cluster": "CL-B",
                "provisioned_mib": 20480,
                "workload_category": "Database/Microsoft SQL",
                "drr": 5.0,
            },
            {
                "vm_name": "WEB-01",
                "datacenter": "DC2",
                "cluster": "CL-C",
                "provisioned_mib": 5120,
                "workload_category": "Virtual Machines",
                "drr": 5.0,
            },
            {
                "vm_name": "WEB-02",
                "datacenter": "DC2",
                "cluster": "CL-C",
                "provisioned_mib": 5120,
                "workload_category": "Virtual Machines",
                "drr": 5.0,
            },
            {
                "vm_name": "SAP-01",
                "datacenter": "DC3",
                "cluster": "CL-D",
                "provisioned_mib": 51200,
                "workload_category": "Database/SAP",
                "drr": 2.0,
            },
        ]
    )


@pytest.fixture
def no_dc_df() -> pd.DataFrame:
    """DataFrame with no datacenter/cluster columns (e.g., LiveOptics)."""
    return pd.DataFrame(
        [
            {"vm_name": "VM-01", "provisioned_mib": 10240, "workload_category": "Virtual Machines", "drr": 5.0},
            {"vm_name": "VM-02", "provisioned_mib": 20480, "workload_category": "Virtual Machines", "drr": 5.0},
        ]
    )


@pytest.fixture
def empty_dc_df() -> pd.DataFrame:
    """DataFrame with datacenter/cluster columns but all empty values."""
    return pd.DataFrame(
        [
            {"vm_name": "VM-01", "datacenter": "", "cluster": "", "provisioned_mib": 10240},
            {"vm_name": "VM-02", "datacenter": "", "cluster": "", "provisioned_mib": 20480},
        ]
    )


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------


class TestScopeFilter:
    """Test datacenter/cluster scope filtering."""

    def test_no_filter_returns_all(self, multi_dc_df: pd.DataFrame) -> None:
        """Empty selection lists mean 'include all'."""
        result = _apply_scope_filter(multi_dc_df, [], [])
        assert len(result) == 5

    def test_filter_single_datacenter(self, multi_dc_df: pd.DataFrame) -> None:
        """Filter to DC1 should return 2 VMs."""
        result = _apply_scope_filter(multi_dc_df, ["DC1"], [])
        assert len(result) == 2
        assert set(result["vm_name"]) == {"SQL-01", "SQL-02"}

    def test_filter_multiple_datacenters(self, multi_dc_df: pd.DataFrame) -> None:
        """Filter to DC1 + DC2 should return 4 VMs."""
        result = _apply_scope_filter(multi_dc_df, ["DC1", "DC2"], [])
        assert len(result) == 4

    def test_filter_single_cluster(self, multi_dc_df: pd.DataFrame) -> None:
        """Filter to CL-C should return 2 VMs (both in DC2)."""
        result = _apply_scope_filter(multi_dc_df, [], ["CL-C"])
        assert len(result) == 2
        assert all(result["datacenter"] == "DC2")

    def test_filter_datacenter_and_cluster(self, multi_dc_df: pd.DataFrame) -> None:
        """Combined filter: DC1 datacenter + CL-A cluster."""
        result = _apply_scope_filter(multi_dc_df, ["DC1"], ["CL-A"])
        assert len(result) == 1
        assert result.iloc[0]["vm_name"] == "SQL-01"

    def test_filter_nonexistent_datacenter(self, multi_dc_df: pd.DataFrame) -> None:
        """Filter to nonexistent DC should return 0 VMs."""
        result = _apply_scope_filter(multi_dc_df, ["DC-NONE"], [])
        assert len(result) == 0

    def test_no_dc_columns_ignores_filter(self, no_dc_df: pd.DataFrame) -> None:
        """If columns don't exist, filter is a no-op."""
        result = _apply_scope_filter(no_dc_df, ["DC1"], ["CL-A"])
        assert len(result) == 2

    def test_empty_dc_values_not_matched(self, empty_dc_df: pd.DataFrame) -> None:
        """Empty string datacenter values should not match a DC filter."""
        result = _apply_scope_filter(empty_dc_df, ["DC1"], [])
        assert len(result) == 0

    def test_all_datacenters_selected_equals_no_filter(self, multi_dc_df: pd.DataFrame) -> None:
        """Selecting all datacenters is equivalent to no filter."""
        all_dcs = multi_dc_df["datacenter"].unique().tolist()
        result = _apply_scope_filter(multi_dc_df, all_dcs, [])
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Unique value extraction tests (mirrors scope page logic)
# ---------------------------------------------------------------------------


class TestUniqueValues:
    """Test extraction of unique datacenter/cluster values for the scope page."""

    def test_extract_unique_datacenters(self, multi_dc_df: pd.DataFrame) -> None:
        """Should extract 3 unique datacenters."""
        dcs = sorted({str(v) for v in multi_dc_df["datacenter"] if v and str(v).strip()})
        assert dcs == ["DC1", "DC2", "DC3"]

    def test_extract_unique_clusters(self, multi_dc_df: pd.DataFrame) -> None:
        """Should extract 4 unique clusters."""
        clusters = sorted({str(v) for v in multi_dc_df["cluster"] if v and str(v).strip()})
        assert clusters == ["CL-A", "CL-B", "CL-C", "CL-D"]

    def test_empty_values_excluded(self, empty_dc_df: pd.DataFrame) -> None:
        """Empty string values should be filtered out."""
        dcs = sorted({str(v) for v in empty_dc_df["datacenter"] if v and str(v).strip()})
        assert dcs == []


# ---------------------------------------------------------------------------
# Merge-back tests (filtered edits → full session)
# ---------------------------------------------------------------------------


class TestMergeRowChanges:
    """Test that editing filtered rows merges correctly back to full dataset."""

    def test_merge_drr_change(self, multi_dc_df: pd.DataFrame) -> None:
        """Editing DRR in a filtered subset should merge back to full data."""
        # Simulate: filter to DC1, edit DRR for SQL-01
        full_records = multi_dc_df.to_dict(orient="records")
        full_records[0]["row_index"] = 0  # SQL-01
        full_records[1]["row_index"] = 1  # SQL-02

        # Edited row from filtered view
        edited = {"row_index": 0, "drr": 10.0, "workload_category": "Database/Oracle", "workload_subcategory": "Oracle"}

        # Merge logic (mirrors save_filtered_rows)
        edited_by_idx = {int(edited["row_index"]): edited}
        for row in full_records:
            idx = int(row.get("row_index", -1))
            if idx in edited_by_idx:
                for key in ("workload_category", "workload_subcategory", "drr"):
                    if key in edited_by_idx[idx]:
                        row[key] = edited_by_idx[idx][key]

        assert full_records[0]["drr"] == 10.0
        assert full_records[0]["workload_category"] == "Database/Oracle"
        # Unedited row should be unchanged
        assert full_records[1]["drr"] == 5.0

    def test_merge_preserves_unfiltered_rows(self) -> None:
        """Rows not in the filtered set should remain untouched."""
        full = [
            {"row_index": 0, "vm_name": "A", "drr": 5.0, "workload_category": "Cat1", "workload_subcategory": "Sub1"},
            {"row_index": 1, "vm_name": "B", "drr": 3.0, "workload_category": "Cat2", "workload_subcategory": "Sub2"},
        ]
        # Only row 0 is in the filtered set
        edited_by_idx = {0: {"drr": 8.0, "workload_category": "Cat3", "workload_subcategory": "Sub3"}}
        for row in full:
            idx = int(row.get("row_index", -1))
            if idx in edited_by_idx:
                for key in ("workload_category", "workload_subcategory", "drr"):
                    if key in edited_by_idx[idx]:
                        row[key] = edited_by_idx[idx][key]

        assert full[0]["drr"] == 8.0
        assert full[1]["drr"] == 3.0
        assert full[1]["workload_category"] == "Cat2"


# ---------------------------------------------------------------------------
# Calculation on filtered data
# ---------------------------------------------------------------------------


class TestFilteredCalculation:
    """Test that calculations on filtered data produce correct results."""

    def test_filtered_totals(self, multi_dc_df: pd.DataFrame) -> None:
        """Filtering should change the total provisioned capacity."""
        from store_predict.pipeline.calculation import calculate

        # Full data
        all_rows = multi_dc_df.to_dict(orient="records")
        for i, row in enumerate(all_rows):
            row["row_index"] = i
            row["workload_subcategory"] = ""
            row["in_use_mib"] = row["provisioned_mib"] * 0.5
            row["os_name"] = "Windows"
            row["num_cpus"] = 4
            row["memory_mib"] = 8192
        full_summary = calculate(all_rows)

        # Filtered to DC1 only
        dc1_rows = [r for r in all_rows if r["datacenter"] == "DC1"]
        dc1_summary = calculate(dc1_rows)

        assert dc1_summary.total_vms == 2
        assert dc1_summary.total_provisioned_mib < full_summary.total_provisioned_mib

    def test_empty_filter_result_handled(self) -> None:
        """An empty filtered result should produce a zero-VM summary."""
        from store_predict.pipeline.calculation import calculate

        summary = calculate([])
        assert summary.total_vms == 0
        assert summary.total_provisioned_mib == 0
