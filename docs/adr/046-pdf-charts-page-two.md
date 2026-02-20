# ADR 046: PDF charts on a dedicated second page

**Date:** 2026-02-20
**Status:** Accepted

## Context

Phase 13 adds charts to the PDF report. The existing report is a single page (summary stats + workload breakdown table). Adding 4 chart types (Sankey aggregate, Sankey per-workload breakdown, capacity pie, DRR bar, before/after capacity bar) cannot fit on one page without compromising readability.

## Decision

Add a second page to the PDF report dedicated to data visualizations. Page 1 remains unchanged (summary stats + workload breakdown table). Page 2 contains all charts.

## Rationale

- Preserves the existing one-page summary for quick reference
- Pre-sales engineers can print both pages or show page 2 on screen as a standalone visual story
- No risk of pushing existing content to overflow (one-page constraint stays for page 1)
- Visuals-only page is self-contained and works as a customer-facing slide equivalent

## Consequences

- `generate_report_pdf()` now produces a two-page PDF
- PDF tests that check page count need updating
- Page 2 layout designed with printability in mind — charts arranged in a 2×2 or similar grid
- ReportLab `SimpleDocTemplate` continues to be used; second page handled by Platypus flow naturally when content overflows page 1 boundary
