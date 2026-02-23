---
phase: 23-multi-cluster-compute
plan: "02"
subsystem: ui
tags: [compute, concerns, cluster, ui, nicegui]
dependency_graph:
  requires: [23-01]
  provides: [per-cluster-breakdown-table, cluster-badge-on-findings]
  affects: [compute.py, concerns.py]
tech_stack:
  added: []
  patterns: [nicegui-ui-table, conditional-badge-rendering, sentinel-pattern]
key_files:
  created: []
  modified:
    - src/store_predict/ui/pages/compute.py
    - src/store_predict/ui/pages/concerns.py
decisions:
  - "__no_cluster__ sentinel translated to i18n label in display rows; sentinel check determines whether multi-cluster table is shown"
  - "cluster badge in concerns.py uses raw cluster name (not i18n key) — cluster names are vCenter environment data"
  - "ui.table used for per-cluster breakdown (not AG Grid — AG Grid Community cannot do row grouping)"
metrics:
  duration: "1 min"
  completed: "2026-02-23"
  tasks_completed: 2
  files_modified: 2
---

# Phase 23 Plan 02: Wire Per-Cluster UI — Compute Breakdown Table and Concerns Badge Summary

**One-liner:** Per-cluster ESXi host breakdown table wired into /compute and cluster name badge added to /concerns finding cards.

## What Was Built

### Task 1: Per-cluster breakdown table in compute.py

Added `_render_cluster_breakdown_table()` to `src/store_predict/ui/pages/compute.py`:

- Filters real clusters (excludes `__no_cluster__` sentinel) to decide whether to show table or informational note
- For 2+ real clusters: renders `ui.table` with columns (Cluster, VMs, vCPUs, RAM GiB, Hosts needed) plus grand total row
- For 0–1 real clusters (single-cluster or LiveOptics): shows a gray informational card with `compute.no_cluster_data_note`
- Called inside `_results_panel()` after the Active/Passive section, recomputing on every refresh (no session caching)
- Imports `ClusterSizingRow` and `compute_cluster_breakdown` from `store_predict.pipeline.compute_sizing`

### Task 2: Cluster badge in concerns.py

Modified `_render_finding_card()` in `src/store_predict/ui/pages/concerns.py`:

- Added `flex-wrap` to header row to accommodate the badge
- When `finding.cluster` is non-empty, renders a gray monospace badge with the cluster name after the title
- Global findings (cluster == "") render exactly as before — no visual change

## Verification Results

- Import checks: both `compute_page` and `concerns_page` import cleanly
- Tests: 455 passed, 1 skipped, 2 pre-existing failures in `test_llm_classifier.py` (unrelated to this plan)
- Ruff: no issues in modified files
- Mypy: no issues in 49 source files

## Deviations from Plan

None — plan executed exactly as written. All i18n keys were already present from Plan 01 or earlier.

## Self-Check: PASSED

- [x] `src/store_predict/ui/pages/compute.py` — exists and imports cleanly
- [x] `src/store_predict/ui/pages/concerns.py` — exists and imports cleanly
- [x] commit b9688dd — feat(23-02): add per-cluster breakdown table to compute.py
- [x] commit 1f15786 — feat(23-02): add cluster badge to finding cards in concerns.py
