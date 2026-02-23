---
phase: 23-multi-cluster-compute
verified: 2026-02-23T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 23: Multi-Cluster Compute Verification Report

**Phase Goal:** Engineers can see host count recommendations broken down per cluster, with health findings scoped to cluster where applicable
**Verified:** 2026-02-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `compute_cluster_breakdown()` returns one `ClusterSizingRow` per distinct cluster name, sorted alphabetically | VERIFIED | Function exists at line 324 of `compute_sizing.py`; uses `groupby("cluster_norm", sort=True)`; 8 cluster tests pass |
| 2 | `ClusterSizingRow.hosts_needed` equals `max(_hosts_n1, _hosts_by_ram)` for that cluster's VMs | VERIFIED | Line 372 `hosts_needed = max(hv, hr)` confirmed; test `test_cluster_breakdown_hosts_formula` passes |
| 3 | VMs with empty or null cluster are grouped under sentinel `__no_cluster__`, not omitted | VERIFIED | Line 362: `cluster_col.replace("", "__no_cluster__")`; test `test_cluster_breakdown_no_cluster_vms` passes |
| 4 | `HealthFinding` accepts an optional `cluster` field (default empty string) without breaking existing tests | VERIFIED | Line 60: `cluster: str = ""`; 455 tests pass, only 2 pre-existing failures in `test_llm_classifier.py` (unrelated) |
| 5 | Per-cluster HW version checks emit one finding per affected cluster with cluster name in the finding | VERIFIED | `_check_hw_version_per_cluster()` at line 308; emits `cluster=str(cluster_name)`; 10 cluster health tests pass |
| 6 | `/compute` page displays per-cluster table with 2+ distinct clusters; suppressed for single-cluster | VERIFIED | `_render_cluster_breakdown_table()` at line 100 in `compute.py`; `if len(real_clusters) < 2: return` |
| 7 | Per-cluster table includes grand total row summing all cluster rows | VERIFIED | Lines 143-149 in `compute.py` append total row; CLUS-03 comment present |
| 8 | Health finding cards on `/concerns` display cluster name badge when `finding.cluster` is non-empty | VERIFIED | Lines 68-71 in `concerns.py`: `if finding.cluster: ui.label(finding.cluster)...` |
| 9 | All new user-visible strings exist in both `fr.yaml` and `en.yaml` | VERIFIED | All 10 `compute:` cluster keys and `health.small_cluster_ha` confirmed in both locale files |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/store_predict/pipeline/compute_sizing.py` | `ClusterSizingRow` dataclass and `compute_cluster_breakdown()` in `__all__` | VERIFIED | Both in `__all__` lines 22-28; dataclass at line 61; function at line 324 |
| `src/store_predict/pipeline/health_checks.py` | `cluster: str = ""` on `HealthFinding`; `_check_hw_version_per_cluster()`; `_check_small_cluster_ha()` | VERIFIED | Line 60: field present; functions at lines 308 and 369; both called in `run_health_checks()` lines 122-123 |
| `src/store_predict/ui/pages/compute.py` | `_render_cluster_breakdown_table()` wired into `_results_panel()` | VERIFIED | Function at line 100; called in `_results_panel()` lines 225-231; `compute_cluster_breakdown` imported line 22 |
| `src/store_predict/ui/pages/concerns.py` | Cluster badge rendered in `_render_finding_card()` when `finding.cluster` non-empty | VERIFIED | Lines 68-71 present; import of `HealthFinding` from health_checks on line 8 |
| `src/store_predict/i18n/locales/fr.yaml` | All cluster i18n keys | VERIFIED | Lines 365-374: all 10 compute cluster keys; lines 331-333: `small_cluster_ha` keys |
| `src/store_predict/i18n/locales/en.yaml` | All cluster i18n keys | VERIFIED | Lines 365-374: all 10 compute cluster keys; lines 331-333: `small_cluster_ha` keys |
| `tests/test_compute_sizing.py` | `TestClusterBreakdown` class with 8 tests | VERIFIED | 8 cluster tests pass (`pytest -k cluster` = 8 passed) |
| `tests/test_health_checks.py` | `TestPerClusterHealthChecks` class with 10 tests | VERIFIED | 10 cluster health tests pass (`pytest -k cluster` = 10 passed) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `compute_cluster_breakdown()` | `_hosts_n1()` and `_hosts_by_ram()` | direct calls with per-cluster aggregates | VERIFIED | Lines 370-372 call both functions; `hosts_needed = max(hv, hr)` |
| `_check_hw_version_per_cluster()` | `HealthFinding(cluster=cluster_name)` | groupby loop emitting one finding per cluster | VERIFIED | Lines 340-349 and 354-364: `cluster=str(cluster_name)` in both `HealthFinding()` calls |
| `src/store_predict/ui/pages/compute.py` | `compute_cluster_breakdown()` | import and call inside `_results_panel()` | VERIFIED | Import line 22; call at line 225 inside `_results_panel()` |
| `_render_cluster_breakdown_table()` | `ui.table(columns=..., rows=...)` | row dicts with grand total appended | VERIFIED | Line 151: `ui.table(columns=columns, rows=rows).classes("w-full")` |
| `src/store_predict/ui/pages/concerns.py` | `finding.cluster` | conditional rendering in `_render_finding_card()` | VERIFIED | Line 68: `if finding.cluster:` with badge label at line 69 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLUS-01 | 23-01 | Tool parses Cluster column from RVTools vInfo tab and groups VMs by cluster | SATISFIED | `compute_cluster_breakdown()` normalizes cluster column, groups by `cluster_norm`; `_check_hw_version_per_cluster()` and `_check_small_cluster_ha()` both group by cluster |
| CLUS-02 | 23-02 | `/compute` page shows per-cluster breakdown table (cluster name, VM count, vCPU/RAM totals, hosts needed per cluster) | SATISFIED | `_render_cluster_breakdown_table()` renders `ui.table` with all 5 required columns; wired into `_results_panel()` |
| CLUS-03 | 23-01 | Per-cluster breakdown table includes a grand total row summing all clusters | SATISFIED | Lines 143-149 in `compute.py` append grand total row labeled `t("compute.cluster_total")` |
| CLUS-04 | 23-01 | Health checks surface findings per cluster (HW version spread, HA host ratio per cluster) | SATISFIED | `_check_hw_version_per_cluster()` replaces global HW check; `_check_small_cluster_ha()` flags clusters with fewer than 3 VMs; both propagate `cluster=` field |

All 4 requirements declared in plans are mapped and satisfied. No orphaned requirements found — REQUIREMENTS.md traceability table confirms CLUS-01 through CLUS-04 all mapped to Phase 23 and marked Complete.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No anti-patterns found in phase-modified files |

Checked for: TODO/FIXME comments, `return null`/`return {}`, empty handlers, console.log placeholders. All clear.

### Human Verification Required

#### 1. Multi-cluster RVTools upload — visual table rendering

**Test:** Upload an RVTools `.xlsx` file whose vInfo tab has a non-empty Cluster column with 2+ distinct cluster names. Navigate to `/compute`.
**Expected:** Per-cluster breakdown table appears below the N+1 HA card. Table has one row per cluster plus a grand total row. Columns: Cluster, VMs, vCPUs, RAM (GiB), Hosts needed. Row order is alphabetical by cluster name. Note text appears beneath the table.
**Why human:** Visual layout, NiceGUI `ui.table` rendering, and alphabetical sort order cannot be verified without running the app.

#### 2. Single-cluster / LiveOptics suppression — informational note

**Test:** Upload a LiveOptics file (no Cluster column) or a single-cluster RVTools file. Navigate to `/compute`.
**Expected:** The per-cluster table is suppressed. A gray informational card appears instead with the `compute.no_cluster_data_note` message.
**Why human:** Conditional suppression logic depends on runtime cluster detection from the actual file.

#### 3. Concerns page cluster badge rendering

**Test:** Upload an RVTools file with multi-cluster data and at least one cluster with old HW version or fewer than 3 VMs. Navigate to `/concerns`.
**Expected:** Per-cluster health findings (e.g. HW version warnings, small cluster HA warnings) show a gray monospace badge with the cluster name in the card header. Global findings (missing OS, powered-off ratio, etc.) show no badge.
**Why human:** Conditional badge visibility and visual styling require running the app.

### Gaps Summary

No gaps found. All automated checks pass.

The 2 pre-existing test failures in `tests/test_llm_classifier.py::test_llm_config_max_concurrent_default` and `tests/test_llm_classifier.py::test_llm_config_timeout_default` are unrelated to Phase 23 and were documented as pre-existing in both SUMMARYs.

---

_Verified: 2026-02-23_
_Verifier: Claude (gsd-verifier)_
