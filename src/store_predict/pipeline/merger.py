"""Best-of-best merge of RVTools and LiveOptics DataFrames.

Each source contributes unique, non-overlapping fields.  The merge produces
a single canonical DataFrame where every column is populated from whichever
source provides the most accurate value for that column.
"""

from __future__ import annotations

import logging

import pandas as pd

from store_predict.pipeline.models import FileFormat

logger = logging.getLogger(__name__)


def merge_dual_sources(rvtools_df: pd.DataFrame, liveoptics_df: pd.DataFrame) -> pd.DataFrame:
    """Merge RVTools and LiveOptics DataFrames using best-of-best column rules.

    Args:
        rvtools_df: DataFrame from :func:`parse_rvtools`.
        liveoptics_df: DataFrame from :func:`parse_liveoptics_xlsx` or
            :func:`parse_liveoptics_csv`.

    Returns:
        Merged DataFrame with ``source_format`` set to ``"merged"`` on all rows.
    """
    rv = rvtools_df.copy()
    lo = liveoptics_df.copy()

    # Normalise join key: strip whitespace and lowercase for case-insensitive matching.
    # astype(str) guards against numeric-only VM names (lab environments): without it,
    # .str.strip() on a float column returns NaN and every row becomes a distinct key.
    rv["vm_name"] = rv["vm_name"].astype(str).str.strip()
    lo["vm_name"] = lo["vm_name"].astype(str).str.strip()
    rv["_join_key"] = rv["vm_name"].str.lower()
    lo["_join_key"] = lo["vm_name"].str.lower()

    # Suffix columns so we can resolve conflicts after the merge
    rv = rv.add_suffix("_rv").rename(columns={"_join_key_rv": "_join_key"})
    lo = lo.add_suffix("_lo").rename(columns={"_join_key_lo": "_join_key"})

    merged = pd.merge(rv, lo, on="_join_key", how="outer")

    # Restore vm_name: prefer RVTools casing, fall back to LiveOptics
    merged["vm_name"] = merged.get("vm_name_rv", pd.Series(dtype=object)).where(
        merged.get("vm_name_rv", pd.Series(dtype=object)).notna(),
        merged.get("vm_name_lo", pd.Series(dtype=object)),
    )
    merged = merged.drop(columns=["_join_key"], errors="ignore")

    # ------------------------------------------------------------------ #
    # Apply best-of-best column priority rules
    # ------------------------------------------------------------------ #

    # provisioned_mib — RVTools preferred (block-level accuracy)
    merged["provisioned_mib"] = merged.get("provisioned_mib_rv", pd.Series(dtype=float)).where(
        merged.get("provisioned_mib_rv", pd.Series(dtype=float)).notna(),
        merged.get("provisioned_mib_lo", pd.Series(dtype=float)),
    )

    # in_use_mib — LiveOptics guest value if > 0, else RVTools
    lo_used = merged.get("in_use_mib_lo", pd.Series(dtype=float))
    rv_used = merged.get("in_use_mib_rv", pd.Series(dtype=float))
    merged["in_use_mib"] = lo_used.where((lo_used.notna()) & (lo_used > 0), rv_used)

    # os_name — RVTools preferred
    merged["os_name"] = _prefer_rv(merged, "os_name")

    # num_cpus — RVTools preferred
    merged["num_cpus"] = _prefer_rv(merged, "num_cpus")

    # memory_mib — RVTools preferred
    merged["memory_mib"] = _prefer_rv(merged, "memory_mib")

    # datacenter — RVTools preferred
    merged["datacenter"] = _prefer_rv(merged, "datacenter")

    # cluster — RVTools preferred
    merged["cluster"] = _prefer_rv(merged, "cluster")

    # is_template — RVTools preferred; cast to bool to avoid object-dtype ~mask issues
    merged["is_template"] = _prefer_rv(merged, "is_template").fillna(False).astype(bool)

    # is_powered_on — RVTools preferred
    merged["is_powered_on"] = _prefer_rv(merged, "is_powered_on").fillna(True).astype(bool)

    # RVTools-only columns — use as-is, NaN for LiveOptics-only VMs
    for col in ("vm_description", "hw_version", "tools_status"):
        merged[col] = merged.get(f"{col}_rv", pd.Series(dtype=object))

    # hw_version defaults to 0 for LiveOptics-only VMs
    if "hw_version" in merged.columns:
        merged["hw_version"] = merged["hw_version"].fillna(0)

    # tools_status defaults to "" for LiveOptics-only VMs
    if "tools_status" in merged.columns:
        merged["tools_status"] = merged["tools_status"].fillna("")

    # LiveOptics-only performance columns — keep as-is (NaN for RVTools-only VMs)
    for col in (
        "peak_iops",
        "avg_iops",
        "peak_throughput_mbps",
        "avg_throughput_mbps",
        "avg_read_latency_ms",
        "avg_write_latency_ms",
        "iops_8k_equivalent",
    ):
        lo_col = f"{col}_lo"
        if lo_col in merged.columns:
            merged[col] = merged[lo_col]
        elif col not in merged.columns:
            merged[col] = float("nan")

    # Mark combined source
    merged["source_format"] = FileFormat.MERGED.value

    # Drop the suffixed helper columns
    suffix_cols = [c for c in merged.columns if c.endswith("_rv") or c.endswith("_lo")]
    merged = merged.drop(columns=suffix_cols)

    # Log match statistics (based on lowercased names for accuracy)
    total = len(merged)
    rv_keys = (
        set(rv["_join_key"].dropna())
        if "_join_key" in rv.columns
        else set(rv.get("vm_name_rv", pd.Series()).str.lower().dropna())
    )
    lo_keys = (
        set(lo["_join_key"].dropna())
        if "_join_key" in lo.columns
        else set(lo.get("vm_name_lo", pd.Series()).str.lower().dropna())
    )
    matched = len(rv_keys & lo_keys)
    rv_only = len(rv_keys - lo_keys)
    lo_only = len(lo_keys - rv_keys)
    logger.info(
        "Merge complete: total=%d matched=%d rv_only=%d lo_only=%d",
        total,
        matched,
        rv_only,
        lo_only,
    )

    # Expose stats as DataFrame attributes for the UI notification
    merged.attrs["merge_stats"] = {
        "total": total,
        "matched": matched,
        "rv_only": rv_only,
        "lo_only": lo_only,
    }

    return merged


def _prefer_rv(merged: pd.DataFrame, col: str) -> pd.Series:
    """Return RVTools value if present, else LiveOptics fallback."""
    rv_col = f"{col}_rv"
    lo_col = f"{col}_lo"
    rv_series = merged.get(rv_col, pd.Series(index=merged.index, dtype=object))
    lo_series = merged.get(lo_col, pd.Series(index=merged.index, dtype=object))
    return rv_series.where(rv_series.notna(), lo_series)
