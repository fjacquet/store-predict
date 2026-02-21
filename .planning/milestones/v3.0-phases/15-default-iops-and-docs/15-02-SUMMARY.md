---
phase: 15-default-iops-and-docs
plan: "02"
subsystem: documentation
tags: [adr, research, architecture, changelog, mkdocs, iops, layout-engine]
dependency_graph:
  requires: []
  provides:
    - ADR-059 documenting IOPS defaults decision
    - research page with IOPS domain knowledge
    - architecture.md updated to 4-stage pipeline
    - CHANGELOG.md v3.0.0 entry
  affects:
    - docs/adr/index.md
    - docs/research/index.md
    - mkdocs.yml nav
tech_stack:
  added: []
  patterns:
    - ADR format following existing 001-058 structure
    - MkDocs Material nav entries for new pages
    - CHANGELOG versioned sections
key_files:
  created:
    - docs/adr/059-default-iops-estimates.md
    - docs/research/phase-15-default-iops.md
  modified:
    - docs/adr/index.md
    - docs/research/index.md
    - mkdocs.yml
    - docs/architecture.md
    - CHANGELOG.md
decisions:
  - "ADR-059: Workload-based IOPS defaults accepted; 50 IOPS for all generic VMs (conservative, no OS distinction)"
  - "Linux vs. Windows IOPS split not implemented — documented as known limitation in ADR-059"
  - "mkdocs.yml nav corrected: ADRs 048-058 added, ADRs 015-033 filenames fixed (pre-existing bug)"
metrics:
  duration_seconds: 267
  completed_date: "2026-02-21"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 5
---

# Phase 15 Plan 02: Documentation — ADR-059, Research Page, Architecture, Changelog Summary

ADR-059 and research page documenting workload-based IOPS defaults, plus architecture.md updated to 4-stage pipeline and CHANGELOG.md v3.0.0 entry for layout engine.

## Objective

Write all documentation for the layout engine and IOPS defaults: ADR-059, research page, architecture update, and CHANGELOG entry.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Write ADR-059 and research page with index/nav updates | 1b0d4d4 | docs/adr/059-default-iops-estimates.md, docs/research/phase-15-default-iops.md, docs/adr/index.md, docs/research/index.md, mkdocs.yml |
| 2 | Update architecture.md and CHANGELOG.md for layout engine | 7ac28f7 | docs/architecture.md, CHANGELOG.md |

## What Was Built

### ADR-059: Workload-based IOPS defaults for RVTools sizing

Documents the architectural decision to inject workload-based IOPS estimates
when `CalculationSummary.has_performance_data` is `False`. Covers:
- Context: RVTools has no IOPS data; layout engine IOPS constraint inactive
- Decision: `_apply_default_iops()` injects estimates from `samples/IOPS.csv`
- Default values for 8 workload categories (SQL 500, Oracle 800, SAP HANA 1000, VDI 30-50, generic 50, File 100)
- Known limitation: Linux vs. Windows split not implemented

### Research Page: phase-15-default-iops.md

Covers IOPS domain knowledge including:
- Problem statement (RVTools has no performance data)
- IOPS values table with sources (Dell H18264, VMware Horizon, SAP HANA sizing)
- Why peak IOPS, not average (pre-sales must size for peak load)
- Conservative bias rationale
- CSV configurability following DRR.csv pattern
- Known limitation: Linux vs. Windows IOPS split

### Architecture.md Updates

- Overview: "3-stage pipeline" updated to "4-stage pipeline"
- Pipeline Architecture Mermaid: layout stage added (Layout Engine node + LayoutProposal[] node)
- Data Flow Mermaid: LayoutProposal[] step added between SizingSummary and PDF
- Key Components: new Layout Engine section documenting layout_models.py and layout_engine.py

### CHANGELOG.md

v3.0.0 section added documenting layout engine, default IOPS estimates, documentation, and tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken mkdocs.yml nav filenames for ADRs 015-033**
- **Found during:** Task 1 verification (mkdocs build --strict)
- **Issue:** ADRs 015-033 in mkdocs.yml nav referenced non-existent filenames (e.g., `015-calculation-dataclass.md` instead of `015-canonical-dataframe-schema.md`). These were pre-existing bugs causing mkdocs build --strict to fail.
- **Fix:** Updated all 19 incorrect filename references to match actual files on disk
- **Files modified:** mkdocs.yml
- **Commit:** 1b0d4d4

**2. [Rule 2 - Missing] Added ADRs 048-058 to mkdocs.yml nav**
- **Found during:** Task 1 (reading mkdocs.yml — nav only went to 047)
- **Issue:** ADRs 048-058 existed in `docs/adr/` and in `docs/adr/index.md` but were missing from mkdocs.yml nav, making them unreachable from navigation
- **Fix:** Added all missing ADRs (048-058) to mkdocs.yml nav
- **Files modified:** mkdocs.yml
- **Commit:** 1b0d4d4

**3. [Rule 2 - Missing] Added Phase 14 research to mkdocs.yml nav**
- **Found during:** Task 1 (checking mkdocs.yml Research nav section)
- **Issue:** Phase 14 research page existed but was not in mkdocs.yml nav
- **Fix:** Added Phase 14 research nav entry before Phase 15
- **Files modified:** mkdocs.yml
- **Commit:** 1b0d4d4

## Self-Check: PASSED

All claimed artifacts verified:
- `docs/adr/059-default-iops-estimates.md` exists and contains "ADR-059"
- `docs/research/phase-15-default-iops.md` exists and contains "Default IOPS"
- `docs/adr/index.md` contains "059"
- `docs/research/index.md` contains "Phase 15"
- `docs/architecture.md` contains "Layout Engine" and "4-stage pipeline"
- `CHANGELOG.md` contains "v3.0.0"
- `mkdocs build --strict` builds cleanly (only pre-existing Material theme version warning)
- Commits 1b0d4d4 and 7ac28f7 verified in git log
