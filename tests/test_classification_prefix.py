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


def test_description_does_not_match_non_optin_rule() -> None:
    """v8.3.1: description fallback is opt-in. The Oracle rule does NOT
    fire on a description containing 'Oracle' because it isn't an OVA
    annotation signature — protects against backup-tool metadata noise
    (e.g. Veeam annotations) wrongly firing app rules."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("SRV001", "", description="Oracle Database Server")
    # No OS, no name match, no opt-in description match -> Unknown.
    assert result.subcategory != "Oracle"


def test_classification_description_does_not_override() -> None:
    """VM name match takes priority -- description cannot override it."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("SQLPROD01", "", description="Oracle server")
    # "SQL" in vm_name matches Microsoft SQL rule first (priority 103)
    assert result.category == "Database"
    assert result.subcategory == "Microsoft SQL"


def test_classify_dataframe_with_description_column() -> None:
    """classify_dataframe reads vm_description column and passes it to
    classify(). v8.3.1: only opt-in rules consume description; generic
    text in description does NOT fire app rules."""
    df = pd.DataFrame(
        {
            "vm_name": ["SRV001", "DBPROD01", "appliance-01"],
            "os_name": ["", "", ""],
            "vm_description": [
                "Oracle Database",  # generic text — must NOT match Oracle rule
                "General purpose",
                "BeyondTrust Secure Remote Access Appliance",  # opt-in signature
            ],
        }
    )
    registry = RuleRegistry(build_default_rules())
    result = classify_dataframe(df, registry)

    # SRV001 with generic "Oracle Database" description must NOT fire Oracle rule
    assert result.iloc[0]["workload_subcategory"] != "Oracle"
    # DBPROD01 unchanged — generic description, no match
    assert isinstance(result.iloc[1]["workload_category"], str)
    # appliance-01 hits the BeyondTrust opt-in description rule
    assert result.iloc[2]["workload_category"] == "Web Servers"
    assert result.iloc[2]["workload_subcategory"] == "Content included"
