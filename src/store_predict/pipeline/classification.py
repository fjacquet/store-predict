"""Workload classification engine for VM-to-DRR category mapping.

Rules-based pattern matching on VM name and OS field to assign each VM
to a DRR workload category.  Rules are evaluated in priority order
(lower number = higher priority); first match wins.

No DRR ratios are embedded here -- rules reference category/subcategory
pairs only.  The DRRTable service provides ratio lookup separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from store_predict.config import COMPANY_PREFIX_PATTERNS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_company_prefix(vm_name: str, patterns: list[str]) -> str:
    """Strip a company prefix from *vm_name* using the first matching pattern.

    Each pattern is a regex string (typically start-anchored, e.g. ``r"^ACME[-_]"``).
    Matching is case-insensitive.  Only the first matching pattern is applied.
    """
    for pattern in patterns:
        stripped = re.sub(pattern, "", vm_name, count=1, flags=re.IGNORECASE)
        if stripped != vm_name:
            return stripped
    return vm_name


def _patterns(*keywords: str) -> tuple[re.Pattern[str], ...]:
    """Compile case-insensitive literal substring patterns.

    Uses ``re.escape`` so characters like ``+`` or ``.`` are safe.
    """
    return tuple(re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords)


def _regex_patterns(*expressions: str) -> tuple[re.Pattern[str], ...]:
    """Compile case-insensitive regex patterns (alternation, word boundaries, etc.)."""
    return tuple(re.compile(expr, re.IGNORECASE) for expr in expressions)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationRule:
    """A single classification rule for matching VMs to workload categories."""

    name: str
    category: str
    subcategory: str
    priority: int
    vm_name_patterns: tuple[re.Pattern[str], ...] = ()
    os_patterns: tuple[re.Pattern[str], ...] = ()
    match_mode: str = "any"  # "any" = OR, "all" = AND

    def matches(self, vm_name: str, os_name: str, description: str = "") -> bool:
        """Return *True* if this rule matches the given VM name / OS.

        When *description* is non-empty and no ``vm_name_patterns`` match
        against *vm_name*, the patterns are also checked against *description*
        as a fallback signal.  ``os_patterns`` are never tested against
        description (it is not an OS field).
        """
        vm_match = any(p.search(vm_name) for p in self.vm_name_patterns)
        os_match = any(p.search(os_name) for p in self.os_patterns)

        # If vm_name didn't match but description is available, try description
        # as a fallback for vm_name_patterns only.
        if not vm_match and description and self.vm_name_patterns:
            vm_match = any(p.search(description) for p in self.vm_name_patterns)

        if self.match_mode == "all":
            return vm_match and os_match

        # "any" mode -- at least one defined pattern type must match.
        if self.vm_name_patterns and self.os_patterns:
            return vm_match or os_match
        if self.vm_name_patterns:
            return vm_match
        if self.os_patterns:
            return os_match
        return False


@dataclass(frozen=True)
class ClassificationResult:
    """Result of classifying a single VM."""

    category: str
    subcategory: str
    rule_name: str
    confidence: str  # "rule_match" | "os_fallback" | "default"


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------


class RuleRegistry:
    """Ordered collection of classification rules (first match wins)."""

    def __init__(self, rules: list[ClassificationRule]) -> None:
        self._rules = sorted(rules, key=lambda r: r.priority)

    def classify(self, vm_name: str, os_name: str, description: str = "") -> ClassificationResult:
        """Classify a VM by evaluating rules in priority order.

        Company prefixes are stripped from *vm_name* before matching
        (configured via :data:`~store_predict.config.COMPANY_PREFIX_PATTERNS`).
        The optional *description* parameter is passed through to rule matching
        as a fallback signal.
        """
        vm_name = strip_company_prefix(vm_name, COMPANY_PREFIX_PATTERNS)
        for rule in self._rules:
            if rule.matches(vm_name, os_name, description):
                if rule.priority < 900:
                    confidence = "rule_match"
                elif rule.priority <= 998:
                    confidence = "os_fallback"
                else:
                    confidence = "default"
                return ClassificationResult(
                    category=rule.category,
                    subcategory=rule.subcategory,
                    rule_name=rule.name,
                    confidence=confidence,
                )
        # Fallback (should never reach here if default rule exists)
        return ClassificationResult(
            category="Unknown (Reducible)",
            subcategory="Unknown (Reducible)",
            rule_name="default",
            confidence="default",
        )


# ---------------------------------------------------------------------------
# Default rule set (~25 rules covering all 28 DRR subcategories)
# ---------------------------------------------------------------------------


def build_default_rules() -> list[ClassificationRule]:
    """Build the default classification rule set covering all DRR categories.

    Priority tiers:
        100-199  Database
        200-299  Application-specific (Healthcare, Email, VDI)
        300-399  Infrastructure (Replication, Containers, Web, File)
        400-499  Logging / Analytics
        500-599  Boot from SAN
        900-949  OS-based fallback
        999      Default (Unknown Reducible)
    """
    return [
        # === Tier 1: Database (100-199) ===
        # NOTE: More specific DB rules (PostgreSQL, MySQL) must come BEFORE
        # generic "SQL" rule because "PGSQL" and "MYSQL" contain "SQL".
        ClassificationRule(
            name="Oracle Database",
            category="Database",
            subcategory="Oracle",
            priority=100,
            vm_name_patterns=_patterns("ORACLE"),
        ),
        ClassificationRule(
            name="MySQL / NoSQL",
            category="Database",
            subcategory="My SQL / NoSQL",
            priority=101,
            vm_name_patterns=_patterns("MYSQL", "NOSQL", "MARIADB"),
        ),
        ClassificationRule(
            name="PostgreSQL",
            category="Database",
            subcategory="PostgreSQL",
            priority=102,
            vm_name_patterns=_patterns("PGSQL", "POSTGRES", "POSTGRESQL"),
        ),
        ClassificationRule(
            name="Microsoft SQL",
            category="Database",
            subcategory="Microsoft SQL",
            priority=103,
            vm_name_patterns=_patterns("SQL", "MSSQL"),
        ),
        ClassificationRule(
            name="DB2",
            category="Database",
            subcategory="DB2",
            priority=104,
            vm_name_patterns=_patterns("DB2"),
        ),
        ClassificationRule(
            name="MongoDB",
            category="Database",
            subcategory="MongoDB",
            priority=105,
            vm_name_patterns=_patterns("MONGODB", "MONGO"),
        ),
        ClassificationRule(
            name="Prometheus",
            category="Database",
            subcategory="Prometheus",
            priority=106,
            vm_name_patterns=_patterns("PROMETHEUS"),
        ),
        ClassificationRule(
            name="SAP HANA",
            category="Database",
            subcategory="SAP HANA(S4)",
            priority=107,
            vm_name_patterns=_patterns("HANA", "S4HANA"),
        ),
        ClassificationRule(
            name="SAP Traditional",
            category="Database",
            subcategory="SAP Traditional (R/3 / ECC)",
            priority=108,
            # Word boundary required: "GISAPP" contains "SAP" but is NOT SAP.
            # Also match "SAP-xxx" and "SAP_xxx" naming conventions.
            vm_name_patterns=(*_patterns("SAP-", "SAP_"), *_regex_patterns(r"\bSAP\b")),
        ),
        # === Tier 2: Application-specific (200-299) ===
        ClassificationRule(
            name="HealthCare EMR/EHR",
            category="HealthCare",
            subcategory="EMR/EHR (Epic, McKesson)",
            priority=200,
            vm_name_patterns=_patterns("EPIC", "MCKESSON", "EMR", "EHR"),
        ),
        ClassificationRule(
            name="Email",
            category="Email",
            subcategory="Domino/Notes, Exchange, Sendmail, Zimbra, etc",
            priority=210,
            vm_name_patterns=_patterns("EXCHANGE", "DOMINO", "ZIMBRA", "SENDMAIL"),
        ),
        ClassificationRule(
            name="VDI Full Clone / MCS",
            category="VDI",
            subcategory="Full Clone / MCS (Citrix)",
            priority=220,
            vm_name_patterns=_patterns("CITRIX", "CIT", "MCS"),
        ),
        ClassificationRule(
            name="VDI Linked Clone / PVS",
            category="VDI",
            subcategory="Linked Clone / PVS (Citrix)",
            priority=221,
            vm_name_patterns=_patterns("PVS"),
        ),
        ClassificationRule(
            name="VDI Instant Clone",
            category="VDI",
            subcategory="Instant Clone",
            priority=222,
            vm_name_patterns=_patterns("HORIZON"),
        ),
        ClassificationRule(
            name="VDI Profiles",
            category="VDI",
            subcategory="VDI Profiles",
            priority=223,
            vm_name_patterns=_regex_patterns(r"VDI.*PROFIL|PROFIL.*VDI"),
        ),
        # === Tier 3: Infrastructure (300-399) ===
        ClassificationRule(
            name="VM Replication",
            category="VM Replication",
            subcategory="Veeam, Zerto, RP4VM",
            priority=300,
            vm_name_patterns=_patterns("VEEAM", "VBR", "ZERTO", "RP4VM"),
        ),
        ClassificationRule(
            name="Containers",
            category="Containers",
            subcategory="Kubernetes, OpenShift, Docker, Tanzu, etc",
            priority=310,
            vm_name_patterns=_patterns("DOCKER", "KUBERNETES", "K8S", "OPENSHIFT", "TANZU"),
        ),
        ClassificationRule(
            name="Web Servers",
            category="Web Servers",
            subcategory="Content included",
            priority=320,
            vm_name_patterns=_patterns("WEB", "WWW", "APACHE", "NGINX", "IIS"),
        ),
        ClassificationRule(
            name="File General Purpose",
            category="File",
            subcategory="General Purpose",
            priority=330,
            vm_name_patterns=_patterns("FILE"),
        ),
        ClassificationRule(
            name="File Content Servers",
            category="File",
            subcategory="Content Servers (Git, Sharepoint)",
            priority=340,
            vm_name_patterns=_patterns("GIT", "GITLAB", "SHAREPOINT"),
        ),
        ClassificationRule(
            name="File Developer Workspaces",
            category="File",
            subcategory="Developer Workspaces (DevOps)",
            priority=350,
            vm_name_patterns=_patterns("DEVOPS", "JENKINS", "ANSIBLE"),
        ),
        ClassificationRule(
            name="File Archive",
            category="File",
            subcategory=("Archive / Backup / Compressed / Encrypted / Rich Media / ISO / PACS / CAD"),
            priority=360,
            vm_name_patterns=_patterns("ARCHIVE"),
        ),
        # === Tier 4: Logging / Analytics (400-499) ===
        ClassificationRule(
            name="Logging Analytics",
            category="Logging - Analytics",
            subcategory="FortiNet, Elastic Search, Splunk, ELK, etc",
            priority=400,
            vm_name_patterns=_patterns(
                "ELASTIC",
                "ELK",
                "SPLUNK",
                "FORTIANALYZER",
                "FORTIMANAGER",
                "ZABBIX",
                "CENTREON",
                "OBSERVIUM",
                "GRAFANA",
            ),
            os_patterns=_patterns("FORTI"),
        ),
        # === Tier 5: Boot from SAN (500-599) ===
        ClassificationRule(
            name="Boot from SAN",
            category="Boot from SAN",
            subcategory="Linux, VMware, Windows - OS Boot",
            priority=500,
            vm_name_patterns=_patterns("BOOTSAN", "SANBOOT"),
        ),
        # === Tier 6: OS-based fallback (900-949) ===
        ClassificationRule(
            name="Windows Server (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=900,
            os_patterns=_regex_patterns(r"windows server"),
        ),
        ClassificationRule(
            name="Windows Desktop (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=905,
            os_patterns=_regex_patterns(r"windows 10|windows 11|windows 7"),
        ),
        ClassificationRule(
            name="Linux (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=910,
            os_patterns=_regex_patterns(
                r"linux|ubuntu|centos|debian|red hat|suse|alma|rocky|oracle linux|freebsd",
            ),
        ),
        ClassificationRule(
            name="VMware/ESXi (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=920,
            os_patterns=_regex_patterns(r"vmware|esxi|photon"),
        ),
        # === Tier 7: Default (999) ===
        ClassificationRule(
            name="default",
            category="Unknown (Reducible)",
            subcategory="Unknown (Reducible)",
            priority=999,
            vm_name_patterns=_regex_patterns(r".*"),
        ),
    ]


# ---------------------------------------------------------------------------
# DataFrame-level classification
# ---------------------------------------------------------------------------


def classify_dataframe(
    df: pd.DataFrame,
    registry: RuleRegistry,
) -> pd.DataFrame:
    """Classify all VMs in *df*, returning a copy with four new columns.

    Added columns: ``workload_category``, ``workload_subcategory``,
    ``classification_rule``, ``classification_confidence``.

    NaN ``os_name`` values are converted to empty string before matching
    so that ``"nan"`` does not accidentally trigger patterns.
    """
    result = df.copy()

    has_description = "vm_description" in df.columns

    classifications = []
    for _, row in df.iterrows():
        vm_name = str(row["vm_name"]) if pd.notna(row["vm_name"]) else ""
        os_name = str(row["os_name"]) if pd.notna(row["os_name"]) else ""
        description = (
            str(row["vm_description"])
            if has_description and pd.notna(row.get("vm_description"))
            else ""
        )
        classifications.append(registry.classify(vm_name, os_name, description))

    result["workload_category"] = [c.category for c in classifications]
    result["workload_subcategory"] = [c.subcategory for c in classifications]
    result["classification_rule"] = [c.rule_name for c in classifications]
    result["classification_confidence"] = [c.confidence for c in classifications]
    return result
