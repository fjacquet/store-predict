"""Tests for the workload classification engine.

Uses real objects and the actual default rule set -- NO mocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)

if TYPE_CHECKING:
    from store_predict.services.drr_table import DRRTable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry() -> RuleRegistry:
    """Convenience: build a registry with the full default rule set."""
    return RuleRegistry(build_default_rules())


# ---------------------------------------------------------------------------
# 1. Rule matching tests (individual patterns)
# ---------------------------------------------------------------------------


class TestRuleMatching:
    """Individual pattern matching tests."""

    def test_sql_substring_match(self) -> None:
        """FR-3.3: CADSRVSQL001 must match SQL rule via substring."""
        result = _registry().classify("CADSRVSQL001", "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL"
        assert result.confidence == "rule_match"

    def test_oracle_match(self) -> None:
        result = _registry().classify("ORACLE-PROD-01", "")
        assert result.category == "Database"
        assert result.subcategory == "Oracle"

    def test_oracle_not_lora(self) -> None:
        """OIK_LORADB should NOT match Oracle ('ORACLE' pattern, not 'ORA')."""
        result = _registry().classify("OIK_LORADB", "Oracle Linux 9 (64-bit)")
        assert not (result.category == "Database" and result.subcategory == "Oracle")

    def test_sap_match(self) -> None:
        result = _registry().classify("SAP-APP-01", "Windows Server 2019")
        assert result.category == "Database"
        assert result.subcategory == "SAP Traditional (R/3 / ECC)"

    def test_sap_not_abac(self) -> None:
        """CIGES-ABAC01 is Abacus ERP, NOT SAP."""
        result = _registry().classify(
            "CIGES-ABAC01",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category == "Virtual Machines"

    def test_sap_not_gisapp(self) -> None:
        """GISAPP contains 'SAP' as substring but is a GIS application server."""
        result = _registry().classify(
            "CIGES-GISAPP",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category != "Database" or "SAP" not in result.subcategory

    def test_exchange_not_ex(self) -> None:
        """CIGES-EXTRANET must NOT match Email (uses 'EXCHANGE', not 'EX')."""
        result = _registry().classify(
            "CIGES-EXTRANET",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category != "Email"

    def test_exchange_match(self) -> None:
        result = _registry().classify("EXCHANGE-01", "")
        assert result.category == "Email"

    def test_citrix_match(self) -> None:
        result = _registry().classify("CITADM-01", "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "VDI"
        assert result.subcategory == "Full Clone / MCS (Citrix)"

    def test_horizon_match(self) -> None:
        result = _registry().classify("HORIZON-POOL01", "")
        assert result.category == "VDI"
        assert result.subcategory == "Instant Clone"

    def test_fortinet_os_match(self) -> None:
        """FortiNet appliances detected via OS field."""
        result = _registry().classify(
            "CIGES-FAZ",
            "FortiAnalyzer-VM64 v7.4.10-build2778 260126 (GA.M)",
        )
        assert result.category == "Logging - Analytics"

    def test_veeam_match(self) -> None:
        result = _registry().classify("VBR-PROXY-01", "")
        assert result.category == "VM Replication"

    def test_web_match(self) -> None:
        result = _registry().classify("WEBSERVER-01", "")
        assert result.category == "Web Servers"

    def test_mongodb_match(self) -> None:
        result = _registry().classify("MONGODB-REPLICA", "")
        assert result.category == "Database"
        assert result.subcategory == "MongoDB"

    def test_postgresql_match(self) -> None:
        result = _registry().classify("PGSQL-PRIMARY", "")
        assert result.category == "Database"
        assert result.subcategory == "PostgreSQL"


# ---------------------------------------------------------------------------
# 2. Priority ordering tests
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    """Verify specific rules beat generic ones."""

    def test_database_before_os_fallback(self) -> None:
        """SQL VM with Windows Server OS -> Database, not Virtual Machines."""
        result = _registry().classify(
            "SQLSERVER-01",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL"

    def test_specific_before_generic(self) -> None:
        """DB rule (priority 101) beats OS fallback (priority 900)."""
        rules = build_default_rules()
        sql_priority = next(r.priority for r in rules if r.name == "Microsoft SQL")
        os_priority = next(r.priority for r in rules if r.name == "Windows Server (OS fallback)")
        assert sql_priority < os_priority


# ---------------------------------------------------------------------------
# 3. OS fallback tests
# ---------------------------------------------------------------------------


class TestOSFallback:
    def test_windows_server_fallback(self) -> None:
        result = _registry().classify(
            "GENERIC-SERVER",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category == "Virtual Machines"
        assert result.confidence == "os_fallback"

    def test_linux_fallback(self) -> None:
        result = _registry().classify("GENERIC-APP", "Ubuntu 22.04")
        assert result.category == "Virtual Machines"
        assert result.confidence == "os_fallback"

    def test_vmware_fallback(self) -> None:
        result = _registry().classify("vCLS-xxx", "VMware Photon CRX")
        assert result.category == "Virtual Machines"
        assert result.confidence == "os_fallback"


# ---------------------------------------------------------------------------
# 4. Default rule test
# ---------------------------------------------------------------------------


def test_default_unknown() -> None:
    """Unmatched VM with empty OS -> Unknown (Reducible), confidence=default."""
    result = _registry().classify("UNKNOWN-VM-001", "")
    assert result.category == "Unknown (Reducible)"
    assert result.subcategory == "Unknown (Reducible)"
    assert result.confidence == "default"


# ---------------------------------------------------------------------------
# 5. Case insensitivity
# ---------------------------------------------------------------------------


def test_case_insensitive() -> None:
    """Lowercase VM name still matches SQL rule."""
    result = _registry().classify("cadsrvsql001", "windows server 2019")
    assert result.category == "Database"
    assert result.subcategory == "Microsoft SQL"


# ---------------------------------------------------------------------------
# 6. classify_dataframe tests
# ---------------------------------------------------------------------------


class TestClassifyDataFrame:
    def test_classify_dataframe_adds_columns(self) -> None:
        """classify_dataframe adds 4 new columns with correct values."""
        df = pd.DataFrame(
            {
                "vm_name": ["CADSRVSQL001", "GENERIC-SVR", "UNKNOWN-001"],
                "os_name": [
                    "Microsoft Windows Server 2019 (64-bit)",
                    "Microsoft Windows Server 2022 (64-bit)",
                    "",
                ],
            }
        )
        result = classify_dataframe(df, _registry())

        # Original unchanged
        assert "vm_name" in result.columns
        assert len(result) == 3

        # New columns exist
        for col in [
            "workload_category",
            "workload_subcategory",
            "classification_rule",
            "classification_confidence",
        ]:
            assert col in result.columns

        # Values correct
        assert result.iloc[0]["workload_category"] == "Database"
        assert result.iloc[1]["workload_category"] == "Virtual Machines"
        assert result.iloc[2]["workload_category"] == "Unknown (Reducible)"

    def test_classify_dataframe_handles_nan_os(self) -> None:
        """NaN os_name does not crash and classifies to default or OS fallback."""
        df = pd.DataFrame(
            {
                "vm_name": ["SOME-VM"],
                "os_name": [None],
            }
        )
        result = classify_dataframe(df, _registry())
        assert result.iloc[0]["workload_category"] is not None

    def test_classify_dataframe_does_not_mutate_input(self) -> None:
        """Input DataFrame must not be modified."""
        df = pd.DataFrame(
            {
                "vm_name": ["SQL-01"],
                "os_name": ["Windows Server 2022"],
            }
        )
        original_cols = list(df.columns)
        _ = classify_dataframe(df, _registry())
        assert list(df.columns) == original_cols


# ---------------------------------------------------------------------------
# 7. Rule consistency tests
# ---------------------------------------------------------------------------


def test_all_rules_have_unique_names() -> None:
    """No duplicate rule names in default rules."""
    rules = build_default_rules()
    names = [r.name for r in rules]
    dupes = [n for n in names if names.count(n) > 1]
    assert len(names) == len(set(names)), f"Duplicate names: {dupes}"


def test_rules_sorted_by_priority() -> None:
    """RuleRegistry sorts rules by priority ascending."""
    registry = _registry()
    priorities = [r.priority for r in registry._rules]
    assert priorities == sorted(priorities)


def test_rule_categories_exist_in_drr(drr_table: DRRTable) -> None:
    """Every rule must reference a valid DRR category/subcategory."""
    drr_categories = {(e.category, e.subcategory) for e in drr_table.entries}
    for rule in build_default_rules():
        key = (rule.category, rule.subcategory)
        assert key in drr_categories, (
            f"Rule '{rule.name}' references ({rule.category}, {rule.subcategory}) "
            f"which does not exist in DRR table"
        )
