---
phase: 28-concerns-enrichment
plan: "02"
subsystem: services/ui
tags: [export, pdf, csv, concerns, health-checks, reportlab]
dependency_graph:
  requires:
    - 28-01 (HealthFinding.remediation field)
  provides:
    - generate_concerns_pdf() in concerns_export service
    - generate_concerns_csv() in concerns_export service
    - Export PDF + Export CSV buttons on /concerns page
  affects:
    - src/store_predict/services/concerns_export.py (new)
    - src/store_predict/ui/pages/concerns.py (export buttons wired)
    - tests/test_concerns_export.py (new, 10 tests)
tech_stack:
  added:
    - concerns_export.py service module (ReportLab Platypus + stdlib csv)
  patterns:
    - Standalone service module with zero UI imports (same pattern as health_checks.py)
    - UTF-8 BOM CSV for Excel compatibility
    - ReportLab Vera/VeraBd font registration (same pattern as pdf_report.py)
key_files:
  created:
    - src/store_predict/services/concerns_export.py
    - tests/test_concerns_export.py
  modified:
    - src/store_predict/ui/pages/concerns.py
decisions:
  - "generate_concerns_pdf uses English strings for the standalone report (engineering doc); locale param reserved for future use"
  - "Export buttons placed between summary badges and separator — always visible when data is loaded"
  - "Test for CSV row count uses >= 2 assertion since health engine may produce bonus findings (small_cluster_ha)"
metrics:
  duration: "~3 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 28 Plan 02: Concerns Export (PDF + CSV) Summary

**One-liner:** Standalone concerns export module with ReportLab PDF and UTF-8 BOM CSV generators, wired to /concerns page via Export PDF and Export CSV buttons.

## What Was Built

### Task 1: `src/store_predict/services/concerns_export.py` (new)

Pure service module with zero UI imports.

**`generate_concerns_csv(health_result)`:**
- Writes header: `severity,check_id,title,detail,remediation,affected_count,cluster`
- One row per finding using `csv.writer` + `io.StringIO`
- Returns `bytes` encoded as UTF-8 with BOM (`utf-8-sig`) for Excel compatibility
- Empty findings tuple produces header-only CSV without error

**`generate_concerns_pdf(health_result, project_name, locale)`:**
- `io.BytesIO` + `reportlab.platypus.SimpleDocTemplate` on A4 page
- Vera/VeraBd fonts registered (same pattern as `pdf_report.py`)
- Flowables: title header + optional project name + generation date, severity summary bar (colored paragraphs), severity legend, one `Table` per finding with severity-colored left border
- Returns `bytes` starting with `%PDF`
- Empty findings tuple generates a valid "no concerns" PDF without error

### Task 2: `/concerns` page wiring + tests

**`src/store_predict/ui/pages/concerns.py` (modified):**
- Added import: `from store_predict.services.concerns_export import generate_concerns_csv, generate_concerns_pdf`
- Added `_get_locale()` helper reading `app.storage.tab.get("locale", "fr")`
- Added export button row (between summary badges and separator): blue PDF button + green CSV button, each triggering `ui.download()`

**`tests/test_concerns_export.py` (new, 10 tests):**
- CSV: header row, row-per-finding count, empty findings, UTF-8 BOM, severity value format
- PDF: returns bytes with `%PDF` magic, empty findings, project name, locale param, multiple findings

## Verification Results

```
tests/test_concerns_export.py    10 passed
tests/test_health_checks.py      60 passed (no regressions)
mypy src/store_predict/services/concerns_export.py  -- Success: no issues found
mypy src/store_predict/ui/pages/concerns.py         -- Success: no issues found
ruff check src/store_predict/services/ src/store_predict/ui/pages/concerns.py -- All checks passed
```

## Commits

| Hash    | Message |
|---------|---------|
| 4fbc634 | feat(28-02): create concerns_export.py with PDF and CSV generators |
| 2eff9dd | feat(28-02): wire Export PDF and Export CSV buttons onto /concerns page and add export tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion adjusted for actual health engine output**
- **Found during:** Task 2 (test run)
- **Issue:** `_make_result_two_findings()` (missing OS + zero provisioned) also triggers `small_cluster_ha` for a single-VM cluster, producing 3 findings instead of 2
- **Fix:** Changed `assert len(lines) == 3` to `assert len(lines) == finding_count + 1` (dynamically computed)
- **Files modified:** `tests/test_concerns_export.py`
- **Commit:** 2eff9dd

## Self-Check: PASSED
