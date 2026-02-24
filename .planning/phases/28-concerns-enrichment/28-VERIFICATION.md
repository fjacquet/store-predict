---
phase: 28-concerns-enrichment
verified: 2026-02-24T12:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Open /concerns after uploading an RVTools file with missing OS VMs"
    expected: "Each finding card shows remediation hint in italic gray text below the detail line"
    why_human: "UI rendering and CSS italic style cannot be confirmed programmatically"
  - test: "Click Export PDF button on /concerns page"
    expected: "Browser downloads a file named 'concerns-report.pdf' (or 'rapport-preoccupations.pdf' in FR) containing finding cards with remediation hints"
    why_human: "Download trigger and file open behavior require browser interaction"
  - test: "Click Export CSV button on /concerns page"
    expected: "Browser downloads a file named 'concerns-report.csv' that opens cleanly in Excel with 7 columns including remediation"
    why_human: "Excel compatibility (UTF-8 BOM rendering) requires manual file open verification"
---

# Phase 28: Concerns Enrichment Verification Report

**Phase Goal:** Each health finding on /concerns includes an actionable remediation hint, and the full concerns report is exportable as a standalone PDF or CSV
**Verified:** 2026-02-24
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every HealthFinding dataclass instance carries a non-empty remediation string | VERIFIED | `HealthFinding.remediation: str = ""` field at line 61 of health_checks.py; all 13 check functions populate non-empty strings |
| 2 | All 13 check functions (14 finding types) populate the remediation field with an actionable sentence | VERIFIED | Direct inspection of health_checks.py: `_check_missing_os`, `_check_zero_provisioned`, `_check_missing_cpu`, `_check_missing_ram`, `_check_high_powered_off_ratio`, `_check_high_unknown_ratio`, `_check_large_unknown_vms`, `_check_iops_budget_exceeded`, `_check_no_cluster`, `_check_hw_version_per_cluster` (very_old + old), `_check_small_cluster_ha`, `_check_tools_status` (not_installed + not_running) -- all 14 types confirmed |
| 3 | The /concerns page renders remediation text in muted italic style | VERIFIED | `concerns.py` line 72-73: `if finding.remediation: ui.label(finding.remediation).classes("text-sm text-gray-500 italic mt-1")` |
| 4 | User can click Export PDF on /concerns and download a standalone concerns PDF | VERIFIED | Export button wired at concerns.py line 156-163; `generate_concerns_pdf` returns `%PDF` bytes confirmed by test `test_generate_concerns_pdf_returns_bytes` |
| 5 | User can click Export CSV on /concerns and download a CSV with one row per finding | VERIFIED | Export button wired at concerns.py line 164-171; CSV header `severity,check_id,title,detail,remediation,affected_count,cluster` confirmed by test `test_generate_concerns_csv_header_row` |
| 6 | PDF and CSV exports are independent of the main sizing report pipeline | VERIFIED | `concerns_export.py` imports only from `store_predict.pipeline.health_checks` and stdlib/reportlab -- zero UI imports confirmed |
| 7 | Tests verify remediation field and both export functions | VERIFIED | 70 tests pass: 60 in test_health_checks.py (including 3 `TestRemediationField` tests) + 10 in test_concerns_export.py (5 CSV + 5 PDF tests) |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/store_predict/pipeline/health_checks.py` | HealthFinding dataclass with remediation field, all check functions updated | VERIFIED | `remediation: str = ""` at line 61; 14 finding constructors set non-empty strings |
| `src/store_predict/ui/pages/concerns.py` | UI card rendering remediation hint in italic muted style; Export PDF and Export CSV buttons | VERIFIED | Lines 72-73 (remediation display); lines 155-171 (export buttons using `ui.download()`) |
| `src/store_predict/services/concerns_export.py` | `generate_concerns_pdf()` and `generate_concerns_csv()` functions | VERIFIED | Module exists, `__all__ = ["generate_concerns_csv", "generate_concerns_pdf"]` at line 26; both functions substantive (259 lines, full ReportLab Platypus implementation) |
| `tests/test_health_checks.py` | Tests verifying remediation field presence | VERIFIED | `TestRemediationField` class with 3 tests at lines 526-551 |
| `tests/test_concerns_export.py` | Tests for both export functions | VERIFIED | 10 tests: `TestGenerateConcernsCsvHeader`, `TestGenerateConcernsCsvRows`, `TestGenerateConcernsPdf` classes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/store_predict/pipeline/health_checks.py` | `src/store_predict/ui/pages/concerns.py` | `HealthFinding.remediation` field read in `_render_finding_card` | WIRED | `finding.remediation` at concerns.py line 72 |
| `src/store_predict/ui/pages/concerns.py` | `src/store_predict/services/concerns_export.py` | `import generate_concerns_pdf, generate_concerns_csv` | WIRED | `from store_predict.services.concerns_export import generate_concerns_csv, generate_concerns_pdf` at concerns.py line 9; both called via `ui.download()` lambdas at lines 160, 168 |
| `src/store_predict/services/concerns_export.py` | `reportlab.platypus` | `SimpleDocTemplate + Paragraph + Table` | WIRED | `from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle` at line 22; `SimpleDocTemplate(buf, ...)` instantiated at line 111; `doc.build(story)` at line 301 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONC-01 | 28-01-PLAN.md | Each health finding on /concerns displays an actionable remediation hint explaining what to do about the issue | SATISFIED | `HealthFinding.remediation` field populated in all 14 finding types; rendered via `_render_finding_card` in italic gray; 3 tests in `TestRemediationField` confirm |
| CONC-02 | 28-02-PLAN.md | User can export the /concerns page as a standalone PDF report | SATISFIED | `generate_concerns_pdf()` in `concerns_export.py` produces `%PDF` bytes via ReportLab Platypus; Export PDF button in `concerns_page()` triggers `ui.download()`; 5 PDF tests pass |
| CONC-03 | 28-02-PLAN.md | User can export the /concerns page as a standalone CSV file with all findings and remediation hints | SATISFIED | `generate_concerns_csv()` in `concerns_export.py` produces UTF-8-BOM bytes with header `severity,check_id,title,detail,remediation,affected_count,cluster`; Export CSV button triggers `ui.download()`; 5 CSV tests pass including BOM and severity-value tests |

**All 3 requirements satisfied. No orphaned requirements.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns detected in any modified file |

### Human Verification Required

#### 1. Remediation hint rendering on /concerns page

**Test:** Open /concerns after uploading an RVTools file that triggers at least one health finding (e.g., a file with VMs missing OS names)
**Expected:** Each finding card shows the remediation hint in italic gray text below the detail description line
**Why human:** CSS italic style and visual rendering cannot be verified programmatically

#### 2. Export PDF button download

**Test:** Click the "Export PDF" button (or "Exporter PDF" in FR locale) on the /concerns page after loading data
**Expected:** Browser downloads a file named `concerns-report.pdf` (or `rapport-preoccupations.pdf`); file opens as a PDF with cover header, severity summary, and one finding table per health concern including remediation hint text
**Why human:** Browser download trigger and file open behavior require interactive testing

#### 3. Export CSV button download and Excel compatibility

**Test:** Click the "Export CSV" button on the /concerns page and open the downloaded CSV in Microsoft Excel
**Expected:** File opens without encoding prompt; shows 7 columns (severity, check_id, title, detail, remediation, affected_count, cluster); one row per finding with readable text
**Why human:** UTF-8 BOM Excel rendering and column display require manual file inspection

### Gaps Summary

No gaps. All automated checks passed. Phase goal is fully achieved at the code level.

All 3 success criteria from ROADMAP.md are satisfied:
1. Every finding card on /concerns displays a remediation hint (hardcoded English, italic gray, conditional on non-empty)
2. Export PDF button wired to `generate_concerns_pdf()` via `ui.download()` -- returns valid `%PDF` bytes
3. Export CSV button wired to `generate_concerns_csv()` via `ui.download()` -- returns UTF-8-BOM CSV with all 7 required columns including remediation

The 4th success criterion ("independent of main sizing report, no navigation away required") is also satisfied: both export functions are pure service-layer functions with zero UI imports, callable directly from the /concerns page.

---

_Verified: 2026-02-24_
_Verifier: Claude (gsd-verifier)_
