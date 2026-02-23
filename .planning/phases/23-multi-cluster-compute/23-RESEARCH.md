# Phase 23: Multi-Cluster Compute - Research

**Researched:** 2026-02-23
**Domain:** Per-cluster compute sizing, health check clustering, NiceGUI ui.table
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLUS-01 | Tool parses Cluster column from RVTools vInfo tab and groups VMs by cluster | Cluster column is already in the canonical DataFrame — no new parsing needed; `df.groupby("cluster")` is the entry point |
| CLUS-02 | `/compute` page shows per-cluster breakdown table (cluster name, VM count, vCPU/RAM totals, hosts needed per cluster) | A new `compute_cluster_breakdown()` function in `pipeline/compute_sizing.py` returns a list of per-cluster results; rendered with `ui.table` in `compute.py` |
| CLUS-03 | Per-cluster breakdown table includes a grand total row summing all clusters | Grand total row appended to the list of row dicts before passing to `ui.table` |
| CLUS-04 | Health checks surface findings per cluster where applicable (e.g., HW version spread, HA host ratio per cluster) | `HealthFinding` gains an optional `cluster` field; two checks (`_check_hw_version`, `_check_no_cluster`) are adapted to produce per-cluster findings |
</phase_requirements>

---

## Summary

Phase 23 builds on the complete compute sizing infrastructure from Phase 22. The canonical DataFrame produced by every parser already contains a `cluster` column — no ingestion changes are required. The work is entirely in the pipeline module and the UI layer.

The central pattern is `df.groupby("cluster")` applied to the active-VM-filtered DataFrame. For each cluster group, the existing `_hosts_n1` and `_hosts_by_ram` helper functions can be called directly with per-cluster aggregates. The result is a list of per-cluster records suitable for a `ui.table` with a grand total row appended.

Health checks require a targeted extension: two checks (`hw_version` and `no_cluster`) are meaningful per-cluster. Adding an optional `cluster: str` field to `HealthFinding` (defaulting to `""` for global findings) is the minimal and backward-compatible change. The concerns page already iterates findings — it will surface the cluster name when present.

**Primary recommendation:** Extend `compute_sizing.py` with a new `compute_cluster_breakdown()` function returning `list[ClusterSizingRow]`; add a `cluster` field to `HealthFinding`; add a `_check_hw_version_per_cluster()` variant; render with `ui.table` following the existing report-page pattern.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | project-pinned | `groupby`, `agg`, DataFrame slicing | Already used everywhere in pipeline |
| NiceGUI | project-pinned | `ui.table` for cluster breakdown display | Established project UI framework |
| Python dataclasses | stdlib | `ClusterSizingRow` value object | Matches existing `HostConfig` / `ComputeSizingResult` pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `typing.TypedDict` | stdlib | Session config extension (if needed) | Only if new session keys are required |
| Python `dataclasses.dataclass(frozen=True)` | stdlib | Immutable result objects | Always — matches project frozen-dataclass convention |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `compute_cluster_breakdown()` function | Modify `compute_sizing()` to return per-cluster data | Modifying `compute_sizing()` breaks the current clean flat API; a separate function is additive and easier to test |
| `ui.aggrid` with row grouping | `ui.table` with explicit rows | AG Grid Community cannot do row grouping (confirmed in STATE.md); `ui.table` is correct choice |
| Per-cluster `ComputeSizingResult` objects | Simple `ClusterSizingRow` dataclass | Full `ComputeSizingResult` per cluster is overweight — no vMSC/AP data needed per cluster; a leaner `ClusterSizingRow` is more appropriate |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

No new files required. Extend existing modules:

```
src/store_predict/pipeline/
└── compute_sizing.py       # Add ClusterSizingRow dataclass + compute_cluster_breakdown()
    health_checks.py        # Add cluster field to HealthFinding, add per-cluster hw_version check

src/store_predict/ui/pages/
└── compute.py              # Add _render_cluster_breakdown_table() + wire into _results_panel()

src/store_predict/i18n/locales/
└── fr.yaml                 # New keys: compute.cluster_breakdown_heading, compute.cluster_col, etc.
    en.yaml                 # Same keys in English
```

### Pattern 1: Per-Cluster Aggregation with groupby

**What:** Group active VMs by cluster, aggregate vCPU and RAM, compute host counts per group.
**When to use:** Any time per-cluster metrics are needed from the session DataFrame.

```python
# Source: existing compute_sizing.py helpers + pandas groupby
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class ClusterSizingRow:
    """Per-cluster sizing result for the breakdown table."""
    cluster_name: str
    vm_count: int
    total_vcpus: int
    total_ram_gib: float
    hosts_needed: int  # N+1 HA, same formula as global

def compute_cluster_breakdown(
    df: pd.DataFrame | None,
    host_config: HostConfig,
    overcommit_ratio: float = 4.0,
) -> list[ClusterSizingRow]:
    """Return per-cluster sizing rows for the compute breakdown table.

    Returns empty list if df is None/empty or has no cluster data.
    VMs with empty/null cluster are grouped as '(No Cluster)'.
    Uses same active-VM filter as compute_sizing().
    """
    if df is None or df.empty:
        return []
    ratio = _clamp_ratio(overcommit_ratio)
    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]
    if active.empty:
        return []

    # Normalize empty cluster labels
    df_work = active.copy()
    df_work["cluster"] = df_work["cluster"].fillna("").astype(str).str.strip()
    df_work["cluster"] = df_work["cluster"].replace("", "(No Cluster)")

    rows: list[ClusterSizingRow] = []
    for cluster_name, group in df_work.groupby("cluster", sort=True):
        total_vcpus = int(pd.to_numeric(group["num_cpus"], errors="coerce").fillna(0).sum())
        total_ram_mib = float(pd.to_numeric(group["memory_mib"], errors="coerce").fillna(0).sum())
        total_ram_gib = total_ram_mib / 1024.0
        hv = _hosts_n1(total_vcpus, host_config.total_cores, ratio)
        hr = _hosts_by_ram(total_ram_gib, host_config.ram_gib)
        hosts = max(hv, hr)
        rows.append(ClusterSizingRow(
            cluster_name=str(cluster_name),
            vm_count=len(group),
            total_vcpus=total_vcpus,
            total_ram_gib=total_ram_gib,
            hosts_needed=hosts,
        ))
    return rows
```

### Pattern 2: Grand Total Row for ui.table

**What:** Append a summary row dict that sums all cluster rows.
**When to use:** Any ui.table that requires a totals footer row.

```python
# Source: existing report.py ui.table pattern
def _cluster_rows_with_total(
    cluster_rows: list[ClusterSizingRow],
    t_fn,  # t() callable
) -> list[dict]:
    """Convert ClusterSizingRow list + grand total into ui.table row dicts."""
    rows = [
        {
            "cluster": r.cluster_name,
            "vm_count": str(r.vm_count),
            "vcpus": str(r.total_vcpus),
            "ram_gib": f"{r.total_ram_gib:.1f}",
            "hosts": str(r.hosts_needed),
        }
        for r in cluster_rows
    ]
    # Grand total row
    rows.append({
        "cluster": t_fn("compute.cluster_total"),
        "vm_count": str(sum(r.vm_count for r in cluster_rows)),
        "vcpus": str(sum(r.total_vcpus for r in cluster_rows)),
        "ram_gib": f"{sum(r.total_ram_gib for r in cluster_rows):.1f}",
        "hosts": str(sum(r.hosts_needed for r in cluster_rows)),
    })
    return rows
```

### Pattern 3: Per-Cluster Health Finding

**What:** Add an optional `cluster` field to `HealthFinding`; per-cluster checks populate it.
**When to use:** Any health check that is meaningful at cluster granularity.

```python
# Source: existing health_checks.py HealthFinding dataclass
@dataclass(frozen=True)
class HealthFinding:
    check_id: str
    severity: Severity
    title: str
    detail: str
    affected_count: int
    affected_vms: tuple[str, ...]
    cluster: str = ""  # NEW: empty string = global finding, non-empty = cluster-scoped
```

The concerns page renders `finding.cluster` as a badge if non-empty:
```python
# In _render_finding_card():
if finding.cluster:
    ui.label(finding.cluster).classes("text-xs font-mono bg-gray-100 px-2 py-0.5 rounded")
```

### Pattern 4: Per-Cluster HW Version Check

**What:** Group active VMs by cluster, emit one `HealthFinding` per cluster that has old HW versions.
**When to use:** Replacing the global `_check_hw_version` with per-cluster variant.

```python
def _check_hw_version_per_cluster(df: pd.DataFrame) -> list[HealthFinding]:
    """Emit per-cluster hardware version findings.

    For each cluster: if any VMs have hw_version < _OLD_HW_VERSION (and > 0),
    emit a finding scoped to that cluster.
    Uses same sentinel guard: hw_version == 0 means data not available.
    """
    hw = pd.to_numeric(df.get("hw_version", pd.Series([0]*len(df))), errors="coerce").fillna(0).astype(int)
    if (hw > 0).sum() == 0:
        return []

    findings: list[HealthFinding] = []
    cluster_col = df["cluster"].fillna("").astype(str).str.strip().replace("", "(No Cluster)")

    for cluster_name, group in df.groupby(cluster_col, sort=True):
        group_hw = pd.to_numeric(group.get("hw_version", pd.Series([0]*len(group))), errors="coerce").fillna(0).astype(int)
        # ... same critical/warning logic as existing _check_hw_version but
        # with cluster=str(cluster_name) in the HealthFinding constructor
    return findings
```

### Pattern 5: HA Ratio Per Cluster (New Check for CLUS-04)

**What:** For each cluster, count total VMs and flag if cluster is too small for N+1 HA (< 3 hosts recommended minimum).
**When to use:** When `cluster` data is available in the DataFrame.

The check is meaningful per cluster: a cluster with 2 hosts and heavy load cannot survive N+1 HA. The check emits a `best_practice.small_cluster_ha` finding with `cluster=cluster_name`.

### Anti-Patterns to Avoid

- **Storing ClusterSizingRow list in `app.storage.tab`:** The list is cheap to recompute on every refresh — follow the same "never cache compute results" rule as `ComputeSizingResult`.
- **Using AG Grid for cluster breakdown:** Enterprise-only row grouping is unavailable. Use `ui.table` with explicit rows.
- **Modifying `ComputeSizingResult` to hold cluster data:** The global result and per-cluster breakdown are separate concerns. Keep them separate.
- **Calling `ingest_file()` or `classify_dataframe()` from compute page:** Always use `load_session_data()`.
- **Logging VM names or cluster names:** Security/privacy rule from CLAUDE.md — never log DataFrame content.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-cluster aggregation | Custom loop with dict accumulator | `df.groupby("cluster").agg(...)` | pandas groupby handles dtype coercion, empty groups, and sorting |
| Grand total row | Custom summation logic | Simple list comprehension `sum(r.field for r in rows)` | Already proven pattern in report page |
| Table display | Custom HTML table | `ui.table(columns=..., rows=...)` | Established pattern throughout the project; consistent styling |
| Host count per cluster | Re-implementing N+1 formula | `_hosts_n1()` and `_hosts_by_ram()` private helpers | Already tested, correct; just call them with per-cluster aggregates |

**Key insight:** All building blocks exist. This phase is assembly and extension, not new invention.

---

## Common Pitfalls

### Pitfall 1: Empty/Null Cluster Values
**What goes wrong:** Some RVTools exports have VMs not in any cluster (standalone hosts). The `cluster` column contains empty string `""` for these. `groupby("")` creates an unnamed group that produces a confusing empty-string row in the table.
**Why it happens:** RVTools parser fills `cluster` with `""` when the "Cluster" column is absent or empty (confirmed in `rvtools.py` line 73-76).
**How to avoid:** Normalize before groupby: `df["cluster"].replace("", "(No Cluster)")`. Use a sentinel string that renders meaningfully in French as well (needs i18n key).
**Warning signs:** Table row with empty cluster name column.

### Pitfall 2: Single-Cluster Files Show Redundant Table
**What goes wrong:** If all VMs are in one cluster, the per-cluster breakdown table shows a single row that duplicates the global totals shown above — confusing UX.
**Why it happens:** The breakdown is always rendered regardless of cluster count.
**How to avoid:** Only render the cluster breakdown table if `len(cluster_rows) > 1` (i.e., more than one distinct cluster). If only one cluster, the global totals are sufficient.
**Warning signs:** Identical numbers in breakdown table and global aggregate cards.

### Pitfall 3: HealthFinding Frozen Dataclass with New Field
**What goes wrong:** Adding `cluster: str = ""` to a `frozen=True` dataclass breaks existing test fixtures that construct `HealthFinding` without the field — only if they use positional arguments.
**Why it happens:** Positional arg count mismatch.
**How to avoid:** `cluster` must have a default value (`= ""`). All existing code creates `HealthFinding(...)` with keyword arguments (confirmed by reading health_checks.py), so this is safe.
**Warning signs:** `TypeError: __init__() takes X positional arguments but Y were given` in tests.

### Pitfall 4: hosts_needed Summation in Grand Total
**What goes wrong:** Summing `hosts_needed` across clusters (e.g., cluster A needs 3, cluster B needs 2 = "5 total") does NOT equal the global `hosts_n1` from `compute_sizing()` (which may be 4). The per-cluster sizing is conservative because each cluster gets its own N+1 buffer.
**Why it happens:** N+1 is computed independently per cluster, so the total is always >= global.
**How to avoid:** This is CORRECT BEHAVIOR — per-cluster sizing is intentionally more conservative (each cluster needs its own HA host). Document this in the UI with a tooltip: "Par-cluster total may exceed global due to independent N+1 buffers per cluster."
**Warning signs:** Engineer asks "why does sum of per-cluster hosts differ from global count?"

### Pitfall 5: LiveOptics Files Have No Cluster Data
**What goes wrong:** LiveOptics exports don't reliably include cluster metadata (noted in REQUIREMENTS.md Out of Scope). The `cluster` column will be all empty strings for LiveOptics files. The breakdown table will show a single "(No Cluster)" row.
**Why it happens:** LiveOptics parser sets `cluster = ""` when the column is absent (see `liveoptics.py`).
**How to avoid:** When all VMs are in "(No Cluster)", suppress the breakdown table entirely and show an informational note. Check `source_format` column OR check if all cluster values are empty.
**Warning signs:** User uploads LiveOptics file and sees uninformative "(No Cluster)" breakdown.

---

## Code Examples

Verified patterns from existing codebase:

### ui.table Columns Definition (from report.py)
```python
# Source: src/store_predict/ui/pages/report.py lines 113-129
columns = [
    {"name": "category", "label": t("report.col_category"), "field": "category", "align": "left"},
    {"name": "vms", "label": t("report.col_vms"), "field": "vms", "align": "right"},
    {"name": "provisioned", "label": t("report.col_provisioned"), "field": "provisioned", "align": "right"},
]
rows = [{"category": ..., "vms": ..., "provisioned": ...} for ...]
ui.table(columns=columns, rows=rows).classes("w-full")
```

### @ui.refreshable Pattern (from compute.py)
```python
# Source: src/store_predict/ui/pages/compute.py lines 98-107
@ui.refreshable
def _results_panel(df, cfg: _ComputeConfig) -> None:
    host_config = _resolve_host_config(cfg)
    result = compute_sizing(df, host_config, ...)
    # ... render results
    # EXTEND HERE: add cluster breakdown table below existing content
```

### Frozen Dataclass with Optional Field
```python
# Source: existing HealthFinding pattern in health_checks.py
@dataclass(frozen=True)
class HealthFinding:
    check_id: str
    severity: Severity
    title: str
    detail: str
    affected_count: int
    affected_vms: tuple[str, ...]
    cluster: str = ""  # fields with defaults must come last
```

### pandas groupby Aggregation Pattern
```python
# Source: pandas docs (HIGH confidence — standard pandas API)
active_df["cluster_norm"] = active_df["cluster"].fillna("").str.strip().replace("", "(No Cluster)")
for cluster_name, group in active_df.groupby("cluster_norm", sort=True):
    vcpus = int(pd.to_numeric(group["num_cpus"], errors="coerce").fillna(0).sum())
    ram_gib = float(pd.to_numeric(group["memory_mib"], errors="coerce").fillna(0).sum()) / 1024.0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat global compute sizing | Per-cluster breakdown added | Phase 23 | Engineers see cluster-level detail without losing global view |
| Global health findings only | Per-cluster findings for HW version | Phase 23 | Findings are actionable — engineer knows WHICH cluster to fix |

**Deprecated/outdated:**
- Global `_check_hw_version()` function: Will be replaced by `_check_hw_version_per_cluster()`. The old global version produces one finding for the entire environment; the per-cluster version produces one finding per affected cluster, enabling targeted remediation.

---

## Open Questions

1. **Should the per-cluster breakdown table also appear in the PDF/Excel reports?**
   - What we know: Phase 24 adds PDF/Excel health findings export. Phase 23 scope is UI only per REQUIREMENTS.md.
   - What's unclear: Whether PDF consumers (pre-sales engineers printing reports) want per-cluster compute breakdown.
   - Recommendation: Out of scope for Phase 23. The planner should NOT add PDF/Excel tasks here. Phase 24 is the export phase.

2. **Should the "(No Cluster)" label be an i18n key?**
   - What we know: All user-visible strings must go through `t()`. "(No Cluster)" will appear in the UI.
   - What's unclear: Whether "(No Cluster)" is a display label or a sentinel groupby key.
   - Recommendation: Use a sentinel string for groupby logic (e.g., `"__no_cluster__"`), but render via `t("compute.no_cluster_label")` when building table rows. This keeps the i18n contract clean.

3. **How many clusters should trigger the breakdown table?**
   - What we know: Single-cluster environments should suppress the table (Pitfall 2).
   - What's unclear: Whether to show the table for exactly 2 clusters, or always >= 2.
   - Recommendation: Show breakdown table when `len(distinct_non_empty_clusters) >= 2`. Suppress entirely for single-cluster or all-empty-cluster data. Show a note for LiveOptics files (all empty).

---

## Sources

### Primary (HIGH confidence)
- `/src/store_predict/pipeline/compute_sizing.py` — full module read; `_hosts_n1`, `_hosts_by_ram`, `_clamp_ratio` helpers verified
- `/src/store_predict/pipeline/health_checks.py` — full module read; `HealthFinding` dataclass and all check functions verified
- `/src/store_predict/pipeline/parsers/rvtools.py` — cluster column parsing verified (lines 73-76)
- `/src/store_predict/pipeline/parsers/columns.py` — `CANONICAL_COLUMNS` includes `cluster`; `RVTOOLS_ALIASES["cluster"] = ["Cluster"]` confirmed
- `/src/store_predict/ui/pages/compute.py` — full page read; `_results_panel` `@ui.refreshable` pattern confirmed
- `/src/store_predict/ui/pages/concerns.py` — full page read; `_render_finding_card` pattern confirmed
- `.planning/STATE.md` — AG Grid Community constraint confirmed; per-cluster breakdown must use `ui.table`

### Secondary (MEDIUM confidence)
- `/tests/test_compute_sizing.py` — test patterns confirmed; `_make_active_df()` builder used
- `/tests/test_health_checks.py` — `_make_active_df()` includes `cluster` field in defaults (line 33)
- `.planning/REQUIREMENTS.md` — LiveOptics cluster limitation confirmed as Out of Scope

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use; no new dependencies
- Architecture: HIGH — patterns directly observed from working source code
- Pitfalls: HIGH for pitfalls 1-3 (confirmed from source); MEDIUM for pitfalls 4-5 (derived from spec + code reading)

**Research date:** 2026-02-23
**Valid until:** 2026-03-25 (stable project; 30-day validity)
