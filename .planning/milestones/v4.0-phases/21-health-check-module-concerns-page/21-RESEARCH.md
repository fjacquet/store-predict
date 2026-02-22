# Phase 21: Health Check Module & Concerns Page - Research

**Researched:** 2026-02-22
**Domain:** VMware health check rules engine + NiceGUI page pattern
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HLT-01 | User sees data quality findings: VMs missing OS info, zero provisioned storage, missing CPU/RAM data, high powered-off VM ratio | Verified: all these fields exist in CANONICAL_COLUMNS and are populated by both parsers. Pure DataFrame comparisons, no new columns needed. |
| HLT-02 | User sees sizing risk findings: large Unknown VMs inflating estimates, high DRR override count, VMs exceeding datastore IOPS budget | Verified: `workload_category`, `provisioned_mib`, `drr`, `peak_iops` all in canonical schema. "IOPS budget" check derived from layout engine's existing `iops_budget_per_ds` concept. |
| HLT-03 | User sees VMware best practice findings: old VM hardware version, VMs without cluster assignment, VMs with missing VMware Tools status | Partially: `cluster` field is in CANONICAL_COLUMNS. `hw_version` and `tools_status` are NOT currently in CANONICAL_COLUMNS — parser extension required. LiveOptics lacks these columns — graceful fallback needed. |
</phase_requirements>

---

## Summary

Phase 21 builds a pure-pipeline health check engine (`pipeline/health_checks.py`) following the same `layout_engine.py` pattern, then wires it to a new `/concerns` NiceGUI page following the `layout_page.py` pattern. The module scans the current session DataFrame — always starting from `load_session_data()` so user edits to workload assignments are reflected — and returns a structured list of `HealthFinding` objects grouped by severity (Critical/Warning/Info).

Two of the three requirement groups (HLT-01, HLT-02) are fully implementable from data already in CANONICAL_COLUMNS. HLT-03 requires extending the RVTools parser to read two additional vInfo columns (`HW version`, `Tools Status`) and adding them to CANONICAL_COLUMNS before the health check module can use them. LiveOptics exports do not contain these columns; the parser must set them to sentinel values (`hw_version=0`, `tools_status=""`) so health checks can detect "data not available" and skip those checks silently.

The concerns page is the simplest new-page pattern in the v4.0 milestone: no reactive inputs, no downloads, no side-panel settings. Page visits trigger a fresh health check computation from session state. The result is rendered as a grouped list of severity-tagged cards.

**Primary recommendation:** Implement in two tasks: (1) parser extension + CANONICAL_COLUMNS + `health_checks.py` module with all checks and tests, (2) `/concerns` page + navigation link + i18n keys.

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pandas` | >=2.2 (already installed) | DataFrame scanning for health check conditions | Already used for all pipeline data operations |
| `dataclasses` (stdlib) | Python 3.12 | `@dataclass(frozen=True)` for `HealthFinding`, `HealthCheckResult` | Matches `LayoutProposal`, `PlacementConstraints` pattern in existing code |
| `nicegui` | >=3.4 (already installed) | `/concerns` page rendering | All pages use NiceGUI |
| `python-i18n` | >=0.3.9 (already installed) | i18n keys for all user-facing strings | Project convention — ALL user-facing strings go through `t()` |

**No changes to `pyproject.toml` required.** This is confirmed — all health check logic is pure pandas + stdlib.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `enum.StrEnum` (stdlib) | Python 3.11+ | `Severity` enum for Critical/Warning/Info | Matches `FileFormat` pattern in `pipeline/models.py` |
| `typing.TYPE_CHECKING` | stdlib | Lazy import of pandas for type hints only | Matches all existing pipeline modules |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dataclass frozen=True findings | Pydantic models | Pydantic adds no value here; existing codebase uses dataclasses for pipeline models |
| pandas-based checks | Pure Python loops | Pandas is already imported; vectorized ops are faster and more readable for DataFrame scans |

**Installation:** None required — no new packages.

---

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/pipeline/
├── health_checks.py      # NEW — pure pipeline module, zero UI imports
├── parsers/
│   ├── columns.py        # MODIFIED — add hw_version, tools_status to CANONICAL_COLUMNS + RVTOOLS_ALIASES
│   └── rvtools.py        # MODIFIED — read HW version and Tools Status columns

src/store_predict/ui/
├── layout.py             # MODIFIED — add /concerns nav link
├── pages/
│   └── concerns.py       # NEW — /concerns page

src/store_predict/i18n/locales/
├── en.yaml               # MODIFIED — add concerns.* and health.* keys
└── fr.yaml               # MODIFIED — add concerns.* and health.* keys (French primary)

tests/
└── test_health_checks.py # NEW — tests for all health check functions
```

### Pattern 1: HealthFinding Dataclass (frozen)

**What:** Immutable data object returned by each check function, following `DatastoreRecommendation` pattern.
**When to use:** Every health check returns a list of these — never returns strings or dicts directly.

```python
# Source: pipeline/layout_models.py pattern (DatastoreRecommendation frozen=True)
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "HealthCheckResult",
    "HealthFinding",
    "Severity",
]


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class HealthFinding:
    """A single health concern with severity and context."""

    check_id: str           # e.g. "data_quality.zero_provisioned"
    severity: Severity
    title: str              # i18n key — caller passes t("health.zero_provisioned.title")
    detail: str             # i18n key with optional substitutions
    affected_count: int     # Number of VMs triggering this finding
    affected_vms: tuple[str, ...]  # Sample VM names (max 5, for display)


@dataclass(frozen=True)
class HealthCheckResult:
    """Aggregated findings from all health checks."""

    findings: tuple[HealthFinding, ...]
    total_vms_checked: int
    has_data: bool  # False if session is empty — page shows "no data" state

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)
```

### Pattern 2: Pure Pipeline Entry Point

**What:** A single `run_health_checks(df)` function that accepts a DataFrame and returns `HealthCheckResult`.
**When to use:** Called once per page visit in `concerns.py` — never cached in session state.

```python
# Source: layout_engine.py pattern (generate_all_proposals signature)
import pandas as pd

def run_health_checks(df: pd.DataFrame) -> HealthCheckResult:
    """Run all health checks on the session DataFrame.

    Args:
        df: Canonical DataFrame from load_session_data().
            Must include is_powered_on, is_template columns.

    Returns:
        HealthCheckResult with all findings.
    """
    if df is None or df.empty:
        return HealthCheckResult(findings=(), total_vms_checked=0, has_data=False)

    # ALWAYS filter before checks — only powered-on, non-template VMs
    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]
    all_findings: list[HealthFinding] = []

    # Data quality checks
    all_findings.extend(_check_zero_provisioned(active))
    all_findings.extend(_check_missing_os(active))
    all_findings.extend(_check_missing_cpu_ram(active))
    all_findings.extend(_check_powered_off_ratio(df))  # uses full df for ratio

    # Sizing risk checks
    all_findings.extend(_check_unknown_vm_ratio(active))
    all_findings.extend(_check_large_unknown_vms(active))

    # VMware best practice checks
    all_findings.extend(_check_no_cluster(active))
    all_findings.extend(_check_hw_version(active))    # only if hw_version data present
    all_findings.extend(_check_tools_status(active))  # only if tools_status data present

    return HealthCheckResult(
        findings=tuple(all_findings),
        total_vms_checked=len(active),
        has_data=True,
    )
```

### Pattern 3: Individual Check Function Structure

**What:** Each check is an internal function `_check_X(df) -> list[HealthFinding]`.
**When to use:** All check functions follow this exact signature to keep `run_health_checks` clean.

```python
# Source: layout_engine.py internal function pattern (_consolidation_strategy, etc.)
_LARGE_VM_THRESHOLD_MIB = 1024 * 1024  # 1 TiB

def _check_large_unknown_vms(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag Unknown VMs larger than 1 TiB provisioned storage.

    Large Unknown VMs use conservative DRR=5 by default which may be wrong;
    if the VM is actually a database, the real DRR could be much higher.
    """
    unknown = df[
        (df["workload_category"].str.startswith("Unknown")) &
        (pd.to_numeric(df["provisioned_mib"], errors="coerce").fillna(0) >= _LARGE_VM_THRESHOLD_MIB)
    ]
    if unknown.empty:
        return []
    names = tuple(unknown["vm_name"].head(5).tolist())
    return [HealthFinding(
        check_id="sizing_risk.large_unknown_vms",
        severity=Severity.WARNING,
        title="health.large_unknown_vms.title",
        detail="health.large_unknown_vms.detail",
        affected_count=len(unknown),
        affected_vms=names,
    )]
```

### Pattern 4: `/concerns` Page Structure

**What:** NiceGUI page that calls `load_session_data()`, runs checks, renders grouped results.
**When to use:** Exactly follows `layout_page.py` page entry point pattern.

```python
# Source: layout_page.py @ui.page entry point pattern
from nicegui import app, ui
from store_predict.ui.layout import layout
from store_predict.ui.state import load_session_data
from store_predict.pipeline.health_checks import run_health_checks, Severity

@ui.page("/concerns")
async def concerns_page() -> None:
    """Health check concerns page."""
    await ui.context.client.connected()

    df = load_session_data()

    if df is None or df.empty:
        with layout("StorePredict - Concerns"), ...:
            ui.icon("health_and_safety", size="3rem").classes("text-gray-400")
            ui.label(t("concerns.no_data")).classes("text-xl text-gray-500")
            ui.button(t("report.go_to_upload"), ...).classes("bg-blue-700 text-white")
        return

    result = run_health_checks(df)

    with layout("StorePredict - Concerns"), ui.column().classes("w-full p-4 gap-4"):
        ui.label(t("concerns.title")).classes("text-2xl font-bold")
        _render_summary_badges(result)
        if not result.findings:
            ui.label(t("concerns.no_findings")).classes("text-green-600")
        else:
            _render_findings_by_severity(result.findings)
```

### Pattern 5: CANONICAL_COLUMNS Extension

**What:** Add `hw_version` and `tools_status` to CANONICAL_COLUMNS before writing health checks.
**When to use:** The whitelist strips unknown columns silently — always add to `columns.py` first.

```python
# Source: pipeline/parsers/columns.py CANONICAL_COLUMNS list
# Add after existing columns (before row_index):
CANONICAL_COLUMNS: list[str] = [
    # ... existing columns ...
    "hw_version",       # int: vmx hardware level (0 = not available)
    "tools_status",     # str: "toolsOk"|"toolsOld"|"toolsNotInstalled"|"toolsNotRunning"|""
    "row_index",
]

# Add to RVTOOLS_ALIASES:
RVTOOLS_ALIASES: dict[str, list[str]] = {
    # ... existing aliases ...
    "hw_version": ["HW version", "Hardware version", "HW Version"],
    "tools_status": ["Tools Status", "VMware Tools Status"],
}
```

### Pattern 6: RVTools Parser Extension for Optional Columns

**What:** Read `hw_version` and `tools_status` from vInfo sheet — graceful fallback if missing.
**When to use:** Matches existing optional column pattern in `rvtools.py`.

```python
# Source: rvtools.py optional column pattern (datacenter, cluster handling)
# In parse_rvtools():

# hw_version: integer vmx level, 0 if not available
if col_map.get("hw_version"):
    result["hw_version"] = (
        pd.to_numeric(df[col_map["hw_version"]], errors="coerce").fillna(0).astype(int)
    )
else:
    result["hw_version"] = 0

# tools_status: string, empty if not available
if col_map.get("tools_status"):
    result["tools_status"] = df[col_map["tools_status"]].fillna("").astype(str)
else:
    result["tools_status"] = ""
```

```python
# In parse_liveoptics (both xlsx and csv variants):
# These columns don't exist in LiveOptics exports — always sentinel values
result["hw_version"] = 0
result["tools_status"] = ""
```

### Pattern 7: Navigation Link Addition

**What:** Add `/concerns` link to `layout.py` header row.
**When to use:** Every new page must add a nav link — same pattern as existing links.

```python
# Source: ui/layout.py
# In the header row, after layout.layout link:
ui.link(t("layout.concerns"), "/concerns").classes("text-white no-underline hover:underline")
```

And in `en.yaml` / `fr.yaml` under `layout:`:
```yaml
# en.yaml
layout:
  concerns: Concerns

# fr.yaml
layout:
  concerns: Alertes
```

### Anti-Patterns to Avoid

- **Re-running classification in the concerns page:** Never call `classify_dataframe()` on the page. Always start with `load_session_data()`. Re-classifying loses the user's manual edits.
- **Caching HealthCheckResult in session storage:** Do not store findings in `app.storage.tab`. Findings must be recomputed on each page visit — the user may have edited workload assignments between visits.
- **Flagging powered-off VMs for best practice violations:** Filter to `is_powered_on == True, is_template == False` BEFORE passing to best practice checks. A powered-off VM from 2019 with old HW version is not a current risk.
- **Using `unittest.mock` in tests:** Project convention forbids mock. Use real DataFrames with synthetic data in test helper functions.
- **Asserting finding title strings directly in tests:** Titles are i18n keys (strings like `"health.zero_provisioned.title"`). Test for `check_id` and `severity` instead of title text.
- **`hw_version` health check on LiveOptics data:** The sentinel value is `0`. Health checks must skip checks when `hw_version == 0` (data not available) rather than flagging all VMs as having version 0 (very old).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session state persistence | Custom session dict for findings | `load_session_data()` from `ui/state.py` | Already handles NaN→None, JSON serialization, tab-scoped storage |
| Finding severity display | Custom badge colors | NiceGUI `.classes()` with Tailwind `bg-red-100`, `bg-yellow-100`, `bg-blue-100` | Already used throughout the UI |
| DataFrame type coercion | Custom float/int parsing | `pd.to_numeric(val, errors='coerce').fillna(0)` | Already in use in `rvtools.py`, `calculation.py` |
| Hardware version mapping | External lookup table / API | Hardcoded `HW_VERSION_TO_MIN_ESXI` dict | Static VMware mapping that changes once per major release |
| i18n key lookup | Custom translation function | `t("key")` from `store_predict.i18n` | Project convention; all user-facing strings go through `t()` |

**Key insight:** Health checks are pure DataFrame comparisons. The entire complexity is in correctly handling sentinel values (0, "", None) from session round-trips and LiveOptics gaps — not in the logic itself.

---

## Complete Health Check Inventory

### Data Quality Checks (HLT-01)

| Check ID | Severity | Filter | Condition | Notes |
|----------|----------|--------|-----------|-------|
| `data_quality.missing_os` | Warning | active only | `os_name == ""` | VMs without OS data can't be classified accurately |
| `data_quality.zero_provisioned` | Warning | active only | `provisioned_mib == 0` | Sizing is impossible without provisioned data |
| `data_quality.missing_cpu` | Info | active only | `num_cpus == 0` | Compute sizing estimates unreliable |
| `data_quality.missing_ram` | Info | active only | `memory_mib == 0` | Compute sizing estimates unreliable |
| `data_quality.high_powered_off_ratio` | Info | full df | `(powered_off / total) > 0.30` | >30% powered-off VMs suggests stale environment data |

### Sizing Risk Checks (HLT-02)

| Check ID | Severity | Filter | Condition | Notes |
|----------|----------|--------|-----------|-------|
| `sizing_risk.high_unknown_ratio` | Warning | active only | `(unknown_count / total_active) > 0.25` | >25% Unknown VMs means DRR estimates are conservative guesses |
| `sizing_risk.large_unknown_vms` | Warning | active only | `workload_category.startswith("Unknown") AND provisioned_mib >= 1 TiB` | Big VMs with unknown DRR inflate required capacity estimates |
| `sizing_risk.iops_budget_exceeded` | Warning | active only | `peak_iops > 0 AND peak_iops > layout_iops_budget_per_ds` | Single VM exceeds standard datastore IOPS budget (100K) |

### VMware Best Practice Checks (HLT-03)

| Check ID | Severity | Filter | Condition | Notes |
|----------|----------|--------|-----------|-------|
| `best_practice.no_cluster` | Warning | active only | `cluster == ""` | VM not assigned to a cluster — cannot be migrated with vMotion |
| `best_practice.old_hw_version` | Warning | active only | `hw_version > 0 AND hw_version < 17` | HW version below vHW 17 (ESXi 7.0) — upgrade before migration |
| `best_practice.very_old_hw_version` | Critical | active only | `hw_version > 0 AND hw_version < 14` | HW version below vHW 14 (ESXi 6.7) — likely incompatible with modern vSphere |
| `best_practice.tools_not_installed` | Critical | active only | `tools_status == "toolsNotInstalled"` | VMware Tools required for migration consistency |
| `best_practice.tools_not_running` | Warning | active only | `tools_status == "toolsNotRunning"` | Tools installed but not running — guest OS issue |
| `best_practice.no_hw_data` | Info | active only | `hw_version == 0 AND source_format == "rvtools"` | HW version column absent from this RVTools export version |

---

## Common Pitfalls

### Pitfall 1: Health Check Re-Running Classification
**What goes wrong:** `/concerns` page calls `classify_dataframe()` instead of `load_session_data()`, discarding all user edits from the Review grid.
**Why it happens:** Natural reflex to "start fresh" with a clean pipeline.
**How to avoid:** The concerns page MUST start with `df = load_session_data()`. The session already contains user-edited `workload_category` values. Never call `classify_dataframe()` in the concerns page.
**Warning signs:** Check IDs for "Unknown VM ratio" go down when user edits workload in Review — but come back up when visiting /concerns.

### Pitfall 2: hw_version Sentinel Zero Mistakenly Flagged
**What goes wrong:** Check fires `hw_version < 14` on ALL VMs from LiveOptics exports (where `hw_version=0`) and reports "very old hardware" on every VM.
**Why it happens:** `0 < 14` is true — the sentinel value triggers the old HW condition.
**How to avoid:** All HW version checks MUST guard with `hw_version > 0`. Pattern: `(df["hw_version"] > 0) & (df["hw_version"] < 17)`.
**Warning signs:** 100% of VMs flagged as "old hardware" on any LiveOptics upload.

### Pitfall 3: Session JSON Round-Trip Type Corruption
**What goes wrong:** `hw_version` stored as int, retrieved as float from JSON. `0.0 > 0` is False, but `0.0 < 14` is True — breaking the guard.
**Why it happens:** JSON has no integer type — all numbers may deserialize as float.
**How to avoid:** Always use `pd.to_numeric(df["hw_version"], errors="coerce").fillna(0).astype(int)` when loading from session. Do this in `run_health_checks()` before any numeric comparison.
**Warning signs:** Guard `hw_version > 0` passes for `0.0` in some Python float edge cases (it actually works correctly for `0.0 > 0` → False, but `int()` cast is safer).

### Pitfall 4: No-Data State Not Handled
**What goes wrong:** User navigates to `/concerns` before uploading a file. `load_session_data()` returns `None`. Calling `run_health_checks(None)` raises `AttributeError`.
**Why it happens:** Pages that only use session data may not handle the None case.
**How to avoid:** `run_health_checks()` must accept `None | pd.DataFrame` and return `HealthCheckResult(findings=(), total_vms_checked=0, has_data=False)` for None input. The page renders a "no data" state card matching `layout_page.py` pattern.
**Warning signs:** 500 error on fresh browser tab visit to `/concerns`.

### Pitfall 5: i18n Key Parity Gaps
**What goes wrong:** Strings appear as raw key names like `"concerns.title"` in French UI because fr.yaml is missing the key.
**Why it happens:** Adding keys to en.yaml without mirroring to fr.yaml. `python-i18n` returns the key string silently when FR key is missing.
**How to avoid:** Add all new `concerns.*`, `health.*`, `layout.concerns` keys to BOTH `en.yaml` and `fr.yaml` in the same commit. The `test_i18n.py` test should be extended with an assertion: `set(en_keys) == set(fr_keys)`.
**Warning signs:** French UI shows English-looking key strings like `"health.zero_provisioned.title"`.

### Pitfall 6: CANONICAL_COLUMNS Not Updated Before Parser Extension
**What goes wrong:** `hw_version` added to `rvtools.py` parser but not to `CANONICAL_COLUMNS` in `columns.py`. The line `return result[CANONICAL_COLUMNS]` at the end of the parser silently strips the new column.
**Why it happens:** CANONICAL_COLUMNS is a whitelist — columns not in the list are dropped.
**How to avoid:** Update `columns.py` FIRST, then update `rvtools.py`. This is a hard ordering constraint.
**Warning signs:** `df["hw_version"]` raises KeyError in health checks despite the parser seemingly setting it.

### Pitfall 7: powered_off VMs Flagged for Best Practice Violations
**What goes wrong:** Health checks flag a VM from 2015 with vmx-11 as "Critical — very old hardware" even though it's been powered off for 3 years and is irrelevant to migration planning.
**Why it happens:** Forgetting to filter before calling best practice check functions.
**How to avoid:** The `active` DataFrame variable in `run_health_checks()` filters BEFORE all checks: `active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]`. Pass `active` to all best practice check functions, never the full `df`.
**Warning signs:** Large number of "old hardware" findings on environments with many powered-off legacy VMs.

---

## Code Examples

### Full run_health_checks() Entry Point

```python
# Source: pipeline/layout_engine.py pattern (generate_all_proposals)
from __future__ import annotations

import pandas as pd

from store_predict.pipeline.health_checks_models import (
    HealthCheckResult,
    HealthFinding,
    Severity,
)

_POWERED_OFF_RATIO_THRESHOLD = 0.30   # 30% powered-off → Info finding
_UNKNOWN_RATIO_THRESHOLD = 0.25       # 25% Unknown → Warning finding
_LARGE_VM_THRESHOLD_MIB = 1024 * 1024 # 1 TiB
_IOPS_BUDGET_PER_DS = 100_000.0       # Standard Dell datastore IOPS budget
_OLD_HW_VERSION = 17                  # vHW 17 = ESXi 7.0 — minimum recommended
_VERY_OLD_HW_VERSION = 14             # vHW 14 = ESXi 6.7 — critical threshold


def run_health_checks(df: pd.DataFrame | None) -> HealthCheckResult:
    """Entry point: run all health checks on the session DataFrame."""
    if df is None or df.empty:
        return HealthCheckResult(findings=(), total_vms_checked=0, has_data=False)

    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]
    findings: list[HealthFinding] = []

    # Data quality
    findings.extend(_check_missing_os(active))
    findings.extend(_check_zero_provisioned(active))
    findings.extend(_check_missing_cpu_ram(active))
    findings.extend(_check_high_powered_off_ratio(df, active))

    # Sizing risk
    findings.extend(_check_high_unknown_ratio(active))
    findings.extend(_check_large_unknown_vms(active))
    findings.extend(_check_iops_budget_exceeded(active))

    # Best practice
    findings.extend(_check_no_cluster(active))
    findings.extend(_check_hw_version(active))
    findings.extend(_check_tools_status(active))

    return HealthCheckResult(
        findings=tuple(findings),
        total_vms_checked=len(active),
        has_data=True,
    )
```

### hw_version Check with Sentinel Guard

```python
# Source: pattern from calculation.py _safe_float() + rvtools.py optional column
def _check_hw_version(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag VMs with old VMware hardware version."""
    hw = pd.to_numeric(df.get("hw_version", 0), errors="coerce").fillna(0).astype(int)

    # Skip check entirely if no HW version data in this export
    if (hw > 0).sum() == 0:
        return []

    has_data = df[hw > 0]

    very_old = has_data[hw[has_data.index] < _VERY_OLD_HW_VERSION]
    if not very_old.empty:
        return [HealthFinding(
            check_id="best_practice.very_old_hw_version",
            severity=Severity.CRITICAL,
            title="health.very_old_hw_version.title",
            detail="health.very_old_hw_version.detail",
            affected_count=len(very_old),
            affected_vms=tuple(very_old["vm_name"].head(5).tolist()),
        )]

    old = has_data[(hw[has_data.index] >= _VERY_OLD_HW_VERSION) & (hw[has_data.index] < _OLD_HW_VERSION)]
    findings = []
    if not old.empty:
        findings.append(HealthFinding(
            check_id="best_practice.old_hw_version",
            severity=Severity.WARNING,
            title="health.old_hw_version.title",
            detail="health.old_hw_version.detail",
            affected_count=len(old),
            affected_vms=tuple(old["vm_name"].head(5).tolist()),
        ))
    return findings
```

### /concerns Page No-Data State (matches layout_page.py)

```python
# Source: layout_page.py no-data pattern (lines 669-682)
if df is None or df.empty:
    with (
        layout("StorePredict - Concerns"),
        ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
        ui.card().classes("p-8 gap-4 items-center text-center"),
    ):
        ui.icon("health_and_safety", size="3rem").classes("text-gray-400")
        ui.label(t("concerns.no_data")).classes("text-xl text-gray-500")
        ui.button(
            t("report.go_to_upload"),
            on_click=lambda: ui.navigate.to("/upload"),
            icon="arrow_forward",
        ).classes("bg-blue-700 text-white")
    return
```

### Test Pattern (no mock — real DataFrames)

```python
# Source: test_layout_engine.py _make_vm() pattern
import pandas as pd
from store_predict.pipeline.health_checks import run_health_checks
from store_predict.pipeline.health_checks_models import Severity


def _make_active_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal active VM DataFrame for testing."""
    defaults = {
        "vm_name": ["test-vm-01"],
        "os_name": ["Windows Server 2022"],
        "workload_category": ["Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"],
        "provisioned_mib": [102400.0],
        "in_use_mib": [51200.0],
        "num_cpus": [4],
        "memory_mib": [8192.0],
        "datacenter": ["DC1"],
        "cluster": ["Cluster-01"],
        "is_powered_on": [True],
        "is_template": [False],
        "hw_version": [19],
        "tools_status": ["toolsOk"],
        "peak_iops": [500.0],
        "avg_iops": [300.0],
        "source_format": ["rvtools"],
        "row_index": [0],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class TestDataQualityChecks:
    def test_zero_provisioned_triggers_warning(self) -> None:
        df = _make_active_df(provisioned_mib=[0.0])
        result = run_health_checks(df)
        ids = {f.check_id for f in result.findings}
        assert "data_quality.zero_provisioned" in ids

    def test_missing_os_triggers_warning(self) -> None:
        df = _make_active_df(os_name=[""])
        result = run_health_checks(df)
        ids = {f.check_id for f in result.findings}
        assert "data_quality.missing_os" in ids


class TestBestPracticeChecks:
    def test_old_hw_version_triggers_warning(self) -> None:
        df = _make_active_df(hw_version=[14])  # ESXi 6.7
        result = run_health_checks(df)
        ids = {f.check_id for f in result.findings}
        assert "best_practice.old_hw_version" in ids

    def test_hw_version_zero_sentinel_skipped(self) -> None:
        """LiveOptics data (hw_version=0) must not trigger any HW version findings."""
        df = _make_active_df(hw_version=[0], source_format=["liveoptics"])
        result = run_health_checks(df)
        ids = {f.check_id for f in result.findings}
        assert "best_practice.old_hw_version" not in ids
        assert "best_practice.very_old_hw_version" not in ids

    def test_powered_off_vms_not_flagged(self) -> None:
        """Powered-off VMs must not trigger best practice findings."""
        df = _make_active_df(hw_version=[11], is_powered_on=[False])
        result = run_health_checks(df)
        ids = {f.check_id for f in result.findings}
        assert "best_practice.very_old_hw_version" not in ids
```

### i18n Key Structure for New Page

```yaml
# en.yaml additions:
layout:
  concerns: Concerns   # nav link

concerns:
  title: "Health Checks & Concerns"
  no_data: "No data uploaded yet. Upload a file to see health check findings."
  no_findings: "No concerns found — environment looks healthy."
  summary_critical: "%{count} Critical"
  summary_warning: "%{count} Warning"
  summary_info: "%{count} Info"
  section_data_quality: "Data Quality"
  section_sizing_risk: "Sizing Risks"
  section_best_practice: "VMware Best Practices"
  affected_vms: "Affected VMs: %{names}"
  affected_count: "%{count} VM(s)"

health:
  missing_os:
    title: "VMs Missing OS Information"
    detail: "%{count} VM(s) have no OS data — classification accuracy reduced."
  zero_provisioned:
    title: "VMs with Zero Provisioned Storage"
    detail: "%{count} VM(s) show 0 MiB provisioned — storage sizing will be incomplete."
  missing_cpu:
    title: "VMs Missing CPU Data"
    detail: "%{count} VM(s) have vCPU count of 0 — compute sizing estimates unreliable."
  missing_ram:
    title: "VMs Missing RAM Data"
    detail: "%{count} VM(s) have RAM of 0 MiB — compute sizing estimates unreliable."
  high_powered_off_ratio:
    title: "High Powered-Off VM Ratio"
    detail: "%{pct}% of VMs are powered off — data may be from a stale environment snapshot."
  high_unknown_ratio:
    title: "High Unknown VM Ratio"
    detail: "%{count} VM(s) (%{pct}%) classified as Unknown — DRR estimates are conservative defaults."
  large_unknown_vms:
    title: "Large Unclassified VMs"
    detail: "%{count} VM(s) over 1 TiB are Unknown — classify these for accurate DRR."
  iops_budget_exceeded:
    title: "VMs Exceeding Datastore IOPS Budget"
    detail: "%{count} VM(s) peak IOPS exceed the standard 100K/datastore budget."
  no_cluster:
    title: "VMs Without Cluster Assignment"
    detail: "%{count} VM(s) are not assigned to a cluster — vMotion migration not possible."
  old_hw_version:
    title: "VMs with Old Hardware Version"
    detail: "%{count} VM(s) are below vHW 17 (ESXi 7.0) — hardware upgrade recommended."
  very_old_hw_version:
    title: "VMs with Very Old Hardware Version (Critical)"
    detail: "%{count} VM(s) are below vHW 14 (ESXi 6.7) — likely incompatible with modern vSphere."
  tools_not_installed:
    title: "VMs Missing VMware Tools"
    detail: "%{count} VM(s) have VMware Tools not installed — required for migration consistency."
  tools_not_running:
    title: "VMs with VMware Tools Not Running"
    detail: "%{count} VM(s) have VMware Tools installed but not running — check guest OS."
  no_hw_data:
    title: "No Hardware Version Data Available"
    detail: "This RVTools export does not include the HW version column — hardware compatibility cannot be assessed."
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Health checks as blocking pipeline step | Health checks as on-demand page-level computation | Architectural decision (Phase 21) | User edits in Review grid are preserved — no re-classification |
| Row identity via vm_name | Row identity via row_index | Phase 20 (Plan 20-01) | Duplicate VM names no longer corrupt health check affected_vms lookups |
| RVTools parser reads only sizing columns | RVTools parser also reads HW version, Tools Status | Phase 21 (Plan 21-01) | Health checks can assess VMware infrastructure readiness from offline data |

**Deprecated/outdated:**
- `hw_version = 0` as "unknown" was historically also used for very old VMs. The sentinel interpretation (0 = data not available from this export) must be documented clearly and guarded in every check function.

---

## Open Questions

1. **Health check module: one file or two (models + engine)?**
   - What we know: `layout_engine.py` (21 KB) and `layout_models.py` (5 KB) are split. Health checks will be smaller.
   - What's unclear: Whether splitting adds clarity or just overhead at this size.
   - Recommendation: Start as a single `health_checks.py` file with `__all__` exporting both models and functions. Split only if the file exceeds ~400 lines.

2. **IOPS budget threshold for HLT-02 "VMs exceeding IOPS budget"**
   - What we know: Layout engine uses 100,000 IOPS per datastore as the default `iops_budget_per_ds`.
   - What's unclear: Should the health check use the same threshold from `PlacementConstraints.iops_budget_per_ds` (user-configurable in layout settings), or hardcode the 100K default?
   - Recommendation: Hardcode 100,000 in health_checks.py constants with a comment referencing the layout engine default. The concerns page does not need a constraint input panel.

3. **"High DRR override count" check from HLT-02**
   - What we know: The additional_context mentions "high DRR override count" as a sizing risk finding.
   - What's unclear: There is no `drr_override_flag` column in CANONICAL_COLUMNS. DRR values come from workload category classification — there is no distinction between "auto-classified DRR" and "manually overridden DRR" in the schema.
   - Recommendation: Interpret this as "high DRR value count" (VMs with drr >= 7, which suggests aggressive compression assumptions) OR skip this specific sub-check and satisfy HLT-02 with the other checks (Unknown ratio + large Unknown + IOPS budget). Flag for planner decision.

4. **Affected VM names in findings: privacy / log sanitization**
   - What we know: `logging_config.py` prohibits logging VM names. But findings display VM names in the UI.
   - What's unclear: Does the no-log rule apply to UI display? Almost certainly no — the user uploaded these VMs.
   - Recommendation: Display VM names in the UI findings cards (this is the expected behavior). Never log the `affected_vms` field via Python's `logging` module.

---

## Sources

### Primary (HIGH confidence)
- `/Users/fjacquet/Projects/store-predict/src/store_predict/pipeline/parsers/columns.py` — CANONICAL_COLUMNS verified, `hw_version` and `tools_status` confirmed absent
- `/Users/fjacquet/Projects/store-predict/src/store_predict/pipeline/parsers/rvtools.py` — Optional column pattern confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/pipeline/layout_engine.py` — Pure pipeline pattern, `generate_all_proposals` signature confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/pipeline/layout_models.py` — `@dataclass(frozen=True)` model pattern confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/ui/layout.py` — Navigation link pattern confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/ui/state.py` — `load_session_data()` signature and behavior confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/ui/pages/layout_page.py` — Page pattern, no-data state, route registration confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/main.py` — Page import pattern for route registration confirmed
- `/Users/fjacquet/Projects/store-predict/src/store_predict/i18n/locales/en.yaml` — i18n structure confirmed, `layout:` and `concerns:` keys absent
- `/Users/fjacquet/Projects/store-predict/.planning/research/STACK.md` — HW version mapping dict, column names, check thresholds from milestone research
- `/Users/fjacquet/Projects/store-predict/tests/test_layout_engine.py` — Test pattern without mock, `_make_vm()` helper confirmed
- `/Users/fjacquet/Projects/store-predict/tests/conftest.py` — Project fixture conventions confirmed

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — Architecture decisions, critical pitfalls, phase ordering rationale
- [Broadcom KB 315655 — Virtual machine hardware versions](https://knowledge.broadcom.com/external/article/315655) — HW version to ESXi mapping (referenced in STACK.md, not fetched directly this pass)
- [virten.net — Virtual Machine Hardware Versions](https://www.virten.net/vmware/virtual-machine-hardware-versions/) — vmx version table (referenced in STACK.md)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all patterns verified against live codebase
- Architecture: HIGH — pipeline module pattern established by layout_engine.py; page pattern established by layout_page.py
- Health check conditions: HIGH — all thresholds from verified milestone research (STACK.md) with sources
- Parser extension: HIGH — optional column pattern confirmed in rvtools.py; sentinel value approach matches existing code
- i18n keys: HIGH — key structure confirmed from existing en.yaml; all new keys identified
- Pitfalls: HIGH — sentinel zero, session round-trip, powered-off filter all verified against live code

**Research date:** 2026-02-22
**Valid until:** 2026-04-22 (stable domain — health check logic is pure DataFrame comparisons, no external API dependencies)
