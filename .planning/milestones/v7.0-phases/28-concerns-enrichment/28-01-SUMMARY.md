---
phase: 28-concerns-enrichment
plan: "01"
subsystem: health-checks
tags: [health-checks, remediation, ui, i18n, dataclass]
dependency_graph:
  requires: []
  provides: [HealthFinding.remediation, concerns-page-remediation-display, i18n-export-keys]
  affects: [src/store_predict/pipeline/health_checks.py, src/store_predict/ui/pages/concerns.py]
tech_stack:
  added: []
  patterns: [frozen-dataclass-default-field, string-concatenation-line-length]
key_files:
  created: []
  modified:
    - src/store_predict/pipeline/health_checks.py
    - src/store_predict/ui/pages/concerns.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - tests/test_health_checks.py
decisions:
  - "Remediation strings hardcoded in English per planning decision (pre-sales tool, English acceptable)"
  - "String concatenation used to satisfy ruff E501 120-char line limit"
  - "En-dash replaced with double-hyphen to satisfy ruff RUF001 (ambiguous character)"
  - "i18n export keys added to concerns section in both locales for Plan 02 readiness"
metrics:
  duration_seconds: 586
  completed_date: "2026-02-24"
  tasks_completed: 2
  files_modified: 5
---

# Phase 28 Plan 01: Remediation Hints for Health Findings Summary

**One-liner:** HealthFinding dataclass extended with remediation field; 14 actionable English hints populated across 13 check functions; /concerns page renders hints in italic muted style below detail text.

## What Was Built

### Task 1: Extend HealthFinding dataclass

- Added `remediation: str = ""` field to the `HealthFinding` frozen dataclass (after `cluster` field)
- Default empty string preserves backward compatibility for all existing construction sites
- Populated actionable English remediation hints in all 13 check functions (14 finding types):
  - `missing_os`: Export RVTools after ensuring VMware Tools is running
  - `zero_provisioned`: Re-export; zero provisioned indicates snapshot-only or powered-off VM
  - `missing_cpu`: Re-export after powering on VMs
  - `missing_ram`: Re-export after powering on VMs
  - `high_powered_off_ratio`: Confirm decommissioned status vs maintenance window
  - `high_unknown_ratio`: Review VM Review page or add pattern rules
  - `large_unknown_vms`: Classify large VMs before generating final report
  - `iops_budget_exceeded`: Dedicated datastore or NVMe-tier; discuss T-series
  - `no_cluster`: Confirm test/dev vs production clustered hosts
  - `very_old_hw_version`: Schedule immediate ESXi upgrade to 7.0 U3+
  - `old_hw_version`: Plan ESXi upgrade to 7.0 U3+
  - `small_cluster_ha`: Add ESXi host for N+1 HA
  - `tools_not_installed`: Install VMware Tools before migration
  - `tools_not_running`: Start VMware Tools service

### Task 2: UI display and i18n keys

- Updated `_render_finding_card` in concerns.py to render remediation hint when non-empty
- Display: `ui.label(finding.remediation).classes("text-sm text-gray-500 italic mt-1")`
- Added `export_pdf`, `export_csv`, `export_pdf_filename`, `export_csv_filename` keys to both en.yaml and fr.yaml under `concerns:` section (for Plan 02 readiness)
- Added 3 new tests: remediation for missing_os, tools_not_installed, and default empty constructor

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 9b670b5 | feat(28-01): extend HealthFinding with remediation field and populate all 13 check functions |
| 2 | f798c31 | feat(28-01): display remediation hint in /concerns card UI and add i18n export keys |

## Test Results

- 60 tests pass (57 original + 3 new remediation tests)
- ruff: no issues
- mypy: no issues in 2 source files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Lint] Fixed E501 line-length violations in remediation strings**
- **Found during:** Task 2 (ruff check)
- **Issue:** 14 remediation strings exceeded 120-char ruff E501 limit
- **Fix:** Wrapped strings using Python implicit string concatenation within parentheses
- **Files modified:** src/store_predict/pipeline/health_checks.py
- **Commit:** f798c31 (included in Task 2 commit after fix)

**2. [Rule 2 - Lint] Fixed RUF001 ambiguous en-dash in old_hw_version remediation**
- **Found during:** Task 2 (ruff check)
- **Issue:** `14–16` contained Unicode en-dash (U+2013); ruff flags as ambiguous character
- **Fix:** Replaced with ASCII double-hyphen `14-16`
- **Files modified:** src/store_predict/pipeline/health_checks.py
- **Commit:** f798c31

## Self-Check: PASSED

All key files confirmed present. Both commits verified in git log. All 60 tests pass. ruff and mypy clean.
