"""Parser for RVTools xlsx exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers.columns import (
    CANONICAL_COLUMNS,
    REQUIRED_RVTOOLS_COLUMNS,
    RVTOOLS_ALIASES,
    resolve_columns,
)

if TYPE_CHECKING:
    from pathlib import Path


def parse_rvtools(path: Path) -> pd.DataFrame:
    """Parse an RVTools xlsx export into a canonical DataFrame.

    Reads the 'vInfo' sheet and normalizes columns to the canonical schema.

    Args:
        path: Path to the RVTools .xlsx file.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.

    Raises:
        IngestionError: If the file cannot be parsed or required columns are missing.
    """
    try:
        df = pd.read_excel(path, sheet_name="vInfo", engine="openpyxl")
    except (KeyError, ValueError) as exc:
        raise IngestionError(
            f"Cannot read RVTools file: {path.name}. Expected an xlsx file with a 'vInfo' sheet.",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise IngestionError(
            f"Failed to open file: {path.name}. Is it a valid Excel file?",
            details=str(exc),
        ) from exc

    # Strip column whitespace before resolution
    df.columns = df.columns.str.strip()

    col_map = resolve_columns(df, RVTOOLS_ALIASES, REQUIRED_RVTOOLS_COLUMNS)

    # Build canonical DataFrame
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

    # is_template: NaN handled as False (research pitfall 1)
    if col_map.get("is_template"):
        result["is_template"] = df[col_map["is_template"]].fillna(False).astype(bool)
    else:
        result["is_template"] = False

    # is_powered_on: derived from powerstate column
    if col_map.get("powerstate"):
        result["is_powered_on"] = df[col_map["powerstate"]].fillna("").astype(str).str.lower() == "poweredon"
    else:
        result["is_powered_on"] = True

    result["source_format"] = FileFormat.RVTOOLS.value

    return result[CANONICAL_COLUMNS]
