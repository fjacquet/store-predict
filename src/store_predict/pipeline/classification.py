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

# Generic role prefixes commonly prepended to VM names in enterprise environments.
# Stripped before pattern matching so that "SrvSAP02" exposes "SAP02" to rules.
# Order matters: longer prefixes first to avoid partial stripping.
_ROLE_PREFIX_RE = re.compile(
    r"^(?:SRV|PC)[-_.]?",
    re.IGNORECASE,
)


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


def _strip_role_prefix(vm_name: str) -> str:
    """Strip generic role prefixes (Srv, PC) from *vm_name*.

    These prefixes indicate server/workstation role but obscure the application
    keyword that classification rules need to match (e.g. "SrvSAP02" → "SAP02").
    """
    return _ROLE_PREFIX_RE.sub("", vm_name)


def _patterns(*keywords: str) -> tuple[re.Pattern[str], ...]:
    """Compile case-insensitive literal substring patterns.

    Uses ``re.escape`` so characters like ``+`` or ``.`` are safe.
    """
    return tuple(re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords)


def _word_patterns(*keywords: str) -> tuple[re.Pattern[str], ...]:
    """Compile case-insensitive word-boundary patterns.

    Use for ambiguous short tokens (``SQL``, ``DB2``, ``CIT``) that would
    otherwise false-match inside unrelated names (``NotASQL``, ``DB2500``,
    ``CITIZEN``). Boundaries treat digits and letters as word chars, so
    ``\\bSQL\\b`` still matches ``SQL-SRV01`` but not ``MSSQL``.
    """
    return tuple(re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords)


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
    folder_patterns: tuple[re.Pattern[str], ...] = ()
    match_mode: str = "any"  # "any" = OR among defined sets, "all" = AND

    def matches(
        self,
        vm_name: str,
        os_name: str,
        description: str = "",
        folder: str = "",
    ) -> bool:
        """Return *True* if this rule matches the given VM signals.

        When *description* is non-empty and no ``vm_name_patterns`` match
        against *vm_name*, the patterns are also checked against *description*
        as a fallback signal.  ``os_patterns`` are never tested against
        description (it is not an OS field).

        Default ``match_mode="any"``: at least one defined pattern set must
        match. ``match_mode="all"``: every defined pattern set must match
        (use this when you need a folder-qualifier AND a name token, e.g.
        Nutanix CVM where bare ``CVM`` would over-match).
        """
        vm_match = any(p.search(vm_name) for p in self.vm_name_patterns)
        os_match = any(p.search(os_name) for p in self.os_patterns)
        folder_match = any(p.search(folder) for p in self.folder_patterns)

        # If vm_name didn't match but description is available, try description
        # as a fallback for vm_name_patterns only.
        if not vm_match and description and self.vm_name_patterns:
            vm_match = any(p.search(description) for p in self.vm_name_patterns)

        defined: list[bool] = []
        if self.vm_name_patterns:
            defined.append(vm_match)
        if self.os_patterns:
            defined.append(os_match)
        if self.folder_patterns:
            defined.append(folder_match)
        if not defined:
            return False

        if self.match_mode == "all":
            return all(defined)
        return any(defined)


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

    def classify(
        self,
        vm_name: str,
        os_name: str,
        description: str = "",
        folder: str = "",
    ) -> ClassificationResult:
        """Classify a VM by evaluating rules in priority order.

        Company prefixes are stripped from *vm_name* before matching
        (configured via :data:`~store_predict.config.COMPANY_PREFIX_PATTERNS`).

        A two-pass approach ensures direct vm_name/os_name/folder matches
        always take priority over description-based fallback matches:

        1. First pass: match without description (direct matches only).
        2. Second pass: match with description as fallback signal.
        """
        vm_name = strip_company_prefix(vm_name, COMPANY_PREFIX_PATTERNS)
        vm_name = _strip_role_prefix(vm_name)

        # Pass 1: direct matches (no description fallback)
        # When description is available, skip OS-fallback and default rules (priority ≥ 900)
        # so that pass 2 can find a better annotation-based match first.
        for rule in self._rules:
            if description and rule.priority >= 900:
                continue
            if rule.matches(vm_name, os_name, folder=folder):
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

        # Pass 2: try again with description as fallback signal
        if description:
            for rule in self._rules:
                if rule.matches(vm_name, os_name, description, folder):
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
        # === Tier 0: Application-level encryption/compression variants (80-99) ===
        # These must come BEFORE their plain counterparts so that specifically-named
        # encrypted/compressed VMs get the correct (lower) DRR subcategory.
        # Combined patterns (HCC+TDE) use regex lookaheads for AND matching.
        ClassificationRule(
            name="Oracle HCC + TDE",
            category="Database",
            subcategory="Oracle - HCC + TDE",
            priority=88,
            vm_name_patterns=_regex_patterns(r"(?=.*(?:ORACLE|ORA))(?=.*HCC)(?=.*TDE)"),
        ),
        ClassificationRule(
            name="Oracle HCC",
            category="Database",
            subcategory="Oracle - HCC (App Compressed)",
            priority=89,
            vm_name_patterns=_regex_patterns(r"(?=.*(?:ORACLE|ORA))(?=.*\bHCC\b)"),
        ),
        ClassificationRule(
            name="Oracle TDE",
            category="Database",
            subcategory="Oracle - TDE (Encrypted)",
            priority=90,
            vm_name_patterns=_patterns("ORACLE-TDE", "ORA-TDE", "ORATDE", "ORACLE-ENC", "ORA-ENC"),
        ),
        ClassificationRule(
            name="SQL Page Compressed + TDE",
            category="Database",
            subcategory="Microsoft SQL - Page Compressed + TDE",
            priority=91,
            vm_name_patterns=_regex_patterns(r"(?=.*(?:MSSQL|SQL))(?=.*(?:COMPRESS|PAGE))(?=.*TDE)"),
        ),
        ClassificationRule(
            name="SQL Page Compressed",
            category="Database",
            subcategory="Microsoft SQL - Page Compressed",
            priority=92,
            vm_name_patterns=_patterns("SQL-COMPRESS", "SQL-COMP", "SQL-PAGE", "MSSQL-COMPRESS", "MSSQL-PAGE"),
        ),
        ClassificationRule(
            name="SQL TDE",
            category="Database",
            subcategory="Microsoft SQL - TDE (Encrypted)",
            priority=93,
            vm_name_patterns=_patterns("SQL-TDE", "MSSQL-TDE", "SQL-ENC", "MSSQL-ENC"),
        ),
        ClassificationRule(
            name="MongoDB Encrypted",
            category="Database",
            subcategory="MongoDB - Encrypted",
            priority=94,
            vm_name_patterns=_patterns("MONGO-ENC", "MONGO-ENCRYPT", "MONGODB-ENC"),
        ),
        ClassificationRule(
            name="PostgreSQL Encrypted",
            category="Database",
            subcategory="PostgreSQL - Encrypted",
            priority=95,
            vm_name_patterns=_patterns("PGSQL-ENC", "POSTGRES-ENC", "PG-ENC", "POSTGRESQL-ENC"),
        ),
        ClassificationRule(
            name="MySQL / NoSQL Encrypted",
            category="Database",
            subcategory="My SQL / NoSQL - Encrypted",
            priority=96,
            vm_name_patterns=_patterns("MYSQL-ENC", "MYSQL-ENCRYPT", "NOSQL-ENC", "MARIADB-ENC"),
        ),
        ClassificationRule(
            name="Kubernetes Encrypted PVs",
            category="Containers",
            subcategory="Kubernetes - Encrypted PVs",
            priority=97,
            vm_name_patterns=_patterns("K8S-ENC", "K8S-LUKS", "KUBE-ENC", "KUBE-LUKS", "K8S-ENCRYPT"),
        ),
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
            vm_name_patterns=_patterns("MYSQL", "NOSQL", "MARIADB", "FILEMAKER", "CLARIS", "SQLITE", "REDIS"),
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
            # Word-bounded: avoid matching "DB2500" storage-array hostnames.
            vm_name_patterns=_word_patterns("DB2"),
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
            # S4[A-Z]\d matches SAP S/4 role suffixes followed by a sequence number:
            # S4P (prod), S4R (reporting), S4Q (quality), S4D (dev), etc.
            # Digit required to avoid false positives like S4DM (storage appliance).
            vm_name_patterns=(*_patterns("HANA", "S4HANA"), *_regex_patterns(r"S4[A-Z]\d")),
        ),
        ClassificationRule(
            name="SAP Traditional",
            category="Database",
            subcategory="SAP Traditional (R/3 / ECC)",
            priority=108,
            # Word boundary required: "GISAPP" contains "SAP" but is NOT SAP.
            # Also match "SAP-xxx" and "SAP_xxx" naming conventions.
            # ^SAP(?![a-z]) covers post-prefix-strip names like "SAP02" (from "SrvSAP02")
            # while rejecting "SAPLING" etc. (IGNORECASE makes [a-z] match uppercase too).
            vm_name_patterns=(*_patterns("SAP-", "SAP_"), *_regex_patterns(r"\bSAP\b", r"^SAP(?![a-z])")),
        ),
        ClassificationRule(
            name="SAP HANA HDB",
            category="Database",
            subcategory="SAP HANA(S4)",
            priority=109,
            # Substring "saphdb" catches embedded forms like "sdsaphdb01" where
            # no word boundary exists. "HDB<digits>" stays word-bounded to avoid
            # false matches on unrelated tokens.
            vm_name_patterns=(*_patterns("SAPHDB"), *_regex_patterns(r"\bHDB\d+\b")),
            folder_patterns=_regex_patterns(r"HanaDB|HANA[-_ ]?DB"),
        ),
        ClassificationRule(
            name="SAP general (folder)",
            category="Database",
            subcategory="SAP Traditional (R/3 / ECC)",
            priority=175,
            # Folder-only fallback: any VM under a /SAP_*/ folder that didn't match
            # a more specific HANA rule above.
            folder_patterns=_regex_patterns(r"/SAP[_ -]|/SAP$"),
        ),
        # === Tier 2: Application-specific (200-299) ===
        ClassificationRule(
            name="HealthCare EMR/EHR",
            category="HealthCare",
            subcategory="EMR/EHR (Epic, McKesson)",
            priority=200,
            vm_name_patterns=(
                # US market EMR/EHR leaders
                *_patterns("EPIC", "MCKESSON", "EMR", "EHR"),
                # Radiology & medical imaging
                *_patterns(
                    "PACS",  # Picture Archiving and Communication System
                    "INTELLISPACE",  # Philips IntelliSpace radiology platform
                    "GLEAMER",  # AI radiology (chest/bone X-ray)
                    "AZMED",  # Azmed AI medical imaging
                    "RAYVOLVE",  # Azmed Rayvolve imaging product
                    "TRAUMACAD",  # Brainlab orthopedic surgical planning
                ),
                # Hospital IS / clinical management (French-Swiss & European ecosystem)
                *_patterns(
                    "OPALE",  # Opale/eOpale hospital billing & management
                    "CARIATIDE",  # Cariatide clinical management software
                    "HANDYLIFE",  # Handylife patient management (Medicentres)
                    "POLYPOINT",  # Polypoint hospital resource scheduling
                    # "HESTIA" handled via regex below (avoid false match on HestiaCP Linux panel)
                    # "SIEMS" handled via regex below (avoid false match on SIEMENS)
                    "PLAISIR",  # PLAISIR psychiatric/social care IS
                    "MEDIDATA",  # MediData health data exchange (Swiss clearing)
                    "DATABICS",  # DatabICS ICU clinical data system
                    "PROCAMED",  # Procamed medical device integration
                    "SEDIA",  # Sedia urology management
                    "DGLAB",  # DGLab diagnostic laboratory IS
                    "DGLIM",  # DGLim laboratory IS variant
                    "STERIGEST",  # Sterigest sterile supply chain management
                    "WINSCRIBE",  # Winscribe medical speech recognition & dictation
                    "SYNLAB",  # Synlab clinical laboratory services
                    "EXOLIS",  # Exolis patient digital experience platform
                    "SCENARA",  # Scenara perioperative / operating room management
                    "MIRTH",  # Mirth Connect HL7/FHIR integration engine
                    "KODIP",  # 3M Kodip DRG coding software
                ),
                # Radiology Information System (word-boundary anchored)
                *_regex_patterns(r"\bRIS\b"),
                # SIEMS - word-boundary required to avoid matching SIEMENS
                *_regex_patterns(r"\bSIEMS\b"),
                # HESTIA - word-boundary required to avoid matching HestiaCP Linux panel
                *_regex_patterns(r"\bHESTIA\b"),
                # Operating room management (BlocOp = bloc opératoire in French)
                *_regex_patterns(r"Bloc-?Op|BLOCOP"),
            ),
        ),
        ClassificationRule(
            name="Microsoft Exchange (folder)",
            category="Email",
            subcategory="Domino/Notes, Exchange, Sendmail, Zimbra, etc",
            priority=215,
            folder_patterns=_regex_patterns(r"/EXCH(?:ANGE)?(?:/|$)"),
        ),
        ClassificationRule(
            name="Cisco Unified Communications",
            category="Web Servers",
            subcategory="Content included",
            priority=250,
            # Cisco UC stack: CUCM (Call Manager), UCCX/CCX (Contact Center Express),
            # CUIC (Intelligence Center), Finesse (agent desktop), IPCC, CUC (Unity
            # Connection voicemail), CER (Emergency Responder), PCD (Prime Collab
            # Deployment). "Cisco Unity Connection" appears in OVA annotations.
            vm_name_patterns=(
                *_regex_patterns(
                    r"\b(?:CUCM|UCCX|CUIC|FINESSE|IPCC|CCX|CUIM|CUC|CER|PCD)\b",
                ),
                *_patterns("Cisco Unity Connection"),
            ),
            folder_patterns=_regex_patterns(r"/UC(?:M)?(?:/|$)"),
        ),
        ClassificationRule(
            name="Email",
            category="Email",
            subcategory="Domino/Notes, Exchange, Sendmail, Zimbra, etc",
            priority=210,
            # MSG = Exchange mail-store abbreviation (e.g. swigva01-msg-*)
            # [-_]EX\d = short Exchange hostname suffix (e.g. CIGES-EX1, CIGES-EX2)
            #   digit required to avoid matching EXTRANET, EXCEPT, etc.
            # EXC + digit = Exchange abbreviation (e.g. SRVEXC02 → EXC02 after prefix strip)
            vm_name_patterns=(
                *_patterns("EXCHANGE", "DOMINO", "ZIMBRA", "SENDMAIL", "MSG", "EXCHG"),
                *_regex_patterns(r"[-_]EX\d", r"EXC\d"),
            ),
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
            # PVS = Citrix Provisioning Services generic label
            # cp-replica-* / cp-template-* = Citrix PVS linked-clone naming convention
            #   (UUID-suffixed VMs created by Citrix Provisioning)
            # MST-W10-* = PVS master target device images (versioned golden images)
            vm_name_patterns=_patterns("PVS", "CP-REPLICA", "CP-TEMPLATE", "MST-W10"),
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
            vm_name_patterns=(
                *_patterns("APPVOL", "APP VOLUMES", "APP-VOL"),  # VMware App Volumes (Horizon)
                *_regex_patterns(r"VDI.*PROFIL|PROFIL.*VDI"),
            ),
        ),
        ClassificationRule(
            name="VDI Generic",
            category="VDI",
            subcategory="Linked Clone / PVS (Citrix)",
            priority=224,
            vm_name_patterns=(*_patterns("VDI", "DESKTOP", "LOGINVSI", "LOGINENTERPRISE", "UAG", "RDS"),),
        ),
        # === Tier 3: Infrastructure (300-399) ===
        # Compressed/dedup backup variants (lower DRR) come before plain rules.
        ClassificationRule(
            name="Nutanix CVM",
            category="VM Replication",
            subcategory="Data Domain Virtual Edition (DDVE)",
            priority=294,
            # Nutanix Controller VMs are storage controllers — they handle the
            # cluster's data services. Their disks contain dedupe metadata + OS,
            # not customer-reducible content. Routed to DDVE (DRR=1.0) because
            # DDVE's "already-deduped, no further reducibility" semantics fit.
            # Tight name patterns required to avoid matching unrelated tokens
            # (bare "CVM" is too generic). Folder match alone also fires.
            vm_name_patterns=(
                # NTNX prefix is Nutanix-specific (e.g. NTNX-19SM5A510097-A-CVM)
                *_patterns("NTNX-", "NTNX_"),
                # CVM as discrete token with separator (avoids matching e.g. "scvm")
                *_regex_patterns(r"[-_]CVM(?:[-_]|$)"),
                *_patterns("Nutanix Controller VM"),
            ),
            folder_patterns=_regex_patterns(r"/NTNX[ _-]?CVMs?(?:/|$)"),
        ),
        ClassificationRule(
            name="DDVE",
            category="VM Replication",
            subcategory="Data Domain Virtual Edition (DDVE)",
            priority=293,
            # DDVE stores already-deduplicated data → PowerStore sees DRR = 1.0
            vm_name_patterns=_patterns("DDVE", "DATADOMAIN", "DATA-DOMAIN"),
        ),
        ClassificationRule(
            name="Veeam Compressed + Dedup",
            category="VM Replication",
            subcategory="Veeam - Compressed + Dedup",
            priority=295,
            vm_name_patterns=_patterns("VEEAM-DD", "VBR-DD"),
        ),
        ClassificationRule(
            name="Commvault Compressed + Dedup",
            category="VM Replication",
            subcategory="Commvault - Compressed + Dedup",
            priority=296,
            vm_name_patterns=_patterns("COMMVAULT-DD", "CVD-DD"),
        ),
        ClassificationRule(
            name="Commvault",
            category="VM Replication",
            subcategory="Commvault",
            priority=297,
            vm_name_patterns=_patterns("COMMVAULT", "CVD"),
        ),
        ClassificationRule(
            name="Veritas / NetBackup",
            category="VM Replication",
            subcategory="Veeam, Zerto, RP4VM",
            priority=298,
            vm_name_patterns=_patterns("VERITAS", "NETBACKUP", "NBU"),
        ),
        ClassificationRule(
            name="Dell PowerProtect (description)",
            category="VM Replication",
            subcategory="Veeam, Zerto, RP4VM",
            priority=299,
            # Description-fallback signature: PowerProtect Data Manager appliances
            # carry "PowerProtect" in vCenter Annotation. Pass-2 of classify()
            # tries vm_name_patterns against description when name didn't match.
            vm_name_patterns=_patterns("PowerProtect"),
        ),
        ClassificationRule(
            name="VM Replication",
            category="VM Replication",
            subcategory="Veeam, Zerto, RP4VM",
            priority=300,
            vm_name_patterns=_patterns("VEEAM", "VBR", "ZERTO", "RP4VM"),
        ),
        ClassificationRule(
            name="Dell PowerFlex SDS",
            category="Containers",
            subcategory="Kubernetes, OpenShift, Docker, Tanzu, etc",
            priority=311,
            # PowerFlex management is Kubernetes-based on recent releases.
            vm_name_patterns=_regex_patterns(r"\bpflex\w*"),
            folder_patterns=_regex_patterns(r"/PowerFlex(?:/|$)"),
        ),
        ClassificationRule(
            name="Domain Controller / AAD",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=320,
            # Active Directory DCs and Azure AD Connect: small NTDS.dit + OS data,
            # routed to generic VM (DRR=5) per pre-sales guidance.
            vm_name_patterns=_regex_patterns(
                r"\bDC\d+\b",
                r"\bAADC?\d*\b",
                r"\bADDS\b",
            ),
            folder_patterns=_regex_patterns(r"/AD$|/AADC|/Domain Controllers"),
        ),
        ClassificationRule(
            name="IPAM",
            category="Web Servers",
            subcategory="Content included",
            priority=325,
            # IPAM appliances (small DB, web UI) — phpipam, BlueCat, Infoblox-style.
            vm_name_patterns=_regex_patterns(r"\bIPAM\b", r"\bphpipam\b"),
            folder_patterns=_regex_patterns(r"/IPAM(?:/|$)"),
        ),
        ClassificationRule(
            name="Identity / Auth (Nevis)",
            category="Web Servers",
            subcategory="Content included",
            priority=330,
            # Nevis (Adnovum) identity & access proxy / auth server. EID/IAM
            # folders cover broader identity stacks (e.g. eID services).
            vm_name_patterns=_regex_patterns(r"\bnevis\b"),
            folder_patterns=_regex_patterns(r"/IAM|/EID|/NEVIS"),
        ),
        ClassificationRule(
            name="Containers",
            category="Containers",
            subcategory="Kubernetes, OpenShift, Docker, Tanzu, etc",
            priority=310,
            vm_name_patterns=(
                *_patterns("DOCKER", "KUBERNETES", "K8S", "OPENSHIFT", "TANZU", "TKG", "HARBOR"),
                *_regex_patterns(r"photon-.*-kube"),
            ),
        ),
        ClassificationRule(
            name="Web Servers",
            category="Web Servers",
            subcategory="Content included",
            priority=320,
            vm_name_patterns=_patterns("WEB", "WWW", "APACHE", "NGINX", "IIS", "TOMCAT", "FORTIWEB", "INTRANET"),
        ),
        ClassificationRule(
            name="File General Purpose",
            category="File",
            subcategory="General Purpose",
            priority=330,
            vm_name_patterns=(
                *_patterns("FILE"),
                # FS + digit/separator = File Server (e.g. SrvFS01 → FS01 after prefix strip)
                *_regex_patterns(r"^FS\d", r"^FS[-_]"),
            ),
        ),
        ClassificationRule(
            name="File Content Servers",
            category="File",
            subcategory="Content Servers (Git, Sharepoint)",
            priority=340,
            vm_name_patterns=(
                *_patterns("GIT", "GITLAB", "BITBUCKET", "SHAREPOINT", "ALFRESCO"),
                *_patterns("SPBE", "SPFE", "SPOWA", "SPOFFICE"),
            ),
        ),
        ClassificationRule(
            name="File Developer Workspaces",
            category="File",
            subcategory="Developer Workspaces (DevOps)",
            priority=350,
            vm_name_patterns=_patterns("DEVOPS", "JENKINS", "ANSIBLE", "DEPLOY"),
        ),
        ClassificationRule(
            name="File Archive",
            category="File",
            subcategory=("Archive / Backup / Compressed / Encrypted / Rich Media / ISO / PACS / CAD"),
            priority=360,
            vm_name_patterns=_patterns("ARCHIVE", "BACKUP"),
        ),
        ClassificationRule(
            name="VMware Infrastructure VMs",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=395,
            # vCLS = VMware Cluster Services (auto-created by vSphere 7.0+ DRS/HA)
            # VxRail = Dell VxRail hyperconverged management appliance
            vm_name_patterns=_patterns("VCLS", "VXRAIL"),
        ),
        ClassificationRule(
            name="vCenter / vSAN Witness (description)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=396,
            # Annotation signatures from VCSA / vSAN Witness OVAs.
            vm_name_patterns=_patterns("vCenter Server Appliance", "vSAN Witness"),
        ),
        # === Tier 4: Logging / Analytics (400-499) ===
        ClassificationRule(
            name="FortiDeceptor (description)",
            category="Logging - Analytics",
            subcategory="FortiNet, Elastic Search, Splunk, ELK, etc",
            priority=401,
            vm_name_patterns=_patterns("FortiDeceptor"),
        ),
        ClassificationRule(
            name="BeyondTrust / Bomgar (description)",
            category="Web Servers",
            subcategory="Content included",
            priority=430,
            # Privileged remote-access appliances (BeyondTrust = Bomgar's modern
            # name). Annotation signatures: "BeyondTrust Secure Remote Access",
            # "Bomgar Virtual Appliance".
            vm_name_patterns=_patterns("BeyondTrust", "Bomgar"),
        ),
        ClassificationRule(
            name="Tenable Nessus (description)",
            category="Web Servers",
            subcategory="Content included",
            priority=435,
            vm_name_patterns=_patterns("Tenable", "Nessus"),
        ),
        ClassificationRule(
            name="NetApp OnCommand UM (description)",
            category="Web Servers",
            subcategory="Content included",
            priority=450,
            vm_name_patterns=_patterns("OnCommand Unified Manager"),
        ),
        ClassificationRule(
            name="Horizon3.ai NodeZero (description)",
            category="Web Servers",
            subcategory="Content included",
            priority=460,
            vm_name_patterns=_patterns("Horizon3.ai", "Nodezero"),
        ),
        ClassificationRule(
            name="exotrack (description)",
            category="Web Servers",
            subcategory="Content included",
            priority=465,
            vm_name_patterns=_patterns("exotrack"),
        ),
        ClassificationRule(
            name="Logging Analytics",
            category="Logging - Analytics",
            subcategory="FortiNet, Elastic Search, Splunk, ELK, etc",
            priority=400,
            vm_name_patterns=(
                *_patterns(
                    "ELASTIC",
                    "ELK",
                    "SPLUNK",
                    "FORTIANALYZER",
                    "FORTIMANAGER",
                    "FAZ",  # FortiAnalyzer short hostname (e.g. CIGES-FAZ)
                    "FMG",  # FortiManager short hostname (e.g. CIGES-FMG)
                    "ZABBIX",
                    "CENTREON",
                    "OBSERVIUM",
                    "GRAFANA",
                    "RSYSLOG",  # syslog collection servers
                    "SYSLOG",
                    "POLLER",  # monitoring pollers (Centreon/Nagios)
                    "PRTG",  # PRTG Network Monitor (Paessler)
                    "LOGSTASH",  # Logstash log pipeline
                    "KIBANA",  # Kibana visualization (ELK stack)
                    "LOGINSIGHT",  # VMware Log Insight / Aria Operations for Logs
                    "NAGIOS",  # Nagios monitoring platform
                    "ICINGA",  # Icinga monitoring (Nagios fork)
                    "SOLARWINDS",  # SolarWinds network monitoring (NPM, etc.)
                    "LIBRENMS",  # LibreNMS open-source network monitoring
                    "OPENNMS",  # OpenNMS open-source network management
                ),
                # LOG followed by digit, separator, or end — avoids LOGIN, LOGIC, LOGO
                # LOGDMZ covers log servers in DMZ segments (e.g. SrvLogDMZ01)
                *_regex_patterns(r"LOG(?:\d|[-_.]|$)"),
                *_patterns("LOGDMZ"),
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
            category="VDI",
            subcategory="Linked Clone / PVS (Citrix)",
            priority=905,
            os_patterns=_regex_patterns(r"windows 10|windows 11|windows 7"),
        ),
        ClassificationRule(
            name="Linux (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=910,
            os_patterns=_regex_patterns(
                r"linux|ubuntu|centos|debian|red hat|suse|alma|rocky|oracle linux|freebsd|solaris",
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
    has_folder = "vm_folder" in df.columns

    classifications = []
    for _, row in df.iterrows():
        vm_name = str(row["vm_name"]) if pd.notna(row["vm_name"]) else ""
        os_name = str(row["os_name"]) if pd.notna(row["os_name"]) else ""
        description = str(row["vm_description"]) if has_description and pd.notna(row.get("vm_description")) else ""
        folder = str(row["vm_folder"]) if has_folder and pd.notna(row.get("vm_folder")) else ""
        classifications.append(registry.classify(vm_name, os_name, description, folder))

    result["workload_category"] = [c.category for c in classifications]
    result["workload_subcategory"] = [c.subcategory for c in classifications]
    result["classification_rule"] = [c.rule_name for c in classifications]
    result["classification_confidence"] = [c.confidence for c in classifications]
    return result
