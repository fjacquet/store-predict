---
phase: 29
slug: reporting-fidelity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `rtk pytest tests/test_calculation.py tests/test_classifier.py tests/test_pdf_charts.py -x -q` |
| **Full suite command** | `rtk pytest` |
| **Estimated runtime** | ~30 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `rtk pytest tests/test_calculation.py tests/test_classifier.py tests/test_pdf_charts.py -x -q`
- **After every plan wave:** Run `rtk pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 29-A-01 | P01 | 1 | DRR-01 | unit | `rtk pytest tests/test_calculation.py -k "drr" -x -q` | ⬜ pending |
| 29-A-02 | P01 | 1 | DRR-02 | unit | `rtk pytest tests/test_pdf_report.py -k "workload" -x -q` | ⬜ pending |
| 29-A-03 | P01 | 1 | DRR-03 | unit | `rtk pytest tests/test_excel_report.py -k "workload" -x -q` | ⬜ pending |
| 29-B-01 | P02 | 1 | CLASSIF-01 | unit | `rtk pytest tests/test_classifier.py -k "backup or veritas or netbackup" -x -q` | ⬜ pending |
| 29-B-02 | P02 | 1 | CLASSIF-02 | unit | `rtk pytest tests/test_classifier.py -k "nagios or solarwinds or monitoring" -x -q` | ⬜ pending |
| 29-B-03 | P02 | 1 | CLASSIF-03 | unit | `rtk pytest tests/test_classifier.py -k "redis" -x -q` | ⬜ pending |
| 29-C-01 | P03 | 1 | REPORT-01 | unit | `rtk pytest tests/test_pdf_charts.py -x -q` | ⬜ pending |
| 29-C-02 | P03 | 1 | REPORT-02 | unit | `rtk pytest tests/test_pdf_charts.py -x -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_calculation.py` — add tests for `(category, drr)` grouped `WorkloadGroupResult` with DRR-differing same-category VMs
- [ ] `tests/test_classifier.py` — add parametrized tests for new VM name patterns (Veritas, NetBackup, Nagios, SolarWinds, Redis)
- [ ] `tests/test_pdf_charts.py` — add/verify test that `make_sankey_image_flowable()` uses DPI ≥ 300

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sankey PDF visually sharp at 100% zoom | REPORT-01 | Pixel quality requires visual inspection | Generate PDF with sample data, open at 100% zoom, confirm no blurriness |
| ECharts Sankey shows two nodes for same-category different-DRR | DRR-01 | Web UI Sankey rendering requires browser | Upload test file with SQL (DRR=5) and SQL Encrypted (DRR=1), check /report Sankey shows two distinct SQL nodes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
