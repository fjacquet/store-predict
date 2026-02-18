# Phase 3: Workload Classification Engine - Research

**Researched:** 2026-02-18
**Domain:** Rules-based pattern matching, VM name parsing, workload categorization
**Confidence:** HIGH

## Summary

Phase 3 implements a rules-based classification engine that assigns each VM to a DRR workload category by matching against its VM name and OS field. The engine uses an ordered list of `ClassificationRule` dataclasses evaluated in priority order (first match wins), with substring matching for embedded keywords (e.g., "CADSRVSQL001" must match "SQL").

Analysis of the actual sample data (610 LiveOptics VMs + 24 RVTools VMs) reveals several important patterns: (1) VM names follow corporate naming conventions with embedded functional keywords (SQL, CIT, DC, etc.), (2) some keywords create false positives ("GISAPP" contains "SAP", "LORADB" contains "ORA"), (3) FortiNet appliances are identifiable via OS field rather than VM name, (4) a significant number of VMs (~60%) have generic names that will fall through to OS-based or default classification. The DRR.csv has 28 valid entries across categories: Database (9), File (4), VDI (4), HealthCare (1), Logging-Analytics (1), Email (1), Containers (1), Virtual Machines (1), VM Replication (1), Boot from SAN (1), Web Servers (2), Unknown (1), Custom (1).

The architecture follows the pattern already established in ARCHITECTURE.md: a rule registry with ordered evaluation, creating `pipeline/classification.py` as a pure function (DataFrame in, enriched DataFrame out) with zero UI imports.

**Primary recommendation:** Build a `ClassificationRule` dataclass with case-insensitive substring matching on VM name and OS field. Use compiled `re.Pattern` objects for patterns. Priority ordering: specific application patterns (Database, VDI, Email) first, then infrastructure patterns (Backup, Containers, Web), then OS-based fallback (Windows Server -> Virtual Machines), then default (Unknown Reducible, DRR=5). Be careful with short/ambiguous patterns (ORA, EX, SAP) that produce false positives.

## Standard Stack

### Core (already installed, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| re (stdlib) | N/A | Compiled regex patterns for substring matching | Standard library, zero dependencies, sufficient for case-insensitive substring search |
| dataclasses (stdlib) | N/A | ClassificationRule and ClassificationResult dataclasses | Already used throughout project (VMRecord, DRREntry) |
| pandas | >=2.2 | DataFrame operations for bulk classification | Already in project, vectorized operations for 5000+ VMs |

### No New Dependencies Needed

Classification is pure Python pattern matching. No NLP, fuzzy matching, or ML libraries are needed for v1. The patterns are well-defined substrings (SQL, ORACLE, VDI, etc.) matched case-insensitively against VM name and OS fields.

## Architecture Patterns

### Recommended Module Structure

```
src/store_predict/
  pipeline/
    classification.py      # ClassificationRule, RuleRegistry, classify_dataframe()
    models.py              # Add ClassificationResult dataclass (or keep in classification.py)
```

### Pattern 1: ClassificationRule Dataclass

**What:** Immutable dataclass defining a single classification rule with priority, patterns, and match mode.

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassificationRule:
    """A single classification rule for matching VMs to workload categories."""

    name: str                          # Human-readable rule name, e.g., "Microsoft SQL"
    category: str                      # DRR category, e.g., "Database"
    subcategory: str                   # DRR subcategory, e.g., "Microsoft SQL"
    priority: int                      # Lower = higher priority (evaluated first)
    vm_name_patterns: tuple[re.Pattern[str], ...] = ()  # Match against VM name
    os_patterns: tuple[re.Pattern[str], ...] = ()       # Match against OS field
    match_mode: str = "any"            # "any" = vm_name OR os, "all" = both required

    def matches(self, vm_name: str, os_name: str) -> bool:
        """Check if this rule matches the given VM name and OS."""
        vm_match = any(p.search(vm_name) for p in self.vm_name_patterns)
        os_match = any(p.search(os_name) for p in self.os_patterns)

        if self.match_mode == "all":
            return vm_match and os_match
        # "any" mode: at least one pattern type must be defined and match
        if self.vm_name_patterns and self.os_patterns:
            return vm_match or os_match
        if self.vm_name_patterns:
            return vm_match
        if self.os_patterns:
            return os_match
        return False
```

**Key design choices:**

- `frozen=True` for immutability (rules never change at runtime)
- `tuple` for patterns (hashable, immutable)
- Compiled `re.Pattern` with `re.IGNORECASE` for case-insensitive substring matching
- `match_mode` supports "any" (OR logic) and "all" (AND logic) for flexible matching

### Pattern 2: Rule Registry with Priority Ordering

**What:** Ordered collection of rules evaluated sequentially. First match wins.

```python
@dataclass
class ClassificationResult:
    """Result of classifying a single VM."""

    category: str
    subcategory: str
    rule_name: str          # Which rule matched (for FR-3.4 confidence indicator)
    confidence: str         # "rule_match" | "os_fallback" | "default"


class RuleRegistry:
    """Ordered collection of classification rules."""

    def __init__(self, rules: list[ClassificationRule]) -> None:
        # Sort by priority (lower number = higher priority)
        self._rules = sorted(rules, key=lambda r: r.priority)

    def classify(self, vm_name: str, os_name: str) -> ClassificationResult:
        """Classify a VM by evaluating rules in priority order."""
        for rule in self._rules:
            if rule.matches(vm_name, os_name):
                return ClassificationResult(
                    category=rule.category,
                    subcategory=rule.subcategory,
                    rule_name=rule.name,
                    confidence="rule_match" if rule.priority < 900 else
                               "os_fallback" if rule.priority < 1000 else "default",
                )
        # Should never reach here if default rule exists
        return ClassificationResult(
            category="Unknown (Reducible)",
            subcategory="Unknown (Reducible)",
            rule_name="default",
            confidence="default",
        )
```

### Pattern 3: DataFrame-Level Classification (Pure Function)

**What:** Bulk classify all VMs in a DataFrame, adding classification columns.

```python
def classify_dataframe(
    df: pd.DataFrame,
    registry: RuleRegistry,
) -> pd.DataFrame:
    """Classify all VMs in the DataFrame.

    Adds columns: workload_category, workload_subcategory, classification_rule, classification_confidence

    Args:
        df: DataFrame with vm_name and os_name columns (from ingestion).
        registry: Rule registry to use for classification.

    Returns:
        Copy of DataFrame with classification columns added.
    """
    result = df.copy()
    classifications = [
        registry.classify(
            str(row["vm_name"]),
            str(row["os_name"]),
        )
        for _, row in df.iterrows()
    ]
    result["workload_category"] = [c.category for c in classifications]
    result["workload_subcategory"] = [c.subcategory for c in classifications]
    result["classification_rule"] = [c.rule_name for c in classifications]
    result["classification_confidence"] = [c.confidence for c in classifications]
    return result
```

**Note on performance:** For 610 VMs with ~40 rules, iterrows is fast enough (<100ms). For 5000+ VMs (NFR-4.1), this is still under 1 second. Vectorized approach with `df.apply()` is an option but adds complexity without meaningful benefit at this scale.

### Pattern 4: Helper for Building Patterns

**What:** Convenience function to create compiled case-insensitive regex patterns.

```python
def _patterns(*keywords: str) -> tuple[re.Pattern[str], ...]:
    """Create case-insensitive substring-matching patterns."""
    return tuple(re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords)

def _regex_patterns(*expressions: str) -> tuple[re.Pattern[str], ...]:
    """Create case-insensitive regex patterns (for non-literal matching)."""
    return tuple(re.compile(expr, re.IGNORECASE) for expr in expressions)
```

Using `re.escape()` for literal substrings prevents regex injection from keywords like "C++" or "C#". Use `_regex_patterns()` only when actual regex features are needed (e.g., word boundaries, alternation).

### Anti-Patterns to Avoid

- **Regex word boundaries for VM names:** FR-3.3 explicitly requires substring matching. `\bSQL\b` would miss "CADSRVSQL001". Use `re.search()` without word boundaries.
- **Hardcoded DRR ratios in rules:** Rules should reference category/subcategory pairs, NOT embed DRR values. The DRRTable service provides the ratio lookup. Rules and ratios change independently.
- **Mutation of input DataFrame:** Always return a copy. The ingestion DataFrame may be reused if the user re-classifies.
- **Complex regex when simple substring suffices:** Most patterns are literal substrings ("SQL", "ORACLE"). Only use regex for patterns that genuinely need it (e.g., "MSSQL|MS-SQL").

## Default Rule Set Design

### Priority Tiers (from ARCHITECTURE.md: Database > Application > Infrastructure > OS fallback > Default)

| Tier | Priority Range | Description |
|------|---------------|-------------|
| 1: Database | 100-199 | SQL, Oracle, MongoDB, PostgreSQL, SAP, DB2 |
| 2: Application-specific | 200-299 | Healthcare (EMR/EHR), Email (Exchange), VDI (Citrix/Horizon) |
| 3: Infrastructure services | 300-399 | Backup (Veeam), Containers (Docker/K8s), Web Servers, File Servers |
| 4: Logging/Analytics | 400-499 | FortiNet, Elastic, Splunk, Zabbix, Centreon |
| 5: OS-based fallback | 900-949 | Windows Server -> Virtual Machines, Linux -> Virtual Machines |
| 6: Default | 999 | Unknown (Reducible) DRR=5 |

### Recommended Rules (28 DRR categories to cover)

Based on analysis of 610 real VM names and 40 unique OS values from samples:

```
Priority 100: Database/Oracle
  vm_name_patterns: ["ORACLE"]  (avoid "ORA" alone - matches LORADB, LORANETv2)

Priority 101: Database/Microsoft SQL
  vm_name_patterns: ["SQL", "MSSQL"]
  NOTE: SQL is broadly used, catches CADSRVSQL001, CIGES-SQL, CIGES-SQLP, etc.
  Must be AFTER Oracle (priority 100) so "ORACLESQL" goes to Oracle first.

Priority 102: Database/My SQL / NoSQL
  vm_name_patterns: ["MYSQL", "NOSQL", "MARIADB"]
  NOTE: MariaDB is a MySQL fork, maps to same DRR category.

Priority 103: Database/DB2
  vm_name_patterns: ["DB2"]

Priority 104: Database/MongoDB
  vm_name_patterns: ["MONGODB", "MONGO"]

Priority 105: Database/PostgreSQL
  vm_name_patterns: ["PGSQL", "POSTGRES", "POSTGRESQL"]
  subcategory: "PostgreSQL"  (DRRTable.from_csv() strips the CSV newline)

Priority 106: Database/Prometheus
  vm_name_patterns: ["PROMETHEUS"]

Priority 107: Database/SAP HANA(S4)
  vm_name_patterns: ["HANA", "S4HANA"]
  NOTE: Use regex for SAP.*HANA to catch "SAP-HANA-01" etc.

Priority 108: Database/SAP Traditional (R/3 / ECC)
  vm_name_patterns: ["SAP"]
  NOTE: Do NOT include "ABAC" (Swiss Abacus ERP, not SAP). "CONSAPPT"
  contains "SAP" but this is acceptable (conservative sizing).

Priority 200: HealthCare/EMR/EHR
  vm_name_patterns: ["EPIC", "MCKESSON", "EMR", "EHR"]

Priority 210: Email/Domino/Notes, Exchange, etc.
  vm_name_patterns: ["EXCHANGE", "DOMINO", "ZIMBRA", "SENDMAIL"]
  NOTE: Avoid "EX" - too short, matches EXTRANET, APEXP, etc.
  Avoid "NOTES" - too generic.

Priority 220: VDI/Full Clone / MCS (Citrix)
  vm_name_patterns: ["CITRIX", "CIT", "MCS"]
  NOTE: "CIT" matches many CIGES VMs (CITADM, CITAP, CITAPP, CITCLR, etc.)
  These are genuinely Citrix infrastructure VMs. 26 matches in sample.

Priority 221: VDI/Linked Clone / PVS (Citrix)
  vm_name_patterns: ["PVS"]

Priority 222: VDI/Instant Clone
  vm_name_patterns: ["HORIZON"]
  NOTE: HORIZON matches 5 VMs. VMware Horizon typically uses instant clone.

Priority 223: VDI/VDI Profiles
  vm_name_patterns: ["VDI.*PROFIL", "PROFIL.*VDI"]
  NOTE: OIK_VDI-PROFIL matches. Generic "PROFIL" without VDI context
  should not match here.

Priority 300: VM Replication/Veeam, Zerto, RP4VM
  vm_name_patterns: ["VEEAM", "VBR", "ZERTO", "RP4VM"]
  NOTE: 28 VMs match backup-related patterns. vbr-* VMs are Veeam proxies.

Priority 310: Containers/Kubernetes, OpenShift, Docker, Tanzu
  vm_name_patterns: ["DOCKER", "KUBERNETES", "K8S", "OPENSHIFT", "TANZU"]

Priority 320: Web Servers/Content included
  vm_name_patterns: ["WEB", "WWW", "APACHE", "NGINX", "IIS"]
  NOTE: 15 VMs match WEB/WWW patterns. Default to "Content included" (DRR=5).

Priority 330: File/General Purpose
  vm_name_patterns: ["MFILES", "FILE"]
  NOTE: Put MFILES before generic FILE pattern. OIK_FILE1 matches.

Priority 340: File/Content Servers (Git, SharePoint)
  vm_name_patterns: ["GIT", "GITLAB", "SHAREPOINT"]

Priority 350: File/Developer Workspaces (DevOps)
  vm_name_patterns: ["DEVOPS", "JENKINS", "ANSIBLE"]

Priority 360: File/Archive / Backup / Compressed / Encrypted
  vm_name_patterns: ["ARCHIVE"]
  NOTE: "BACKUP" overlaps with VM Replication (priority 300). Veeam-specific
  VMs go to VM Replication first due to lower priority number.

Priority 400: Logging - Analytics/FortiNet, Elastic Search, Splunk, ELK
  vm_name_patterns: ["ELASTIC", "ELK", "SPLUNK", "FORTIANALYZER", "FORTIMANAGER",
                      "ZABBIX", "CENTREON", "OBSERVIUM", "GRAFANA"]
  os_patterns: ["FORTI"]
  NOTE: OS field catches FortiNet appliances (FAZ, FMG) even when VM name
  doesn't contain "FORTI". Single DRR category covers all logging/analytics.

Priority 500: Boot from SAN
  vm_name_patterns: ["BOOTSAN", "SANBOOT"]
  NOTE: Likely no matches in sample data. Keep for completeness.

Priority 900: OS Fallback - Windows Server -> Virtual Machines
  os_patterns: ["WINDOWS SERVER"]
  category: Virtual Machines / VMware / Hyper-V / KVM

Priority 905: OS Fallback - Windows Desktop -> Virtual Machines
  os_patterns: ["WINDOWS 10", "WINDOWS 11", "WINDOWS 7"]
  category: Virtual Machines / VMware / Hyper-V / KVM

Priority 910: OS Fallback - Linux -> Virtual Machines
  os_patterns: ["LINUX", "UBUNTU", "CENTOS", "DEBIAN", "RED HAT", "SUSE",
                "ALMA", "ROCKY", "ORACLE LINUX", "FREEBSD"]
  category: Virtual Machines / VMware / Hyper-V / KVM

Priority 920: OS Fallback - VMware/ESXi -> Virtual Machines
  os_patterns: ["VMWARE", "ESXI", "PHOTON"]
  category: Virtual Machines / VMware / Hyper-V / KVM

Priority 999: Default
  Always matches. Unknown (Reducible), DRR=5
```

### Verified DRR Subcategory Strings

Verified by running `DRRTable.from_csv()` against actual `samples/DRR.csv`. These are the EXACT subcategory strings that rules must use to match DRR lookups:

| Category | Subcategory (exact string) | DRR |
|----------|---------------------------|-----|
| Database | Oracle | 5.0 |
| Database | Microsoft SQL | 5.0 |
| Database | My SQL / NoSQL | 5.0 |
| Database | DB2 | 1.5 |
| Database | MongoDB | 1.5 |
| Database | PostgreSQL | 1.5 |
| Database | Prometheus | 1.5 |
| Database | SAP HANA(S4) | 2.0 |
| Database | SAP Traditional (R/3 / ECC) | 5.0 |
| HealthCare | EMR/EHR (Epic, McKesson) | 3.0 |
| File | General Purpose | 2.0 |
| File | Archive / Backup / Compressed / Encrypted / Rich Media / ISO / PACS / CAD | 1.0 |
| File | Content Servers (Git, Sharepoint) | 2.0 |
| File | Developer Workspaces (DevOps) | 2.0 |
| VDI | Full Clone / MCS (Citrix) | 8.0 |
| VDI | Linked Clone / PVS (Citrix) | 2.0 |
| VDI | Instant Clone | 1.0 |
| VDI | VDI Profiles | 2.0 |
| Logging - Analytics | FortiNet, Elastic Search, Splunk, ELK, etc | 1.5 |
| Email | Domino/Notes, Exchange, Sendmail, Zimbra, etc | 2.0 |
| Containers | Kubernetes, OpenShift, Docker, Tanzu, etc | 2.0 |
| Virtual Machines | VMware / Hyper-V / KVM - No Database, File nor Email | 5.0 |
| VM Replication | Veeam, Zerto, RP4VM | 1.5 |
| Boot from SAN | Linux, VMware, Windows - OS Boot | 1.5 |
| Web Servers | Content included | 5.0 |
| Web Servers | Content not included | 1.5 |
| Unknown (Reducible) | Unknown (Reducible) | 5.0 |
| Custom DRR | Custom DRR | 3.0 |

Note: "PostgreSQL" subcategory is clean (DRRTable.from_csv() strips the embedded newline from the CSV). No special handling needed in rules.

### False Positive Analysis (from actual sample data)

| Pattern | False Positive Risk | Example | Mitigation |
|---------|-------------------|---------|------------|
| "ORA" | HIGH | OIK_LORADB, OIK_LORANETv2, ORAP-COMMUNES | Use "ORACLE" instead of "ORA" |
| "SAP" | MEDIUM | CIGES-CONSAPPT, CIGES-GISAPP | "GISAPP" contains "SAP" at boundary; "CONSAPPT" acceptable |
| "EX" | HIGH | EXTRANET, APEXP, APEXT | Use "EXCHANGE" not "EX" |
| "SQL" | LOW | Broadly correct - SQL in VM name almost always means SQL Server | Keep as-is |
| "CIT" | LOW for Citrix infra | CITADM, CITAPP, etc. are genuinely Citrix | Keep as-is |
| "DB" | MEDIUM | NESTDB, DPODB, SITDB could be app DBs not specific DB engines | Only use in combination patterns |
| "ABAC" | MEDIUM | Abacus (Swiss ERP) VMs, not SAP | Do NOT use as SAP pattern |
| "FILE" | LOW | OIK_FILE1, MFILES (M-Files doc mgmt) | MFILES matches File/General Purpose (acceptable) |
| "BACKUP" | LOW | BACKUP-DC1, BACKUP-DC2 are backup-related | Place Veeam/Zerto rules (priority 300) before generic backup (360) |
| "GIT" | LOW | CIGES-GIT, OIK_GITLAB genuinely Git servers | Keep as-is |

### Special Cases in Sample Data

1. **vCLS VMs (6 matches):** VMware Cluster Services VMs. OS field "VMware Photon CRX" catches them via OS fallback -> Virtual Machines.
2. **VxRail Manager VMs (3 matches):** VxRail management appliances. Falls through to OS fallback -> Virtual Machines.
3. **Template VMs (17 matches):** Should already be filtered out by ingestion (Phase 2, is_template flag). VMs with "Template" in name but is_template=False should be classified normally.
4. **TODELETE VMs (17 matches):** Marked for deletion. Still active VMs that should be classified normally.
5. **AZURE VMs (15 matches):** Azure AD Connect or Azure-related appliances. Falls through to OS fallback -> Virtual Machines.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pattern matching | Custom substring search loops | Compiled `re.Pattern` with `re.IGNORECASE` | Handles case-insensitive matching in one call, well-tested |
| DRR ratio lookup | Embed ratios in rules | `DRRTable.get_ratio(category, subcategory)` | Ratios change independently of rules |
| Rule ordering | Manual index management | `sorted(rules, key=lambda r: r.priority)` + first-match-wins | Clean, maintainable, easy to reorder |
| Classification results | Ad-hoc dict/tuple | `ClassificationResult` dataclass | Type-safe, self-documenting |

**Key insight:** Rules define WHAT category a VM belongs to. DRRTable defines WHAT ratio that category gets. These are separate concerns. Never embed DRR values in classification rules.

## Common Pitfalls

### Pitfall 1: Overly Short Patterns Causing False Positives

**What goes wrong:** Using "ORA" to match Oracle catches "LORADB", "ORAP-COMMUNES". Using "EX" for Exchange catches "EXTRANET", "APEXP".
**Why it happens:** VM naming conventions embed short keywords within longer names.
**How to avoid:** Use longer, more specific patterns ("ORACLE" not "ORA", "EXCHANGE" not "EX"). Test every rule against the full 610-VM dataset.
**Warning signs:** Unexpectedly high match count for a category.

### Pitfall 2: Priority Order Bugs

**What goes wrong:** A generic rule (e.g., OS fallback "Windows Server") matches before a specific rule (e.g., "SQL Server" on Windows).
**Why it happens:** Rules not properly sorted by priority, or priority values not carefully assigned.
**How to avoid:** Test with VMs that should match specific rules AND have Windows Server OS. Verify the specific rule wins.
**Warning signs:** Too many VMs classified as "Virtual Machines" when they should be Database/Application.

### Pitfall 3: Case Sensitivity

**What goes wrong:** "cadsrvsql001" (lowercase) doesn't match "SQL" pattern.
**Why it happens:** Forgot `re.IGNORECASE` flag, or used `str.find()` without `.upper()`.
**How to avoid:** Always compile patterns with `re.IGNORECASE`. Test with mixed-case VM names from real data (sample has: "cig-cent-int-p-01", "ciges-phenix", "ciges-poller3", "ciges-TST2-07").
**Warning signs:** VMs with lowercase names get classified as "Unknown."

### Pitfall 4: NaN/Empty OS Field

**What goes wrong:** OS-based fallback rules crash or don't match when OS field is NaN or empty string.
**Why it happens:** Some VMs (especially in RVTools) have NaN OS field when VMware Tools is not installed.
**How to avoid:** Convert NaN to empty string before classification. Beware that `str(float('nan'))` produces "nan" which could accidentally match patterns. Use explicit check: `os_name if pd.notna(os_name) else ""`.
**Warning signs:** VMs with no OS getting classified incorrectly, or "nan" string matching patterns.

### Pitfall 5: Abacus (ABAC) vs SAP Confusion

**What goes wrong:** Swiss accounting software Abacus VMs (30+ in sample) get classified as SAP.
**Why it happens:** "ABAC" is a common prefix in Swiss IT for Abacus ERP, not SAP's ABAP.
**How to avoid:** Do NOT use "ABAC" as a SAP pattern. Only match "SAP", "HANA", "S4HANA", "R3", "ECC" for SAP categories. ABAC VMs should fall through to OS fallback (Virtual Machines, DRR=5).
**Warning signs:** Large number of VMs classified as SAP when the customer is not a SAP shop.

### Pitfall 6: Regex vs Literal Substring Confusion

**What goes wrong:** Using `re.compile("C++")` which interprets `+` as regex quantifier.
**Why it happens:** Mixing literal substrings with regex patterns.
**How to avoid:** Use `re.escape()` for literal keywords. Only use raw regex when features like alternation or character classes are needed.
**Warning signs:** Patterns silently fail to match or match unexpected strings.

### Pitfall 7: Subcategory String Mismatch with DRRTable

**What goes wrong:** Classification assigns a subcategory that does not exist in DRRTable, causing lookup to return default 5.0 instead of correct ratio.
**Why it happens:** Typo in subcategory string, or mismatch between rule and DRR.csv.
**How to avoid:** Use the exact strings from the Verified DRR Subcategory Strings table above. Add a test that verifies every rule's (category, subcategory) exists in DRRTable.
**Warning signs:** DRR ratios not matching expected values for certain categories.

## Code Examples

### Building the Default Rule Set

```python
# Source: derived from samples/DRR.csv categories + analysis of 610 sample VMs

def build_default_rules() -> list[ClassificationRule]:
    """Build the default classification rule set covering all DRR categories."""
    return [
        # === Tier 1: Database (priority 100-199) ===
        ClassificationRule(
            name="Oracle Database",
            category="Database",
            subcategory="Oracle",
            priority=100,
            vm_name_patterns=_patterns("ORACLE"),
        ),
        ClassificationRule(
            name="Microsoft SQL",
            category="Database",
            subcategory="Microsoft SQL",
            priority=101,
            vm_name_patterns=_patterns("SQL", "MSSQL"),
        ),
        ClassificationRule(
            name="MongoDB",
            category="Database",
            subcategory="MongoDB",
            priority=104,
            vm_name_patterns=_patterns("MONGODB", "MONGO"),
        ),
        ClassificationRule(
            name="PostgreSQL",
            category="Database",
            subcategory="PostgreSQL",  # DRRTable strips CSV newline
            priority=105,
            vm_name_patterns=_patterns("PGSQL", "POSTGRES", "POSTGRESQL"),
        ),
        # ... (continue for all 28 categories)

        # === Tier 5: OS Fallback (priority 900-949) ===
        ClassificationRule(
            name="Windows Server (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=900,
            os_patterns=_regex_patterns(r"windows server"),
        ),
        ClassificationRule(
            name="Linux (OS fallback)",
            category="Virtual Machines",
            subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
            priority=910,
            os_patterns=_regex_patterns(
                r"linux|ubuntu|centos|debian|red hat|suse|alma|rocky|oracle linux"
            ),
        ),

        # === Tier 6: Default (priority 999) ===
        ClassificationRule(
            name="default",
            category="Unknown (Reducible)",
            subcategory="Unknown (Reducible)",
            priority=999,
            vm_name_patterns=_regex_patterns(r".*"),  # Matches everything
        ),
    ]
```

### Integration with Ingestion Pipeline

```python
# Typical usage in the session controller:
from store_predict.pipeline.ingestion import ingest_file
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)

# After file upload:
df = ingest_file(uploaded_path)

# Classification:
registry = RuleRegistry(build_default_rules())
classified_df = classify_dataframe(df, registry)

# classified_df now has columns:
# vm_name, os_name, provisioned_mib, in_use_mib, ...
# + workload_category, workload_subcategory, classification_rule, classification_confidence
```

### Testing Pattern: Rule-DRRTable Consistency

```python
# Test that every rule's category/subcategory exists in DRRTable
def test_rule_categories_exist_in_drr(drr_table: DRRTable) -> None:
    """Every rule must reference a valid DRR category/subcategory."""
    drr_categories = {
        (e.category, e.subcategory) for e in drr_table.entries
    }
    for rule in build_default_rules():
        key = (rule.category, rule.subcategory)
        assert key in drr_categories, (
            f"Rule '{rule.name}' references ({rule.category}, {rule.subcategory}) "
            f"which does not exist in DRR table"
        )
```

### Testing Pattern: Rule Coverage Test

```python
# Test that every DRR category has at least one matching rule
def test_all_drr_categories_covered(drr_table: DRRTable) -> None:
    """Every DRR category/subcategory must have at least one rule."""
    registry = RuleRegistry(build_default_rules())
    rule_categories = {
        (r.category, r.subcategory) for r in registry._rules
    }
    drr_categories = {
        (e.category, e.subcategory) for e in drr_table.entries
    }
    uncovered = drr_categories - rule_categories
    # Allow "Custom DRR" to be uncovered (user-assigned only)
    uncovered.discard(("Custom DRR", "Custom DRR"))
    assert uncovered == set(), f"DRR categories without rules: {uncovered}"
```

### Testing Pattern: Sample Data Classification

```python
# Test classification against real 610-VM sample
def test_classify_liveoptics_sample(liveoptics_xlsx_path: Path) -> None:
    """Classify all 610 VMs and verify >80% reasonable matches."""
    from store_predict.pipeline.ingestion import ingest_file

    df = ingest_file(liveoptics_xlsx_path)
    registry = RuleRegistry(build_default_rules())
    result = classify_dataframe(df, registry)

    # Check no VMs are unclassified (all should have a category)
    assert result["workload_category"].notna().all()

    # Check distribution is reasonable
    category_counts = result["workload_category"].value_counts()

    # "Unknown (Reducible)" should be less than 20% of total
    unknown_pct = category_counts.get("Unknown (Reducible)", 0) / len(result)
    assert unknown_pct < 0.20, f"Too many unknown: {unknown_pct:.1%}"

    # Specific known VMs should classify correctly
    sql_vms = result[result["vm_name"].str.upper().str.contains("SQL")]
    assert (sql_vms["workload_category"] == "Database").all()
```

### Testing Pattern: Specific Rule Tests (per project convention: real objects, no mocks)

```python
def test_sql_substring_match() -> None:
    """FR-3.3: CADSRVSQL001 must match SQL rule via substring."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("CADSRVSQL001", "Microsoft Windows Server 2019 (64-bit)")
    assert result.category == "Database"
    assert result.subcategory == "Microsoft SQL"
    assert result.confidence == "rule_match"


def test_fortinet_os_match() -> None:
    """FortiNet appliances detected via OS field."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify(
        "CIGES-FAZ",
        "FortiAnalyzer-VM64 v7.4.10-build2778 260126 (GA.M)",
    )
    assert result.category == "Logging - Analytics"


def test_windows_server_fallback() -> None:
    """Generic Windows Server VM falls to OS fallback, not Unknown."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify(
        "CIGES-SERVICES",
        "Microsoft Windows Server 2022 (64-bit)",
    )
    assert result.category == "Virtual Machines"
    assert result.confidence == "os_fallback"


def test_oracle_not_lora() -> None:
    """OIK_LORADB should NOT match Oracle (uses 'ORACLE' not 'ORA')."""
    registry = RuleRegistry(build_default_rules())
    result = registry.classify("OIK_LORADB", "Oracle Linux 9 (64-bit)")
    assert result.category != "Database" or result.subcategory != "Oracle"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ML-based classification | Rules-based pattern matching | v1 design decision | Simpler, faster, sufficient for 80%+ accuracy |
| Exact word boundary matching | Substring matching | FR-3.3 requirement | Catches embedded keywords in naming conventions |
| Flat pattern list | Priority-ordered rule registry | Architecture decision | Prevents ambiguous classifications |

**Out of scope for v1:**

- ML-based classification (deferred to v2 per PROJECT.md)
- Fuzzy/approximate matching (not needed - patterns are well-defined)
- User-defined custom rules (Phase 4 handles user overrides per-VM)

## Open Questions

1. **Abacus (ABAC) classification**
   - What we know: ~30 CIGES VMs contain "ABAC" which is Swiss Abacus ERP software
   - What's unclear: Whether customer considers Abacus similar to SAP for DRR purposes
   - Recommendation: Do NOT map ABAC to SAP. Let these fall through to OS-based fallback (Virtual Machines, DRR=5). Users can override in Phase 4's review UI.

2. **Citrix VMs: Full Clone vs Linked Clone**
   - What we know: 26 VMs match "CIT" patterns. DRR has separate entries for Full Clone (DRR=8) and Linked Clone (DRR=2).
   - What's unclear: Cannot determine clone type from VM name or OS field alone.
   - Recommendation: Default Citrix VMs to "VDI/Full Clone / MCS (Citrix)" (DRR=8, optimistic). User can override specific VMs to Linked Clone in review UI.

3. **MariaDB classification**
   - What we know: OIK_MARIADB3, OIK_MARIADB4 exist in sample. DRR.csv has "My SQL / NoSQL" category.
   - What's unclear: Whether MariaDB should map to "My SQL / NoSQL" (DRR=5) or be separate.
   - Recommendation: Map MariaDB to "My SQL / NoSQL" since MariaDB is a MySQL fork. Add "MARIADB" to that rule's patterns.

4. **Web Servers: Content included vs not included**
   - What we know: DRR has two subcategories: "Content included" (DRR=5) and "Content not included" (DRR=1.5).
   - What's unclear: Cannot determine content inclusion from VM name alone.
   - Recommendation: Default to "Content included" (DRR=5, more conservative for sizing). User can override.

## Sources

### Primary (HIGH confidence)

- **Actual sample data** analyzed with pandas:
  - `samples/live-optics.xlsx`: 610 VMs, 40 unique OS values, pattern frequency analysis
  - `samples/rvtools.xlsx`: 24 VMs, 20 with OS data
  - `samples/DRR.csv`: 28 valid entries across 13 top-level categories
- **DRRTable.from_csv() output** verified at runtime: all 28 subcategory strings confirmed exact (PostgreSQL is clean, no newline)
- **Existing codebase**: `pipeline/models.py`, `services/drr_table.py`, `pipeline/ingestion.py`, `pipeline/parsers/columns.py`
- **ARCHITECTURE.md**: Rule Registry pattern (Pattern 2), classification pipeline design
- **REQUIREMENTS.md**: FR-3.1 through FR-3.4 specifications

### Secondary (MEDIUM confidence)

- **Python re module** documentation: `re.compile()`, `re.IGNORECASE`, `re.search()` API (stable stdlib, HIGH confidence)
- **Phase 2 RESEARCH.md**: DataFrame schema, canonical columns, ingestion pipeline output format

### Tertiary (LOW confidence)

- None. All findings verified against actual sample files and existing code.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - no new dependencies, uses stdlib re + existing pandas/dataclasses
- Architecture: HIGH - follows established patterns from ARCHITECTURE.md, verified against real data
- Rule design: HIGH - patterns derived from actual 610-VM sample analysis with false positive verification
- DRR subcategories: HIGH - verified by running DRRTable.from_csv() and inspecting actual output
- Pitfalls: HIGH - false positive patterns verified with real VM names from sample data
- Coverage estimate: MEDIUM - >80% target based on pattern analysis, needs validation with actual classification run

**Research date:** 2026-02-18
**Valid until:** 2026-04-18 (stable domain, pattern matching doesn't evolve rapidly)
