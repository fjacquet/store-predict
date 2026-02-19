"""Parsers for LiveOptics xlsx and csv exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers.columns import (
    CANONICAL_COLUMNS,
    LIVEOPTICS_ALIASES,
    LIVEOPTICS_PERFORMANCE_ALIASES,
    REQUIRED_LIVEOPTICS_COLUMNS,
    REQUIRED_LIVEOPTICS_PERFORMANCE_COLUMNS,
    resolve_columns,
)

if TYPE_CHECKING:
    from pathlib import Path


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
            perf_df["peak_throughput_mbs"] = pd.to_numeric(
                perf_df["peak_throughput_kbs"], errors="coerce"
            ) / 1024.0
        else:
            perf_df["peak_throughput_mbs"] = float("nan")

        if "avg_throughput_kbs" in perf_df.columns:
            perf_df["avg_throughput_mbs"] = pd.to_numeric(
                perf_df["avg_throughput_kbs"], errors="coerce"
            ) / 1024.0
        else:
            perf_df["avg_throughput_mbs"] = float("nan")

        # Compute 8K equivalent IOPS: avg_iops + (avg_throughput_kbs / 8.0)
        avg_iops = pd.to_numeric(perf_df.get("avg_iops", float("nan")), errors="coerce")
        avg_tp_kbs = pd.to_numeric(perf_df.get("avg_throughput_kbs", float("nan")), errors="coerce")
        perf_df["iops_8k_equivalent"] = avg_iops + (avg_tp_kbs / 8.0)

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

    return result[CANONICAL_COLUMNS]


def parse_liveoptics_csv(path: Path) -> pd.DataFrame:
    """Parse a LiveOptics csv export into a canonical DataFrame.

    Tries UTF-8 encoding first, then falls back to Latin-1.

    Args:
        path: Path to the LiveOptics .csv file.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.

    Raises:
        IngestionError: If the file cannot be decoded or required columns are missing.
    """
    df: pd.DataFrame | None = None
    encodings = ["utf-8", "latin-1"]

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
        raise IngestionError("Cannot decode CSV file. Tried UTF-8 and Latin-1 encodings.")

    df.columns = df.columns.str.strip()
    return _build_liveoptics_df(df, FileFormat.LIVEOPTICS_CSV.value)
