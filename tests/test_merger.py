"""Tests for the best-of-best dual-source merge logic."""

from __future__ import annotations

import pandas as pd
import pytest

from store_predict.pipeline.merger import merge_dual_sources
from store_predict.pipeline.models import FileFormat


def _rvtools_df(**overrides: object) -> pd.DataFrame:
    """Return a minimal RVTools-style DataFrame row."""
    base: dict[str, object] = {
        "vm_name": "vm-001",
        "os_name": "Windows Server 2019",
        "provisioned_mib": 102400.0,
        "in_use_mib": 51200.0,
        "num_cpus": 4,
        "memory_mib": 8192.0,
        "datacenter": "DC-West",
        "cluster": "Cluster-A",
        "is_template": False,
        "is_powered_on": True,
        "vm_description": "Web server",
        "hw_version": 19,
        "tools_status": "toolsOk",
        "source_format": FileFormat.RVTOOLS.value,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def _liveoptics_df(**overrides: object) -> pd.DataFrame:
    """Return a minimal LiveOptics-style DataFrame row."""
    base: dict[str, object] = {
        "vm_name": "vm-001",
        "os_name": "Windows 2019",
        "provisioned_mib": 100000.0,
        "in_use_mib": 60000.0,
        "num_cpus": 4,
        "memory_mib": 8192.0,
        "datacenter": "DC-West",
        "cluster": "Cluster-A",
        "is_template": False,
        "is_powered_on": True,
        "peak_iops": 5000.0,
        "avg_iops": 2500.0,
        "peak_throughput_mbps": 200.0,
        "avg_throughput_mbps": 100.0,
        "avg_read_latency_ms": 1.5,
        "avg_write_latency_ms": 2.0,
        "iops_8k_equivalent": 2800.0,
        "source_format": FileFormat.LIVEOPTICS_XLSX.value,
    }
    base.update(overrides)
    return pd.DataFrame([base])


# ---------------------------------------------------------------------------
# source_format
# ---------------------------------------------------------------------------


def test_source_format_is_merged() -> None:
    rv = _rvtools_df()
    lo = _liveoptics_df()
    result = merge_dual_sources(rv, lo)
    assert (result["source_format"] == FileFormat.MERGED.value).all()


# ---------------------------------------------------------------------------
# Full match — best-of-best column resolution
# ---------------------------------------------------------------------------


def test_provisioned_mib_uses_rvtools() -> None:
    rv = _rvtools_df(provisioned_mib=102400.0)
    lo = _liveoptics_df(provisioned_mib=99000.0)
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "provisioned_mib"] == pytest.approx(102400.0)


def test_os_name_uses_rvtools() -> None:
    rv = _rvtools_df(os_name="Windows Server 2019")
    lo = _liveoptics_df(os_name="Windows 2019 (guest)")
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "os_name"] == "Windows Server 2019"


def test_hw_version_from_rvtools() -> None:
    rv = _rvtools_df(hw_version=19)
    lo = _liveoptics_df()
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "hw_version"] == 19


def test_tools_status_from_rvtools() -> None:
    rv = _rvtools_df(tools_status="toolsOk")
    lo = _liveoptics_df()
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "tools_status"] == "toolsOk"


# ---------------------------------------------------------------------------
# in_use_mib — LiveOptics guest value if > 0, else RVTools
# ---------------------------------------------------------------------------


def test_in_use_mib_uses_liveoptics_when_positive() -> None:
    rv = _rvtools_df(in_use_mib=51200.0)
    lo = _liveoptics_df(in_use_mib=60000.0)
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "in_use_mib"] == pytest.approx(60000.0)


def test_in_use_mib_fallback_to_rvtools_when_lo_is_zero() -> None:
    rv = _rvtools_df(in_use_mib=51200.0)
    lo = _liveoptics_df(in_use_mib=0.0)
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "in_use_mib"] == pytest.approx(51200.0)


def test_in_use_mib_fallback_to_rvtools_when_lo_is_nan() -> None:
    lo = _liveoptics_df(in_use_mib=float("nan"))
    rv = _rvtools_df(in_use_mib=51200.0)
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "in_use_mib"] == pytest.approx(51200.0)


# ---------------------------------------------------------------------------
# Performance columns — LiveOptics only
# ---------------------------------------------------------------------------


def test_performance_columns_from_liveoptics() -> None:
    rv = _rvtools_df()
    lo = _liveoptics_df(peak_iops=5000.0, avg_iops=2500.0)
    result = merge_dual_sources(rv, lo)
    assert result.loc[0, "peak_iops"] == pytest.approx(5000.0)
    assert result.loc[0, "avg_iops"] == pytest.approx(2500.0)


# ---------------------------------------------------------------------------
# Outer join — VMs in only one source are retained
# ---------------------------------------------------------------------------


def test_outer_join_keeps_rvtools_only_vm() -> None:
    rv = pd.concat([_rvtools_df(vm_name="vm-rv-only"), _rvtools_df(vm_name="vm-shared")], ignore_index=True)
    lo = _liveoptics_df(vm_name="vm-shared")
    result = merge_dual_sources(rv, lo)
    assert "vm-rv-only" in result["vm_name"].values
    assert len(result) == 2


def test_outer_join_keeps_liveoptics_only_vm() -> None:
    rv = _rvtools_df(vm_name="vm-shared")
    lo = pd.concat([_liveoptics_df(vm_name="vm-lo-only"), _liveoptics_df(vm_name="vm-shared")], ignore_index=True)
    result = merge_dual_sources(rv, lo)
    assert "vm-lo-only" in result["vm_name"].values
    assert len(result) == 2


def test_rvtools_only_vm_has_nan_performance_columns() -> None:
    rv = _rvtools_df(vm_name="rv-exclusive")
    lo = _liveoptics_df(vm_name="lo-exclusive")
    result = merge_dual_sources(rv, lo)
    rv_row = result[result["vm_name"] == "rv-exclusive"].iloc[0]
    assert pd.isna(rv_row["peak_iops"])


def test_liveoptics_only_vm_has_zero_hw_version() -> None:
    rv = _rvtools_df(vm_name="rv-exclusive")
    lo = _liveoptics_df(vm_name="lo-exclusive")
    result = merge_dual_sources(rv, lo)
    lo_row = result[result["vm_name"] == "lo-exclusive"].iloc[0]
    assert lo_row["hw_version"] == 0


def test_liveoptics_only_vm_has_empty_tools_status() -> None:
    rv = _rvtools_df(vm_name="rv-exclusive")
    lo = _liveoptics_df(vm_name="lo-exclusive")
    result = merge_dual_sources(rv, lo)
    lo_row = result[result["vm_name"] == "lo-exclusive"].iloc[0]
    assert lo_row["tools_status"] == ""


# ---------------------------------------------------------------------------
# Merge stats
# ---------------------------------------------------------------------------


def test_merge_stats_are_stored_in_attrs() -> None:
    rv = pd.concat([_rvtools_df(vm_name="vm-shared"), _rvtools_df(vm_name="vm-rv-only")], ignore_index=True)
    lo = pd.concat([_liveoptics_df(vm_name="vm-shared"), _liveoptics_df(vm_name="vm-lo-only")], ignore_index=True)
    result = merge_dual_sources(rv, lo)
    stats = result.attrs.get("merge_stats", {})
    assert stats["total"] == 3
    assert stats["matched"] == 1
    assert stats["rv_only"] == 1
    assert stats["lo_only"] == 1


# ---------------------------------------------------------------------------
# vm_name whitespace stripping
# ---------------------------------------------------------------------------


def test_vm_name_whitespace_stripped_for_join() -> None:
    rv = _rvtools_df(vm_name="  vm-001  ")
    lo = _liveoptics_df(vm_name="vm-001")
    result = merge_dual_sources(rv, lo)
    # Should match — one row
    assert len(result) == 1


def test_vm_name_case_insensitive_join() -> None:
    rv = _rvtools_df(vm_name="VM-WEB-01")
    lo = _liveoptics_df(vm_name="vm-web-01")
    result = merge_dual_sources(rv, lo)
    # Should match despite different casing — one row
    assert len(result) == 1


def test_is_template_dtype_is_bool() -> None:
    """Ensure ~is_template never raises due to object dtype."""
    rv = _rvtools_df(vm_name="rv-only")
    lo = _liveoptics_df(vm_name="lo-only")
    result = merge_dual_sources(rv, lo)
    # This must not raise even for mixed-origin rows
    mask = ~result["is_template"].fillna(False).astype(bool)
    assert mask.dtype == bool


def test_numeric_vm_name_joins_without_nan_key() -> None:
    """Numeric VM identifiers must not collapse to NaN after .str.strip()."""
    rv = _rvtools_df(vm_name=12345)
    lo = _liveoptics_df(vm_name=12345)
    result = merge_dual_sources(rv, lo)
    # Numeric vm_name flows through astype(str) + strip and the dual-source row
    # is matched instead of splitting into two partial rows.
    assert len(result) == 1
    assert result.iloc[0]["vm_name"] == "12345"
