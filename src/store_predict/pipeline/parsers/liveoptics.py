"""Parsers for LiveOptics xlsx and csv exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers.columns import (
    CANONICAL_COLUMNS,
    LIVEOPTICS_ALIASES,
    REQUIRED_LIVEOPTICS_COLUMNS,
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

    return result[CANONICAL_COLUMNS]


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
    return _build_liveoptics_df(df, FileFormat.LIVEOPTICS_XLSX.value)


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
