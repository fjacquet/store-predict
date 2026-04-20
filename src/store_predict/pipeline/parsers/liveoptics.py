"""Parsers for LiveOptics xlsx and csv exports."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers.columns import (
    CANONICAL_COLUMNS,
    LIVEOPTICS_ALIASES,
    LIVEOPTICS_PERFORMANCE_ALIASES,
    LIVEOPTICS_VM_DISKS_ALIASES,
    REQUIRED_LIVEOPTICS_COLUMNS,
    REQUIRED_LIVEOPTICS_PERFORMANCE_COLUMNS,
    REQUIRED_LIVEOPTICS_VM_DISKS_COLUMNS,
    resolve_columns,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _build_liveoptics_df(
    df: pd.DataFrame,
    source_format: str,
) -> pd.DataFrame:
    """Build a canonical DataFrame from a resolved LiveOptics source.

    Args:
        df: Raw DataFrame with columns already stripped.
        source_format: FileFormat value string for the source_format column.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.
    """
    col_map = resolve_columns(df, LIVEOPTICS_ALIASES, REQUIRED_LIVEOPTICS_COLUMNS)

    result = pd.DataFrame()
    result["vm_name"] = df[col_map["vm_name"]].fillna("")
    result["os_name"] = df[col_map["os_name"]].fillna("")
    result["num_cpus"] = (
        pd.to_numeric(df[col_map["num_cpus"]], errors="coerce").fillna(0).astype(int) if col_map.get("num_cpus") else 0
    )
    result["memory_mib"] = (
        pd.to_numeric(df[col_map["memory_mib"]], errors="coerce").fillna(0.0) if col_map.get("memory_mib") else 0.0
    )
    result["provisioned_mib"] = pd.to_numeric(df[col_map["provisioned_mib"]], errors="coerce").fillna(0.0)
    result["in_use_mib"] = pd.to_numeric(df[col_map["in_use_mib"]], errors="coerce").fillna(0.0)

    # Optional columns
    if col_map.get("datacenter"):
        result["datacenter"] = df[col_map["datacenter"]].fillna("")
    else:
        result["datacenter"] = ""

    if col_map.get("cluster"):
        result["cluster"] = df[col_map["cluster"]].fillna("")
    else:
        result["cluster"] = ""

    if col_map.get("is_template"):
        result["is_template"] = df[col_map["is_template"]].fillna(False).astype(bool)
    else:
        result["is_template"] = False

    if col_map.get("powerstate"):
        result["is_powered_on"] = df[col_map["powerstate"]].fillna("").astype(str).str.lower() == "poweredon"
    else:
        result["is_powered_on"] = True

    result["source_format"] = source_format

    # Description field (optional)
    if col_map.get("vm_description"):
        result["vm_description"] = df[col_map["vm_description"]].fillna("")
    else:
        result["vm_description"] = ""

    # hw_version and tools_status: not available in LiveOptics exports — use sentinel values
    # health_checks.py guards all HW checks with hw_version > 0
    result["hw_version"] = 0
    result["tools_status"] = ""

    # Performance columns default to NaN (populated later for xlsx from VM Performance sheet)
    for perf_col in [
        "peak_iops",
        "avg_iops",
        "peak_throughput_mbs",
        "avg_throughput_mbs",
        "peak_latency_ms",
        "avg_read_latency_ms",
        "avg_write_latency_ms",
        "iops_8k_equivalent",
    ]:
        result[perf_col] = float("nan")

    result["row_index"] = 0  # placeholder; overwritten by ingest_file after reset_index
    return result[CANONICAL_COLUMNS]


def parse_liveoptics_performance(path: Path) -> pd.DataFrame:
    """Parse the VM Performance sheet from a LiveOptics xlsx export.

    Args:
        path: Path to the LiveOptics .xlsx file.

    Returns:
        DataFrame with performance columns keyed by vm_name.
        Empty DataFrame if sheet is missing or cannot be parsed.
    """
    perf_columns = [
        "vm_name",
        "peak_iops",
        "avg_iops",
        "peak_throughput_kbs",
        "avg_throughput_kbs",
        "peak_latency_ms",
        "avg_read_latency_ms",
        "avg_write_latency_ms",
    ]
    try:
        df = pd.read_excel(path, sheet_name="VM Performance", engine="openpyxl")
    except (KeyError, ValueError):
        return pd.DataFrame(columns=perf_columns)
    except Exception:
        return pd.DataFrame(columns=perf_columns)

    df.columns = df.columns.str.strip()

    try:
        col_map = resolve_columns(
            df,
            LIVEOPTICS_PERFORMANCE_ALIASES,
            REQUIRED_LIVEOPTICS_PERFORMANCE_COLUMNS,
        )
    except Exception:
        return pd.DataFrame(columns=perf_columns)

    result = pd.DataFrame()
    for canonical in perf_columns:
        actual = col_map.get(canonical)
        if actual:
            result[canonical] = pd.to_numeric(df[actual], errors="coerce") if canonical != "vm_name" else df[actual]
        else:
            result[canonical] = float("nan") if canonical != "vm_name" else ""

    return result


def _apply_vm_disks_override(
    result: pd.DataFrame,
    raw_vms_df: pd.DataFrame,
    vm_disks_df: pd.DataFrame,
) -> pd.DataFrame:
    """Override ``provisioned_mib`` / ``in_use_mib`` on ``result`` with summed
    per-disk totals from ``vm_disks_df``.

    Joins on MOB ID (vCenter-unique) when present in both frames; falls back
    to VM Name. VMs with no matching disk data keep their VMs-sheet values.
    """
    use_mob_id = (
        "MOB ID" in raw_vms_df.columns
        and "mob_id" in vm_disks_df.columns
        and vm_disks_df["mob_id"].astype(str).str.strip().ne("").all()
    )

    if use_mob_id:
        result = result.copy()
        result["_join_key"] = raw_vms_df["MOB ID"].astype(str).str.strip().values
        vm_disks_df = vm_disks_df.copy()
        vm_disks_df["_join_key"] = vm_disks_df["mob_id"].astype(str).str.strip()
    else:
        result = result.copy()
        result["_join_key"] = result["vm_name"].astype(str).str.strip()
        vm_disks_df = vm_disks_df.copy()
        vm_disks_df["_join_key"] = vm_disks_df["vm_name"].astype(str).str.strip()

    merged = result.merge(
        vm_disks_df[["_join_key", "disks_provisioned_mib", "disks_in_use_mib"]],
        on="_join_key",
        how="left",
    )

    prov = pd.to_numeric(merged["disks_provisioned_mib"], errors="coerce")
    used = pd.to_numeric(merged["disks_in_use_mib"], errors="coerce")
    result["provisioned_mib"] = prov.where(prov.notna(), result["provisioned_mib"]).astype(float)
    result["in_use_mib"] = used.where(used.notna(), result["in_use_mib"]).astype(float)
    result = result.drop(columns=["_join_key"])
    return result


def parse_liveoptics_vm_disks(path: Path) -> pd.DataFrame:
    """Aggregate the 'VM Disks' sheet of a LiveOptics xlsx export per VM.

    LiveOptics' 'VMs' sheet column 'Virtual Disk Size (MiB)' reports only the
    primary virtual disk, not the sum across all disks. Multi-disk VMs are
    therefore under-reported. This helper sums per-disk capacities and used
    bytes so the caller can override the VMs-sheet values.

    Args:
        path: Path to the LiveOptics .xlsx file.

    Returns:
        DataFrame with columns ``[mob_id, vm_name, disks_provisioned_mib,
        disks_in_use_mib]``, one row per VM. Empty DataFrame if the sheet is
        absent or unreadable — caller should then fall back to VMs-sheet values.
    """
    empty_cols = ["mob_id", "vm_name", "disks_provisioned_mib", "disks_in_use_mib"]
    try:
        df = pd.read_excel(path, sheet_name="VM Disks", engine="openpyxl")
    except (KeyError, ValueError):
        return pd.DataFrame(columns=empty_cols)
    except Exception:
        return pd.DataFrame(columns=empty_cols)

    df.columns = df.columns.str.strip()

    try:
        col_map = resolve_columns(
            df,
            LIVEOPTICS_VM_DISKS_ALIASES,
            REQUIRED_LIVEOPTICS_VM_DISKS_COLUMNS,
        )
    except Exception:
        return pd.DataFrame(columns=empty_cols)

    capacity = pd.to_numeric(df[col_map["capacity_mib"]], errors="coerce").fillna(0.0)
    used = (
        pd.to_numeric(df[col_map["used_mib"]], errors="coerce").fillna(0.0)
        if col_map.get("used_mib")
        else pd.Series([0.0] * len(df))
    )

    mob_col = col_map.get("mob_id")
    name_col = col_map.get("vm_name")

    # Choose join key: prefer MOB ID (vCenter-unique), fall back to VM Name.
    if mob_col and df[mob_col].notna().all():
        key_col = mob_col
        key_canonical = "mob_id"
    elif name_col:
        key_col = name_col
        key_canonical = "vm_name"
    else:
        return pd.DataFrame(columns=empty_cols)

    working = pd.DataFrame(
        {
            "_key": df[key_col].astype(str).str.strip(),
            "_mob_id": df[mob_col].astype(str).str.strip() if mob_col else "",
            "_vm_name": df[name_col].astype(str).str.strip() if name_col else "",
            "_capacity": capacity,
            "_used": used,
        }
    )

    grouped = (
        working.groupby("_key", dropna=False)
        .agg(
            mob_id=("_mob_id", "first"),
            vm_name=("_vm_name", "first"),
            disks_provisioned_mib=("_capacity", "sum"),
            disks_in_use_mib=("_used", "sum"),
        )
        .reset_index(drop=True)
    )

    logger.info(
        "LiveOptics VM Disks: %d disk rows aggregated into %d VMs (join=%s)",
        len(df),
        len(grouped),
        key_canonical,
    )

    return grouped[["mob_id", "vm_name", "disks_provisioned_mib", "disks_in_use_mib"]]


def parse_liveoptics_xlsx(path: Path) -> pd.DataFrame:
    """Parse a LiveOptics xlsx export into a canonical DataFrame.

    Reads the 'VMs' sheet and normalizes columns to the canonical schema.

    Args:
        path: Path to the LiveOptics .xlsx file.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.

    Raises:
        IngestionError: If the file cannot be parsed or required columns are missing.
    """
    try:
        df = pd.read_excel(path, sheet_name="VMs", engine="openpyxl")
    except (KeyError, ValueError) as exc:
        raise IngestionError(
            f"Cannot read LiveOptics file: {path.name}. Expected an xlsx file with a 'VMs' sheet.",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise IngestionError(
            f"Failed to open file: {path.name}. Is it a valid Excel file?",
            details=str(exc),
        ) from exc

    df.columns = df.columns.str.strip()
    result = _build_liveoptics_df(df, FileFormat.LIVEOPTICS_XLSX.value)

    # Override provisioned_mib / in_use_mib with per-VM SUM from the 'VM Disks'
    # sheet when present. The 'VMs' sheet's 'Virtual Disk Size (MiB)' reports
    # only the primary disk, causing severe under-reporting for multi-disk VMs
    # (e.g. a container cluster with avg 11 disks/VM showed ~4 TiB instead of
    # ~40 TiB). Fall back to VMs-sheet values if VM Disks sheet is missing.
    vm_disks_df = parse_liveoptics_vm_disks(path)
    if not vm_disks_df.empty:
        result = _apply_vm_disks_override(result, df, vm_disks_df)

    # Join performance data from VM Performance sheet
    perf_df = parse_liveoptics_performance(path)
    if not perf_df.empty and len(perf_df) > 0:
        # Strip whitespace on join keys
        result["vm_name"] = result["vm_name"].astype(str).str.strip()
        perf_df["vm_name"] = perf_df["vm_name"].astype(str).str.strip()

        # Drop performance columns from result before merge (they are NaN defaults)
        perf_cols_to_update = [
            "peak_iops",
            "avg_iops",
            "peak_throughput_mbs",
            "avg_throughput_mbs",
            "peak_latency_ms",
            "avg_read_latency_ms",
            "avg_write_latency_ms",
            "iops_8k_equivalent",
        ]
        result = result.drop(columns=perf_cols_to_update, errors="ignore")

        # Convert throughput from KB/s to MB/s
        if "peak_throughput_kbs" in perf_df.columns:
            perf_df["peak_throughput_mbs"] = pd.to_numeric(perf_df["peak_throughput_kbs"], errors="coerce") / 1024.0
        else:
            perf_df["peak_throughput_mbs"] = float("nan")

        if "avg_throughput_kbs" in perf_df.columns:
            perf_df["avg_throughput_mbs"] = pd.to_numeric(perf_df["avg_throughput_kbs"], errors="coerce") / 1024.0
        else:
            perf_df["avg_throughput_mbs"] = float("nan")

        # Compute 8K equivalent IOPS: throughput_KB/s / 8 (normalize all IO to 8K block size)
        avg_tp_kbs = pd.to_numeric(perf_df.get("avg_throughput_kbs", float("nan")), errors="coerce")
        perf_df["iops_8k_equivalent"] = avg_tp_kbs / 8.0

        # Select columns for merge
        merge_cols = [
            "vm_name",
            "peak_iops",
            "avg_iops",
            "peak_throughput_mbs",
            "avg_throughput_mbs",
            "peak_latency_ms",
            "avg_read_latency_ms",
            "avg_write_latency_ms",
            "iops_8k_equivalent",
        ]
        perf_merge = perf_df[[c for c in merge_cols if c in perf_df.columns]]

        result = result.merge(perf_merge, on="vm_name", how="left")

        # Ensure all performance columns exist
        for col in perf_cols_to_update:
            if col not in result.columns:
                result[col] = float("nan")

    result["row_index"] = 0  # placeholder; overwritten by ingest_file after reset_index
    return result[CANONICAL_COLUMNS]


def parse_liveoptics_csv(path: Path) -> pd.DataFrame:
    """Parse a LiveOptics csv export into a canonical DataFrame.

    Tries UTF-8 (with BOM stripping) first, then plain UTF-8, then falls back to Latin-1.
    ``utf-8-sig`` silently strips any ``\\ufeff`` prefix that Excel adds when
    saving as CSV — without it, the first column header becomes ``\\ufeffVM Name``
    and the canonical-column mapping silently loses data.

    Args:
        path: Path to the LiveOptics .csv file.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.

    Raises:
        IngestionError: If the file cannot be decoded or required columns are missing.
    """
    df: pd.DataFrame | None = None
    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    for encoding in encodings:
        try:
            df = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            raise IngestionError(
                f"Failed to read CSV file: {path.name}.",
                details=str(exc),
            ) from exc

    if df is None:
        raise IngestionError("Cannot decode CSV file. Tried UTF-8 (with/without BOM) and Latin-1 encodings.")

    df.columns = df.columns.str.strip()
    return _build_liveoptics_df(df, FileFormat.LIVEOPTICS_CSV.value)
