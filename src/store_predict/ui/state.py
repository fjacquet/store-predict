"""Per-tab session state helpers for DataFrame serialization and project metadata."""

from __future__ import annotations

import functools
from typing import Any

import pandas as pd
from nicegui import app

from store_predict.config import DRR_CSV_PATH, StorageModel
from store_predict.pipeline.llm_classifier import RuleSuggestion
from store_predict.services.drr_table import DRRTable


def save_session_data(df: pd.DataFrame, project_name: str) -> None:
    """Store classified DataFrame and project name in tab-scoped session.

    NaN values are converted to None for JSON serialization compatibility.
    """
    records: list[dict[str, object]] = df.to_dict(orient="records")  # type: ignore[assignment]
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


def clear_session_data() -> None:
    """Remove uploaded VM data and project name from tab-scoped session.

    Call this before processing a new upload so stale data cannot bleed
    into the review page if the new upload fails partway through.
    """
    app.storage.tab.pop("vm_data", None)
    app.storage.tab.pop("project_name", None)
    app.storage.tab.pop("selected_datacenters", None)
    app.storage.tab.pop("selected_clusters", None)


def save_scope_selection(
    datacenters: list[str] | None,
    clusters: list[str] | None,
) -> None:
    """Persist datacenter/cluster scope selection in tab-scoped session.

    Pass None or empty list to indicate "all" (no filtering).
    """
    app.storage.tab["selected_datacenters"] = datacenters or []
    app.storage.tab["selected_clusters"] = clusters or []


def get_scope_selection() -> tuple[list[str], list[str]]:
    """Return (selected_datacenters, selected_clusters) from session.

    Empty list means "all" (no filtering applied).
    """
    dcs: list[str] = app.storage.tab.get("selected_datacenters", [])
    clusters: list[str] = app.storage.tab.get("selected_clusters", [])
    return dcs, clusters


def load_filtered_session_data() -> pd.DataFrame | None:
    """Load session DataFrame filtered by datacenter/cluster scope selection.

    Returns None if no data uploaded yet. If no scope is selected
    (empty lists), returns the full DataFrame unfiltered.
    """
    df = load_session_data()
    if df is None:
        return None

    selected_dcs, selected_clusters = get_scope_selection()

    if selected_dcs and "datacenter" in df.columns:
        df = df[df["datacenter"].isin(selected_dcs)]

    if selected_clusters and "cluster" in df.columns:
        df = df[df["cluster"].isin(selected_clusters)]

    return df


def save_filtered_rows(row_data: list[dict[str, Any]], project_name: str) -> None:
    """Merge edited rows (potentially a filtered subset) back into full session data.

    Uses row_index as the join key. Rows not present in row_data are kept unchanged.
    """
    full_records: list[dict[str, object]] | None = app.storage.tab.get("vm_data")
    if full_records is None:
        # No existing data — just save directly
        save_session_data(pd.DataFrame(row_data), project_name)
        return

    # Build index for fast lookup
    edited_by_idx: dict[int, dict[str, Any]] = {int(r.get("row_index", -1)): r for r in row_data}

    # Merge changes into full records
    for full_row in full_records:
        idx = int(full_row.get("row_index", -1))  # type: ignore[arg-type]
        if idx in edited_by_idx:
            edited = edited_by_idx[idx]
            for key in ("workload_category", "workload_subcategory", "drr"):
                if key in edited:
                    full_row[key] = edited[key]

    app.storage.tab["vm_data"] = full_records
    app.storage.tab["project_name"] = project_name


def get_project_name() -> str:
    """Return the current project name from session storage."""
    return str(app.storage.tab.get("project_name", ""))


def set_project_name(name: str) -> None:
    """Store project name in tab-scoped session."""
    app.storage.tab["project_name"] = name


def get_storage_model() -> StorageModel:
    """Return the selected storage model from session (default: PowerStore)."""
    val = app.storage.tab.get("storage_model", StorageModel.POWERSTORE)
    return StorageModel(val)


def set_storage_model(model: StorageModel) -> None:
    """Persist the selected storage model in tab-scoped session."""
    app.storage.tab["storage_model"] = model.value


def get_llm_ui_enabled() -> bool:
    """Return per-session AI classification preference (default True)."""
    return bool(app.storage.tab.get("llm_ui_enabled", True))


def set_llm_ui_enabled(val: bool) -> None:
    """Persist the AI classification toggle state in tab-scoped session."""
    app.storage.tab["llm_ui_enabled"] = val


def save_rule_suggestions(suggestions: list[RuleSuggestion]) -> None:
    """Persist LLM rule suggestions in tab-scoped session storage."""
    app.storage.tab["rule_suggestions"] = [
        {
            "keyword": s.keyword,
            "category": s.category,
            "subcategory": s.subcategory,
            "vm_examples": s.vm_examples,
            "count": s.count,
        }
        for s in suggestions
    ]


def load_rule_suggestions() -> list[RuleSuggestion]:
    """Retrieve LLM rule suggestions from session storage."""
    raw: list[dict[str, Any]] = app.storage.tab.get("rule_suggestions", [])
    return [
        RuleSuggestion(
            keyword=r["keyword"],
            category=r["category"],
            subcategory=r["subcategory"],
            vm_examples=r.get("vm_examples", []),
            count=r.get("count", 1),
        )
        for r in raw
    ]


@functools.cache
def get_workload_options() -> list[dict[str, object]]:
    """Load DRR table and return workload option dicts for UI dropdowns.

    Each dict has keys: category, subcategory, label, drr.
    Result is cached since DRR table is static reference data.
    """
    drr_table = DRRTable.from_csv(DRR_CSV_PATH)
    return sorted(
        [
            {
                "category": entry.category,
                "subcategory": entry.subcategory,
                "label": f"{entry.category} / {entry.subcategory}",
                "drr": entry.ratio,
            }
            for entry in drr_table.entries
        ],
        key=lambda e: str(e["label"]),
    )
