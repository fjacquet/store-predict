"""Format detection and ingestion orchestrator.

Single entry point for file ingestion: detect_format() identifies the file type,
and ingest_file() dispatches to the appropriate parser and filters templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import openpyxl
import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers import (
    parse_liveoptics_csv,
    parse_liveoptics_xlsx,
    parse_rvtools,
)

if TYPE_CHECKING:
    from pathlib import Path


def detect_format(path: Path) -> FileFormat:
    """Auto-detect the file format from path extension and content.

    Args:
        path: Path to the uploaded file.

    Returns:
        FileFormat enum indicating the detected format.

    Raises:
        IngestionError: If the file does not exist, has an unsupported extension,
            or cannot be identified as a known format.
    """
    if not path.exists():
        raise IngestionError(
            f"File not found: {path.name}",
            details=f"Full path: {path}",
        )

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _detect_csv(path)
    if suffix == ".xlsx":
        return _detect_xlsx(path)

    raise IngestionError(
        f"Unsupported file type: {suffix}. "
        "Please upload .xlsx (RVTools or LiveOptics) or .csv (LiveOptics)."
    )


def _detect_csv(path: Path) -> FileFormat:
    """Check CSV header for LiveOptics signature columns."""
    try:
        header_df = pd.read_csv(path, nrows=0)
    except Exception as exc:
        raise IngestionError(
            f"Cannot read CSV header: {path.name}.",
            details=str(exc),
        ) from exc

    columns = [c.strip() for c in header_df.columns]
    if "VM Name" in columns or "VM OS" in columns:
        return FileFormat.LIVEOPTICS_CSV

    raise IngestionError(
        f"CSV file does not appear to be a LiveOptics export. "
        f"Expected columns like 'VM Name' or 'VM OS'. "
        f"Found: {columns[:10]}",
    )


def _detect_xlsx(path: Path) -> FileFormat:
    """Check xlsx sheet names for RVTools or LiveOptics signatures."""
    try:
        wb = openpyxl.load_workbook(path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()
    except Exception as exc:
        raise IngestionError(
            f"Cannot open Excel file: {path.name}. Is it a valid .xlsx?",
            details=str(exc),
        ) from exc

    if "vInfo" in sheet_names:
        return FileFormat.RVTOOLS
    if "VMs" in sheet_names:
        return FileFormat.LIVEOPTICS_XLSX

    raise IngestionError(
        f"Excel file does not appear to be RVTools or LiveOptics. "
        f"Expected a 'vInfo' or 'VMs' sheet. "
        f"Found sheets: {sheet_names[:5]}",
    )


def ingest_file(path: Path) -> pd.DataFrame:
    """Detect format, parse, and return template-filtered DataFrame.

    This is the single entry point for the UI upload page.

    Args:
        path: Path to the uploaded file.

    Returns:
        DataFrame with canonical columns, template VMs filtered out.

    Raises:
        IngestionError: If detection or parsing fails.
    """
    fmt = detect_format(path)

    if fmt == FileFormat.RVTOOLS:
        df = parse_rvtools(path)
    elif fmt == FileFormat.LIVEOPTICS_XLSX:
        df = parse_liveoptics_xlsx(path)
    elif fmt == FileFormat.LIVEOPTICS_CSV:
        df = parse_liveoptics_csv(path)
    else:
        raise IngestionError(f"No parser available for format: {fmt}")

    # Filter out template VMs
    df = df[~df["is_template"]].reset_index(drop=True)

    return df
