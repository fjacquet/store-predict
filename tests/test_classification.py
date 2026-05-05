"""Tests for the workload classification engine.

Uses real objects and the actual default rule set -- NO mocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

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

    def test_db2_word_bounded_match(self) -> None:
        """Real DB2 VMs (DB2 at word boundary) still classify as DB2."""
        result = _registry().classify("DB2-PROD-01", "")
        assert result.category == "Database"
        assert result.subcategory == "DB2"

    def test_db2_rejects_storage_array_hostname(self) -> None:
        """DB2500 / DB2700 storage-array hostnames must NOT classify as DB2."""
        for name in ("DB2500-CTL", "prod-DB2700"):
            result = _registry().classify(name, "")
            assert result.subcategory != "DB2", f"{name} wrongly matched DB2"


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


# ---------------------------------------------------------------------------
# 9. Backup/Replication tool classification (Task 1: Veritas/NetBackup + BACKUP)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vm_name, expected_category",
    [
        ("Veritas-Media-01", "VM Replication"),
        ("NetBackup-Master", "VM Replication"),
        ("NBU-Client-03", "VM Replication"),
        ("Backup-Server-01", "File"),
        ("veeam-backup-01", "VM Replication"),  # priority 300 wins over 360
    ],
)
def test_backup_classification(vm_name: str, expected_category: str) -> None:
    """Veritas/NetBackup VMs -> VM Replication; generic BACKUP VMs -> File.

    veeam-backup-01 must stay as VM Replication (priority 300 beats 360).
    """
    result = _registry().classify(vm_name, "")
    assert result.category == expected_category, (
        f"Expected {vm_name!r} -> {expected_category!r}, got {result.category!r} (rule={result.rule_name!r})"
    )


# ---------------------------------------------------------------------------
# 10. Monitoring tool classification (Task 2: Nagios, SolarWinds, Icinga, etc.)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vm_name, expected_category",
    [
        ("Nagios-Monitor", "Logging - Analytics"),
        ("Icinga-Server", "Logging - Analytics"),
        ("SolarWinds-NPM", "Logging - Analytics"),
        ("LibreNMS-Poller", "Logging - Analytics"),
        ("OpenNMS-Core", "Logging - Analytics"),
    ],
)
def test_monitoring_classification(vm_name: str, expected_category: str) -> None:
    """Network monitoring tools must classify to Logging - Analytics."""
    result = _registry().classify(vm_name, "")
    assert result.category == expected_category, (
        f"Expected {vm_name!r} -> {expected_category!r}, got {result.category!r} (rule={result.rule_name!r})"
    )


@pytest.mark.parametrize(
    "vm_name, expected_category",
    [
        ("Redis-Cache-01", "Database"),
    ],
)
def test_redis_classification(vm_name: str, expected_category: str) -> None:
    """Redis VMs must classify to Database (MySQL/NoSQL rule)."""
    result = _registry().classify(vm_name, "")
    assert result.category == expected_category, (
        f"Expected {vm_name!r} -> {expected_category!r}, got {result.category!r} (rule={result.rule_name!r})"
    )


# ---------------------------------------------------------------------------
# Folder-aware classification (added v8.3+ from real customer file analysis)
# ---------------------------------------------------------------------------


class TestFolderAwareClassification:
    """Rules that consume the vm_folder signal."""

    def test_sap_hana_by_folder_and_name(self) -> None:
        """saphdb01 in /SAP_Dina/HanaDB/PROD must classify as SAP HANA(S4)."""
        result = _registry().classify(
            "sdsaphdb01",
            "SUSE Linux Enterprise 15 (64-bit)",
            folder="/DC_01/Guest VMs/SAP_Dina/HanaDB/PROD",
        )
        assert result.category == "Database"
        assert result.subcategory == "SAP HANA(S4)"
        assert result.rule_name == "SAP HANA HDB"

    def test_sap_hana_qualifier_blocks_generic_sap(self) -> None:
        """HANA HDB rule (109) must beat the generic SAP folder rule (175)."""
        result = _registry().classify(
            "sdsaphdb04",
            "",
            folder="/DC_01/Guest VMs/SAP_Dina/HanaDB/DEV",
        )
        assert result.subcategory == "SAP HANA(S4)"
        assert result.rule_name != "SAP general (folder)"

    def test_sap_general_by_folder(self) -> None:
        """Non-HANA VMs in a /SAP_*/ folder route to SAP Traditional."""
        result = _registry().classify(
            "sdsapcrm11",
            "Microsoft Windows Server 2019 (64-bit)",
            folder="/DC_01/Guest VMs/SAP_Dina/Windows/DEV",
        )
        assert result.category == "Database"
        assert result.subcategory == "SAP Traditional (R/3 / ECC)"

    def test_exchange_by_folder(self) -> None:
        """A VM in /EXCH/* routes to Email."""
        result = _registry().classify(
            "spex01",
            "Microsoft Windows Server 2019 (64-bit)",
            folder="/DC_PREPROD/Guest VMs/EXCH",
        )
        assert result.category == "Email"
        assert result.rule_name == "Microsoft Exchange (folder)"

    def test_cisco_ucm_by_name(self) -> None:
        """CUCM hostname routes to Web Servers / Content included."""
        result = _registry().classify("cucm-pub01", "")
        assert result.category == "Web Servers"
        assert result.subcategory == "Content included"
        assert result.rule_name == "Cisco Unified Communications"

    def test_cisco_uc_by_folder(self) -> None:
        """A VM in /UC routes to Cisco UC even with a generic name."""
        result = _registry().classify(
            "app1",
            "Microsoft Windows Server 2019 (64-bit)",
            folder="/DC_PREPROD/Guest VMs/UC",
        )
        assert result.category == "Web Servers"
        assert result.rule_name == "Cisco Unified Communications"

    def test_nutanix_cvm_by_name_and_folder(self) -> None:
        """Nutanix CVM routes to DDVE (DRR=1.0)."""
        result = _registry().classify(
            "NTNX-19SM5A510097-A-CVM",
            "CentOS 7 (64-bit)",
            folder="/DC_01/NTNX CVMs/SEC101",
        )
        assert result.category == "VM Replication"
        assert result.subcategory == "Data Domain Virtual Edition (DDVE)"
        assert result.rule_name == "Nutanix CVM"

    def test_nutanix_cvm_does_not_overmatch_bare_cvm(self) -> None:
        """A VM named 'cvm-bench' (no NTNX prefix, no /NTNX CVMs/ folder) must
        NOT match the Nutanix rule — bare 'cvm' is too generic."""
        result = _registry().classify(
            "cvm-bench",
            "Ubuntu 22.04 (64-bit)",
            folder="/DC_01/Guest VMs/Tests",
        )
        assert result.subcategory != "Data Domain Virtual Edition (DDVE)"

    def test_domain_controller_by_name(self) -> None:
        """DC hostnames stay in Virtual Machines (DRR=5)."""
        result = _registry().classify(
            "spaddc01",
            "Microsoft Windows Server 2019 (64-bit)",
        )
        # spaddc01 contains AADC pattern \bAADC?\d* — actually \b is between sp/a (letter/letter)
        # so this case relies on folder. Use a clear DC-tokenised name instead:
        result = _registry().classify(
            "PROD-DC01",
            "Microsoft Windows Server 2019 (64-bit)",
        )
        assert result.category == "Virtual Machines"
        assert result.rule_name == "Domain Controller / AAD"

    def test_ipam_by_folder(self) -> None:
        """IPAM folder routes to Web Servers / Content included."""
        result = _registry().classify(
            "spipam01",
            "Microsoft Windows Server 2019 (64-bit)",
            folder="/DC_PREPROD/Guest VMs/IPAM",
        )
        assert result.category == "Web Servers"
        assert result.subcategory == "Content included"
        assert result.rule_name == "IPAM"

    def test_identity_nevis_by_folder(self) -> None:
        """NEVIS folder routes to Web Servers / Content included."""
        result = _registry().classify(
            "spnevisauth01",
            "Linux",
            folder="/DC_PREPROD/Guest VMs/NEVIS",
        )
        assert result.category == "Web Servers"
        assert result.rule_name == "Identity / Auth (Nevis)"

    def test_powerflex_sds_to_containers(self) -> None:
        """PowerFlex SDS management VMs route to Containers (k8s-based)."""
        result = _registry().classify(
            "kppflexmp11",
            "VMware Photon CRX (64-bit)",
            folder="/DC_01/Guest VMs/PowerFlex",
        )
        assert result.category == "Containers"
        assert result.subcategory == "Kubernetes, OpenShift, Docker, Tanzu, etc"

    def test_description_signature_beyondtrust(self) -> None:
        """Description-only signature: BeyondTrust appliance routes to Web Servers."""
        result = _registry().classify(
            "appliance-01",
            "",
            description="BeyondTrust Secure Remote Access Appliance",
        )
        assert result.category == "Web Servers"
        assert result.subcategory == "Content included"
        assert result.confidence == "rule_match"

    def test_description_signature_nutanix(self) -> None:
        """Description signature 'Nutanix Controller VM' alone routes to DDVE."""
        result = _registry().classify(
            "host-x",
            "",
            description="CentOS based Nutanix Controller VM",
        )
        assert result.subcategory == "Data Domain Virtual Edition (DDVE)"
        assert result.confidence == "rule_match"

    def test_folder_does_not_override_specific_db_rule(self) -> None:
        """A MSSQL VM in a /SAP_*/ folder must still classify as Microsoft SQL
        because the SQL name rule (priority 103) outranks SAP general (175)."""
        result = _registry().classify(
            "MSSQL-PROD01",
            "Microsoft Windows Server 2019 (64-bit)",
            folder="/DC_01/Guest VMs/SAP_Dina/Windows/PROD",
        )
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL"


# ---------------------------------------------------------------------------
# v8.3.1 hotfix: description-fallback over-classification
# ---------------------------------------------------------------------------


class TestDescriptionFallbackOptIn:
    """Regression tests for the v8.3.1 hotfix where Veeam backup metadata in
    vCenter Annotation falsely fired the Veeam rule on every backed-up VM."""

    VEEAM_BACKUP_DESC = (
        "Last backup: [06.01.2026 21:20:13]; "
        "Veeam server: [sphfrbkp01]; "
        "Job: [HFR - Gold - Standard - DC1]; "
        "Repository: [sobr-hfr-immutable-dc1]"
    )

    def test_veeam_description_does_not_overmatch_generic_app(self) -> None:
        """A generic Windows app VM whose Annotation contains 'Veeam' (because
        Veeam writes its backup log there) must NOT classify as VM Replication."""
        result = _registry().classify(
            "SPHFRAPP01",
            "Microsoft Windows Server 2022 (64-bit)",
            description=self.VEEAM_BACKUP_DESC,
        )
        assert result.category != "VM Replication", (
            f"Veeam description over-matched: {result.rule_name!r} → {result.subcategory!r}"
        )
        assert result.confidence == "os_fallback"

    def test_veeam_description_does_not_overmatch_exchange(self) -> None:
        """SPHFREXCH01 with a Veeam backup annotation must classify as Email,
        not VM Replication."""
        result = _registry().classify(
            "SPHFREXCH01",
            "Microsoft Windows Server 2022 (64-bit)",
            description=self.VEEAM_BACKUP_DESC,
        )
        assert result.category == "Email"
        assert result.rule_name == "Email"

    def test_exchange_exch_short_token(self) -> None:
        """The customer's EXCH naming convention (no full EXCHANGE) must
        match Email — covers SPHFREXCH01-04 / SPRFSMEXCH01-02."""
        for name in ("SPHFREXCH01", "SPRFSMEXCH02"):
            result = _registry().classify(name, "")
            assert result.category == "Email", f"{name!r} not classified as Email: {result.subcategory!r}"

    def test_description_signature_beyondtrust_still_works(self) -> None:
        """Opt-in regression: BeyondTrust rule must still fire via description
        because we set match_description=True on it."""
        result = _registry().classify(
            "appliance-01",
            "",
            description="BeyondTrust Secure Remote Access Appliance",
        )
        assert result.category == "Web Servers"
        assert result.subcategory == "Content included"
        assert result.confidence == "rule_match"

    def test_description_signature_nutanix_still_works(self) -> None:
        """Opt-in regression: Nutanix CVM rule still matches via description
        signature 'Nutanix Controller VM'."""
        result = _registry().classify(
            "host-x",
            "",
            description="CentOS based Nutanix Controller VM",
        )
        assert result.subcategory == "Data Domain Virtual Edition (DDVE)"
        assert result.confidence == "rule_match"


# ---------------------------------------------------------------------------
# v8.3.2 manual coverage extensions
# ---------------------------------------------------------------------------


class TestV832Extensions:
    """Manual rule additions identified on the Jan 2026 customer file."""

    @pytest.mark.parametrize(
        "vm_name",
        ["SPHFRCARDIO21", "SDRFSMORAMED01", "SPHFREMEDISTA01", "SPHFREASYDOSE01", "SPHFRCODMED01", "SPHFRHEMA04"],
    )
    def test_healthcare_specialty_apps(self, vm_name: str) -> None:
        """Cardiology / pharma / clinical apps route to HealthCare EMR/EHR."""
        result = _registry().classify(vm_name, "Microsoft Windows Server 2022 (64-bit)")
        assert result.category == "HealthCare"
        assert result.subcategory == "EMR/EHR (Epic, McKesson)"

    def test_sharepoint_app_role(self) -> None:
        """SharePoint App role server (SPAPP) routes to File / Content Servers."""
        result = _registry().classify("SPHFRSPAPP11", "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "File"
        assert result.subcategory == "Content Servers (Git, Sharepoint)"

    def test_sharepoint_wfe(self) -> None:
        """SharePoint Web Front End (SPWFE) routes to File / Content Servers."""
        result = _registry().classify("SPHFRSPWFE12", "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "File"
        assert result.subcategory == "Content Servers (Git, Sharepoint)"

    @pytest.mark.parametrize("vm_name", ["SPHFRDFS01", "SPRFSMDFS01"])
    def test_dfs_distributed_file_system(self, vm_name: str) -> None:
        """Microsoft DFS namespace/replication servers route to File."""
        result = _registry().classify(vm_name, "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "File"
        assert result.subcategory == "General Purpose"

    def test_dfs_does_not_match_pdfs(self) -> None:
        """The DFS pattern requires DFS<digit/separator> — must not catch PDF
        servers or other false positives."""
        result = _registry().classify(
            "PDFSERVER01",
            "Microsoft Windows Server 2019 (64-bit)",
        )
        assert result.subcategory != "General Purpose"

    def test_wsus_routes_to_web_servers(self) -> None:
        """WSUS (already-compressed Microsoft patches) routes to Web Servers /
        Content included (DRR=1.5)."""
        result = _registry().classify("SPHFRWSUS01", "Microsoft Windows Server 2022 (64-bit)")
        assert result.category == "Web Servers"
        assert result.subcategory == "Content included"
        assert result.rule_name == "WSUS"

    @pytest.mark.parametrize(
        "vm_name",
        ["SDHFRDWHPYT01", "SPHFRDWHTAB02", "SPRFSMDWHCUBE11", "SPHFRPDMSDWH10"],
    )
    def test_dwh_routes_to_sql_page_compressed(self, vm_name: str) -> None:
        """Data Warehouse VMs (DWH token) route to SQL Page Compressed
        (DRR=2.5) — DWH workloads typically use SQL columnstore/page
        compression."""
        result = _registry().classify(vm_name, "Microsoft Windows Server 2022 (64-bit)")
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL - Page Compressed"


# ---------------------------------------------------------------------------
# v9.0.0: 3 missed patterns + size-aware reroute for unknown VMs
# ---------------------------------------------------------------------------


class TestV900PatternsAndSizeAware:
    """v9.0.0 closes the biggest sizing risk in the tool: 64% of a real
    customer file fell to the generic Virtual Machines bucket (DRR=5) but
    held 330 TiB of provisioned data. Size-aware reroute moves unknown VMs
    ≥100 GiB to a new 'Large data-bearing' subcategory at DRR=2.5.

    Plus 3 patterns identified during the same audit: INSIGHTIQ → PostgreSQL,
    SECDB → Microsoft SQL, FORTIA<digit> → Logging/FortiNet.
    """

    def test_insightiq_routes_postgresql(self) -> None:
        """Dell PowerScale InsightIQ ships with embedded PostgreSQL."""
        result = _registry().classify("SPHFRINSIGHTIQ01", "")
        assert result.category == "Database"
        assert result.subcategory == "PostgreSQL"

    def test_secdb_routes_microsoft_sql(self) -> None:
        """SECDB customer convention for Security Database (Microsoft SQL)."""
        result = _registry().classify("SPHFRSECDB01", "")
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL"

    def test_fortiadc_short_form(self) -> None:
        """FORTIA<digit> short-host convention catches FortiADC appliances."""
        result = _registry().classify("SPHFRFORTIA01", "")
        assert result.category == "Logging - Analytics"
        assert result.subcategory == "FortiNet, Elastic Search, Splunk, ELK, etc"

    def test_fortiadc_long_form(self) -> None:
        """Full 'FORTIADC' substring also matches the rule."""
        result = _registry().classify("prod-fortiadc-01", "")
        assert result.category == "Logging - Analytics"

    def test_small_unknown_vm_stays_generic(self) -> None:
        """50 GiB Windows Server with no name match stays in generic VM bucket."""
        df = pd.DataFrame(
            {
                "vm_name": ["GENERIC-APP-50G"],
                "os_name": ["Microsoft Windows Server 2022 (64-bit)"],
                "provisioned_mib": [50 * 1024],
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_subcategory"] == "VMware / Hyper-V / KVM - No Database, File nor Email"
        assert out.iloc[0]["classification_confidence"] == "os_fallback"

    def test_large_unknown_vm_reroutes_to_large_databearing(self) -> None:
        """200 GiB Windows Server unknown VM reroutes to Large data-bearing."""
        df = pd.DataFrame(
            {
                "vm_name": ["GENERIC-APP-200G"],
                "os_name": ["Microsoft Windows Server 2022 (64-bit)"],
                "provisioned_mib": [200 * 1024],
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_category"] == "Virtual Machines"
        assert out.iloc[0]["workload_subcategory"] == "Large data-bearing (>100 GiB unknown)"
        assert out.iloc[0]["classification_rule"] == "Large generic (>=100 GiB)"
        # Confidence preserves provenance (still os_fallback, not rule_match).
        assert out.iloc[0]["classification_confidence"] == "os_fallback"

    def test_large_default_unknown_vm_reroutes(self) -> None:
        """500 GiB VM with no name match AND no OS match (confidence=default)
        also reroutes to Large data-bearing."""
        df = pd.DataFrame(
            {
                "vm_name": ["UNCLASSIFIABLE"],
                "os_name": [""],
                "provisioned_mib": [500 * 1024],
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_subcategory"] == "Large data-bearing (>100 GiB unknown)"
        assert out.iloc[0]["classification_confidence"] == "default"

    def test_large_specific_app_not_rerouted(self) -> None:
        """A 1 TiB Oracle VM keeps its Database/Oracle classification —
        rule_match is never overridden by size-based reroute."""
        df = pd.DataFrame(
            {
                "vm_name": ["oracle-prod-01"],
                "os_name": ["Oracle Linux 9 (64-bit)"],
                "provisioned_mib": [1024 * 1024],  # 1 TiB
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_category"] == "Database"
        assert out.iloc[0]["workload_subcategory"] == "Oracle"
        assert out.iloc[0]["classification_confidence"] == "rule_match"

    def test_threshold_boundary_exact_100gib(self) -> None:
        """100 GiB exactly is the threshold — must reroute (≥, inclusive)."""
        df = pd.DataFrame(
            {
                "vm_name": ["GENERIC-APP-100G"],
                "os_name": ["Microsoft Windows Server 2019 (64-bit)"],
                "provisioned_mib": [100 * 1024],
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_subcategory"] == "Large data-bearing (>100 GiB unknown)"

    def test_classify_dataframe_without_provisioned_column(self) -> None:
        """When provisioned_mib column is absent, no reroute happens (no crash)."""
        df = pd.DataFrame(
            {
                "vm_name": ["GENERIC-APP-LARGE"],
                "os_name": ["Microsoft Windows Server 2019 (64-bit)"],
            }
        )
        out = classify_dataframe(df, _registry())
        assert out.iloc[0]["workload_subcategory"] == "VMware / Hyper-V / KVM - No Database, File nor Email"
