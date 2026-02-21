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
