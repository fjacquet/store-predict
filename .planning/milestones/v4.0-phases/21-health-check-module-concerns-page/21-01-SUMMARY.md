---
phase: 21-health-check-module-concerns-page
plan: "01"
subsystem: pipeline
tags: [health-checks, data-quality, best-practices, parsers]
dependency_graph:
  requires: []
  provides:
    - health_checks_engine
    - hw_version_column
    - tools_status_column
  affects:
    - concerns_page_plan_21_02
tech_stack:
  added: []
  patterns:
    - frozen_dataclass_for_value_objects
    - strEnum_for_severity
    - sentinel_value_pattern_for_missing_data
    - active_vm_filtering_before_checks
key_files:
  created:
    - src/store_predict/pipeline/health_checks.py
    - tests/test_health_checks.py
  modified:
    - src/store_predict/pipeline/parsers/columns.py
    - src/store_predict/pipeline/parsers/rvtools.py
    - src/store_predict/pipeline/parsers/liveoptics.py
decisions:
  - "hw_version sentinel 0 means data not available — guards all HW version checks to prevent false positives on LiveOptics exports"
  - "tools_status empty string sentinel guards tools checks similarly"
  - "very_old_hw_version finding suppresses old_hw_version to avoid duplicate findings on the same VMs"
  - "Thresholds as module-level constants: 30% powered-off (Info), 25% unknown ratio (Warning), 1 TiB large VM, 100K IOPS budget, vHW 14 critical, vHW 17 recommended minimum"
  - "active filter (is_powered_on==True and is_template==False) applied once in run_health_checks before all best-practice/quality checks"
metrics:
  duration: "~20 minutes"
  completed: "2026-02-22"
  tasks_completed: 3
  files_modified: 5
  tests_added: 49
---

# Phase 21 Plan 01: Health Check Engine — Column Extensions and Pipeline Module Summary

**One-liner:** Pure health check pipeline with hw_version/tools_status columns added to canonical schema, 11 check functions, and 49 tests covering all check IDs and sentinel guards.

## What Was Implemented

### Task 1: CANONICAL_COLUMNS and Parser Extensions

Extended `src/store_predict/pipeline/parsers/columns.py`:
- Added `"hw_version"` (int, 0 = not available) and `"tools_status"` (str, "" = not available) to `CANONICAL_COLUMNS` before `"row_index"`
- Added `RVTOOLS_ALIASES` entries: `hw_version` maps to `["HW version", "Hardware version", "HW Version"]`; `tools_status` maps to `["Tools Status", "VMware Tools Status"]`

Extended `src/store_predict/pipeline/parsers/rvtools.py`:
- `parse_rvtools()` now extracts `hw_version` using `pd.to_numeric(..., errors="coerce").fillna(0).astype(int)` with fallback 0 if column absent
- `parse_rvtools()` now extracts `tools_status` as string with fallback `""` if column absent

Extended `src/store_predict/pipeline/parsers/liveoptics.py`:
- `_build_liveoptics_df()` sets `result["hw_version"] = 0` and `result["tools_status"] = ""` as sentinels (LiveOptics exports never have these columns)

### Task 2: health_checks.py — Full Engine

Created `src/store_predict/pipeline/health_checks.py` (~300 lines):

**Domain models:**
- `Severity(StrEnum)` — CRITICAL, WARNING, INFO
- `HealthFinding(frozen dataclass)` — check_id, severity, title (i18n key), detail (i18n key), affected_count, affected_vms (tuple, max 5)
- `HealthCheckResult(frozen dataclass)` — findings tuple, total_vms_checked, has_data, plus critical_count/warning_count/info_count properties

**Entry point:** `run_health_checks(df: pd.DataFrame | None) -> HealthCheckResult`
- Returns `has_data=False` immediately for `None` or empty DataFrame
- Filters to `is_powered_on==True and is_template==False` before all checks

**11 check functions across 3 categories:**

| check_id | Severity | Trigger |
|---|---|---|
| `data_quality.missing_os` | WARNING | os_name empty or whitespace-only |
| `data_quality.zero_provisioned` | WARNING | provisioned_mib == 0 |
| `data_quality.missing_cpu` | INFO | num_cpus == 0 |
| `data_quality.missing_ram` | INFO | memory_mib == 0 |
| `data_quality.high_powered_off_ratio` | INFO | >30% VMs powered off |
| `sizing_risk.high_unknown_ratio` | WARNING | >25% active VMs are Unknown workload |
| `sizing_risk.large_unknown_vms` | WARNING | Unknown VM with provisioned >= 1 TiB |
| `sizing_risk.iops_budget_exceeded` | WARNING | peak_iops > 100,000 (and > 0) |
| `best_practice.no_cluster` | WARNING | cluster is empty |
| `best_practice.very_old_hw_version` | CRITICAL | hw_version > 0 AND < 14 |
| `best_practice.old_hw_version` | WARNING | hw_version >= 14 AND < 17 (only if very_old not fired) |
| `best_practice.tools_not_installed` | CRITICAL | tools_status == "toolsNotInstalled" |
| `best_practice.tools_not_running` | WARNING | tools_status == "toolsNotRunning" |

### Task 3: tests/test_health_checks.py — 49 Tests

Created `tests/test_health_checks.py`:
- `_make_active_df(**overrides)` helper builds minimal canonical DataFrame with healthy defaults
- `_get_ids(result)` helper extracts set of check_ids for clean assertions
- 5 test classes: TestEdgeCases, TestDataQualityChecks, TestSizingRiskChecks, TestBestPracticeChecks, TestAffectedVms
- 49 tests, all passing; zero `unittest.mock` usage

**Key sentinel guard tests:**
- `test_hw_version_zero_sentinel_skipped` — single VM with hw_version=0 produces no HW findings
- `test_hw_version_zero_all_vms_sentinel_skipped` — 5 VMs all hw_version=0 produces no HW findings
- `test_empty_tools_status_skipped` — tools_status="" produces no tools findings
- `test_powered_off_vms_not_flagged_for_hw` — powered-off VM with hw_version=11 not flagged
- `test_template_vms_not_flagged_for_hw` — template VM with hw_version=11 not flagged

## Key Decisions Made

1. **hw_version sentinel 0**: Selected 0 (not -1 or None) because `pd.to_numeric` returns 0 on coerce+fillna naturally. Guards all `_check_hw_version` logic with `(hw > 0)` mask.

2. **Duplicate finding suppression**: When `very_old_hw_version` fires (< vHW 14), `old_hw_version` (vHW 14-16) is NOT also fired. This prevents the UI from showing two overlapping findings for the same VMs.

3. **active filter is centralized**: Applied once in `run_health_checks()` before all checks. Individual check functions receive already-filtered `active` DataFrame. The powered-off ratio check alone receives both `full_df` and `active` as arguments.

4. **i18n keys for title/detail**: `title` and `detail` fields store i18n keys (e.g., `"health.missing_os.title"`) not translated strings. The UI layer (plan 21-02) will call `t()` for display.

5. **affected_vms capped at 5**: Uses `.head(5).tolist()` — the full count is in `affected_count` for display, while `affected_vms` is a sample for UI tooltips. Never logged.

## Patterns Established

- **Check function signature**: `_check_X(df: pd.DataFrame) -> list[HealthFinding]` — returns empty list if no issue, list with one finding otherwise. Exception: `_check_high_powered_off_ratio(full_df, active)` takes two DFs.
- **Frozen dataclass value objects**: Both `HealthFinding` and `HealthCheckResult` are frozen — immutable, hashable, safe to pass across layers.
- **Sentinel pattern**: 0 for int columns (hw_version), "" for str columns (tools_status) — consistent with existing parsers that use 0/False/"" as absence sentinels.

## Deviations from Plan

None — plan executed exactly as written.

## Test Count and Coverage

- 49 tests added in `tests/test_health_checks.py`
- `health_checks.py` coverage: 98% (3 lines uncovered: empty DataFrame path and one sentinel branch)
- Existing test suite: 386 passed, 1 skipped (pre-existing `test_llm_config_max_concurrent_default` failure in test_llm_classifier.py, unrelated to this plan)

## Commits

| Hash | Message |
|---|---|
| `be872fc` | feat(21-01): extend CANONICAL_COLUMNS with hw_version and tools_status |
| `bb705d9` | feat(21-01): create health_checks.py with all 11 check functions |
| `de4b3cb` | test(21-01): add comprehensive test suite for health_checks.py |

## Self-Check: PASSED

Files created/modified verified:
- `src/store_predict/pipeline/health_checks.py` — exists, imports OK
- `tests/test_health_checks.py` — exists, 49 tests pass
- `src/store_predict/pipeline/parsers/columns.py` — hw_version and tools_status in CANONICAL_COLUMNS
- `src/store_predict/pipeline/parsers/rvtools.py` — hw_version/tools_status extraction added
- `src/store_predict/pipeline/parsers/liveoptics.py` — sentinel values added

Commits verified: be872fc, bb705d9, de4b3cb all present in git log.
