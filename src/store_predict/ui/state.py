"""Per-tab session state helpers for DataFrame serialization and project metadata."""

from __future__ import annotations

import functools

import pandas as pd
from nicegui import app

from store_predict.config import DRR_CSV_PATH
from store_predict.services.drr_table import DRRTable


def save_session_data(df: pd.DataFrame, project_name: str) -> None:
    """Store classified DataFrame and project name in tab-scoped session.

    NaN values are converted to None for JSON serialization compatibility.
    """
    records: list[dict] = df.to_dict(orient="records")
    for row in records:
        for key, val in row.items():
            if isinstance(val, float) and val != val:  # NaN check
                row[key] = None
    app.storage.tab["vm_data"] = records
    app.storage.tab["project_name"] = project_name


def load_session_data() -> pd.DataFrame | None:
    """Retrieve DataFrame from session, or None if not uploaded yet."""
    records = app.storage.tab.get("vm_data")
    if records is None:
        return None
    return pd.DataFrame(records)


def get_project_name() -> str:
    """Return the current project name from session storage."""
    return str(app.storage.tab.get("project_name", ""))


def set_project_name(name: str) -> None:
    """Store project name in tab-scoped session."""
    app.storage.tab["project_name"] = name


@functools.cache
def get_workload_options() -> list[dict[str, object]]:
    """Load DRR table and return workload option dicts for UI dropdowns.

    Each dict has keys: category, subcategory, label, drr.
    Result is cached since DRR table is static reference data.
    """
    drr_table = DRRTable.from_csv(DRR_CSV_PATH)
    return [
        {
            "category": entry.category,
            "subcategory": entry.subcategory,
            "label": f"{entry.category} / {entry.subcategory}",
            "drr": entry.ratio,
        }
        for entry in drr_table.entries
    ]
