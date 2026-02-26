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
        """xxx-ABAC01 is Abacus ERP, NOT SAP."""
        result = _registry().classify(
            "xxx-ABAC01",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category == "Virtual Machines"

    def test_sap_not_gisapp(self) -> None:
        """GISAPP contains 'SAP' as substring but is a GIS application server."""
        result = _registry().classify(
            "xxx-GISAPP",
            "Microsoft Windows Server 2022 (64-bit)",
        )
        assert result.category != "Database" or "SAP" not in result.subcategory

    def test_exchange_not_ex(self) -> None:
        """xxx-EXTRANET must NOT match Email (uses 'EXCHANGE', not 'EX')."""
        result = _registry().classify(
            "xxx-EXTRANET",
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
            "xxx-FAZ",
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
        # vCLS is now matched by the explicit "VMware Infrastructure VMs" rule
        result = _registry().classify("vCLS-xxx", "VMware Photon CRX")
        assert result.category == "Virtual Machines"
        assert result.confidence == "rule_match"


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
            f"Rule '{rule.name}' references ({rule.category}, {rule.subcategory}) which does not exist in DRR table"
        )


# ---------------------------------------------------------------------------
# Encrypted / compressed variant classification
# ---------------------------------------------------------------------------


def test_oracle_tde_classification() -> None:
    """ORACLE-TDE VM names should classify as Oracle - TDE (Encrypted)."""
    result = _registry().classify("PROD-ORACLE-TDE-01", "")
    assert result.subcategory == "Oracle - TDE (Encrypted)"


def test_oracle_hcc_classification() -> None:
    """ORACLE-HCC VM names should classify as Oracle - HCC (App Compressed)."""
    result = _registry().classify("PROD-ORACLE-HCC-01", "")
    assert result.subcategory == "Oracle - HCC (App Compressed)"


def test_oracle_hcc_tde_combined_classification() -> None:
    """ORACLE-HCC-TDE names (both keywords present) → Oracle - HCC + TDE."""
    result = _registry().classify("PROD-ORACLE-HCC-TDE-01", "")
    assert result.subcategory == "Oracle - HCC + TDE"


def test_sql_tde_classification() -> None:
    """SQL-TDE VM names should classify as Microsoft SQL - TDE (Encrypted)."""
    result = _registry().classify("PROD-SQL-TDE-01", "")
    assert result.subcategory == "Microsoft SQL - TDE (Encrypted)"


def test_sql_page_compressed_classification() -> None:
    """SQL-PAGE VM names should classify as Microsoft SQL - Page Compressed."""
    result = _registry().classify("PROD-SQL-PAGE-01", "")
    assert result.subcategory == "Microsoft SQL - Page Compressed"


def test_mongo_encrypted_classification() -> None:
    """MONGO-ENC VM names should classify as MongoDB - Encrypted."""
    result = _registry().classify("PROD-MONGO-ENC-01", "")
    assert result.subcategory == "MongoDB - Encrypted"


def test_commvault_classification() -> None:
    """COMMVAULT VM names should classify as Commvault."""
    result = _registry().classify("BACKUP-COMMVAULT-01", "")
    assert result.category == "VM Replication"
    assert result.subcategory == "Commvault"


def test_ddve_classification() -> None:
    """DDVE VM names should classify as Data Domain Virtual Edition (DDVE)."""
    result = _registry().classify("BACKUP-DDVE-PROD-01", "")
    assert result.category == "VM Replication"
    assert result.subcategory == "Data Domain Virtual Edition (DDVE)"


def test_plain_oracle_unaffected() -> None:
    """Plain ORACLE VMs (no TDE/HCC) still classify as Oracle base."""
    result = _registry().classify("PROD-ORACLE-DB-01", "")
    assert result.subcategory == "Oracle"


def test_plain_sql_unaffected() -> None:
    """Plain SQL VMs (no TDE/compress) still classify as Microsoft SQL base."""
    result = _registry().classify("PROD-SQL-DB-01", "")
    assert result.subcategory == "Microsoft SQL"


# ---------------------------------------------------------------------------
# LiveOptics-driven classification improvements
# ---------------------------------------------------------------------------


class TestLiveOpticsImprovements:
    """Tests for patterns added from LiveOptics 1483-VM analysis."""

    def test_windows_desktop_os_fallback_vdi(self) -> None:
        """Windows 10/11 OS → VDI Linked Clone (not Virtual Machines)."""
        result = _registry().classify("GENERIC-PC-042", "Microsoft Windows 11 (64-bit)")
        assert result.category == "VDI"
        assert result.subcategory == "Linked Clone / PVS (Citrix)"
        assert result.confidence == "os_fallback"

    def test_generic_vdi_keyword(self) -> None:
        """VM name containing VDI → VDI category."""
        result = _registry().classify("VDIPOOL-01", "")
        assert result.category == "VDI"
        assert result.subcategory == "Linked Clone / PVS (Citrix)"
        assert result.confidence == "rule_match"

    def test_rds_vdi(self) -> None:
        """RDS as word boundary → VDI (Remote Desktop Services)."""
        result = _registry().classify("vsmrdsjenov", "")
        assert result.category == "VDI"

    def test_desktop_vdi(self) -> None:
        """VM name containing DESKTOP → VDI."""
        result = _registry().classify("DESKTOP-POOL-03", "")
        assert result.category == "VDI"
        assert result.confidence == "rule_match"

    def test_loginvsi_vdi(self) -> None:
        """LoginVSI (VDI benchmarking tool) → VDI."""
        result = _registry().classify("LOGINVSI-DC1", "")
        assert result.category == "VDI"

    def test_uag_vdi(self) -> None:
        """UAG (Unified Access Gateway) → VDI."""
        result = _registry().classify("UAGDC1v25-06", "")
        assert result.category == "VDI"

    def test_tkg_containers(self) -> None:
        """TKG (Tanzu Kubernetes Grid) → Containers."""
        result = _registry().classify("vsltkg-dev-controlplane", "")
        assert result.category == "Containers"

    def test_photon_kube_containers(self) -> None:
        """photon-*-kube pattern → Containers (Tanzu node images)."""
        result = _registry().classify("photon-5-kube-v1.31.9", "")
        assert result.category == "Containers"

    def test_harbor_containers(self) -> None:
        """Harbor (container registry) → Containers."""
        result = _registry().classify("vslharbor1", "")
        assert result.category == "Containers"

    def test_exchg_email(self) -> None:
        """EXCHG abbreviation → Email."""
        result = _registry().classify("vsmexchgn01", "")
        assert result.category == "Email"

    def test_sharepoint_abbreviations(self) -> None:
        """SharePoint abbreviations (SPBE, SPFE, SPOWA) → File Content Servers."""
        for vm_name in ("vsmspbe1", "vsm22spfe1", "vsm22spowa1"):
            result = _registry().classify(vm_name, "")
            assert result.category == "File", f"{vm_name} should be File, got {result.category}"
            assert result.subcategory == "Content Servers (Git, Sharepoint)", (
                f"{vm_name} subcategory mismatch: {result.subcategory}"
            )

    def test_logstash_logging(self) -> None:
        """Logstash → Logging - Analytics."""
        result = _registry().classify("vsllogstashn1", "")
        assert result.category == "Logging - Analytics"

    def test_kibana_logging(self) -> None:
        """Kibana → Logging - Analytics."""
        result = _registry().classify("KIBANA-01", "")
        assert result.category == "Logging - Analytics"


# ---------------------------------------------------------------------------
# 8. Citrix PVS / VMware infrastructure patterns (ESB VDI use case)
# ---------------------------------------------------------------------------


class TestCitrixPVSAndVMwareInfra:
    """Explicit patterns added after analysis of real ESB VDI customer data."""

    def test_cp_replica_is_pvs(self) -> None:
        """Citrix PVS linked-clone replicas (cp-replica-<UUID>) -> VDI Linked Clone."""
        result = _registry().classify(
            "cp-replica-0ac294e6-23f0-4b9a-8931-5e8a496e493f",
            "Microsoft Windows 10 (64-bit)",
        )
        assert result.category == "VDI"
        assert result.subcategory == "Linked Clone / PVS (Citrix)"
        assert result.confidence == "rule_match"

    def test_cp_template_is_pvs(self) -> None:
        """Citrix PVS templates (cp-template-<UUID>) -> VDI Linked Clone."""
        result = _registry().classify(
            "cp-template-77c19479-64f5-4e5d-b798-3961504ffc28",
            "Microsoft Windows 10 (64-bit)",
        )
        assert result.category == "VDI"
        assert result.subcategory == "Linked Clone / PVS (Citrix)"
        assert result.confidence == "rule_match"

    def test_mst_w10_is_pvs_master(self) -> None:
        """PVS master target device images (MST-W10-*) -> VDI Linked Clone."""
        result = _registry().classify(
            "MST-W10-STD-DAT-20240828",
            "Microsoft Windows 10 (64-bit)",
        )
        assert result.category == "VDI"
        assert result.subcategory == "Linked Clone / PVS (Citrix)"
        assert result.confidence == "rule_match"

    def test_vcls_is_vmware_infra(self) -> None:
        """VMware Cluster Services VMs (vCLS-<UUID>) -> Virtual Machines via rule."""
        result = _registry().classify(
            "vCLS-996323af-736c-4d6e-8d16-5d615133f1f3",
            "VMware Photon OS (64-bit)",
        )
        assert result.category == "Virtual Machines"
        assert result.confidence == "rule_match"

    def test_vxrail_manager_is_vmware_infra(self) -> None:
        """Dell VxRail Manager appliance -> Virtual Machines via rule."""
        result = _registry().classify(
            "VxRail Manager",
            "SUSE Linux Enterprise 15 (64-bit)",
        )
        assert result.category == "Virtual Machines"
        assert result.confidence == "rule_match"
