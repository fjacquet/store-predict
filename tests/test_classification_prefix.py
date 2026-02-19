"""Tests for company prefix stripping and description-based classification."""

from __future__ import annotations

import pandas as pd

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
    strip_company_prefix,
)

# ---------------------------------------------------------------------------
# strip_company_prefix tests
# ---------------------------------------------------------------------------


def test_strip_company_prefix_basic() -> None:
    """Pattern anchored to start strips the prefix."""
    result = strip_company_prefix("ACME-SQLPROD01", [r"^ACME[-_]"])
    assert result == "SQLPROD01"


def test_strip_company_prefix_no_match() -> None:
    """When no pattern matches, original name is returned unchanged."""
    result = strip_company_prefix("SQLPROD01", [r"^ACME[-_]"])
    assert result == "SQLPROD01"


def test_strip_company_prefix_case_insensitive() -> None:
    """Matching is case-insensitive."""
    result = strip_company_prefix("acme-SQLPROD01", [r"^ACME[-_]"])
    assert result == "SQLPROD01"


def test_strip_company_prefix_multiple_patterns() -> None:
    """Only the first matching pattern is applied."""
    result = strip_company_prefix(
        "CORP_SQLPROD01",
        [r"^ACME[-_]", r"^CORP[-_]"],
    )
    assert result == "SQLPROD01"


def test_strip_company_prefix_empty_list() -> None:
    """Empty patterns list returns original name unchanged."""
    result = strip_company_prefix("ACME-SQLPROD01", [])
    assert result == "ACME-SQLPROD01"


def test_strip_company_prefix_delimiter_anchored() -> None:
    """Pattern requiring delimiter does NOT match when no delimiter present."""
    result = strip_company_prefix("ACMEFILE01", [r"^ACME[-_]"])
    assert result == "ACMEFILE01"


# ---------------------------------------------------------------------------
# Description-aware classification tests
# ---------------------------------------------------------------------------


def test_classification_with_description() -> None:
    """Description field acts as fallback for vm_name_patterns."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("SRV001", "", description="Oracle Database Server")
    assert result.category == "Database"
    assert result.subcategory == "Oracle"


def test_classification_description_does_not_override() -> None:
    """VM name match takes priority -- description cannot override it."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("SQLPROD01", "", description="Oracle server")
    # "SQL" in vm_name matches Microsoft SQL rule first (priority 103)
    assert result.category == "Database"
    assert result.subcategory == "Microsoft SQL"


def test_classify_dataframe_with_description_column() -> None:
    """classify_dataframe reads vm_description column and uses it for matching."""
    df = pd.DataFrame(
        {
            "vm_name": ["SRV001", "DBPROD01"],
            "os_name": ["", ""],
            "vm_description": ["Oracle Database", "General purpose"],
        }
    )
    registry = RuleRegistry(build_default_rules())
    result = classify_dataframe(df, registry)

    # SRV001 with description "Oracle Database" should match Oracle
    assert result.iloc[0]["workload_category"] == "Database"
    assert result.iloc[0]["workload_subcategory"] == "Oracle"

    # DBPROD01 with generic description falls to default
    # (DB2 won't match since "DB" alone isn't a pattern)
    assert isinstance(result.iloc[1]["workload_category"], str)
