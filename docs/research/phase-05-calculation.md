# Phase 5: Calculation & PDF Report - Research

**Researched:** 2026-02-19
**Domain:** Capacity calculation engine + PDF report generation (ReportLab)
**Confidence:** HIGH

## Summary

Phase 5 completes the StorePredict pipeline by adding a calculation service that computes per-VM required capacity and workload-grouped totals, a report page displaying summary cards and breakdown tables, and a one-page PDF export using ReportLab.

ReportLab 4.4.10 is already installed. It ships with Bitstream Vera TTF fonts that fully support French characters. The Platypus high-level framework (`SimpleDocTemplate`, `Table`, `Paragraph`) handles content flow, table rendering, and font embedding automatically.

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| PDF library | ReportLab Platypus (not WeasyPrint) | No system dependencies, already installed |
| Font | Vera TTF (bundled) | Covers French chars, ships with ReportLab |
| Download | `ui.download` with positional `src` arg | NiceGUI API, no disk I/O |
| Weighted avg DRR | `total_provisioned / total_required` | Mathematically correct, simpler than per-group averaging |
| DRR guard | `max(drr, 0.1)` | Prevents division by zero |

## Architecture

```
pipeline/calculation.py    # Pure data, no UI dependency
services/pdf_report.py     # ReportLab PDF generation
ui/pages/report.py         # Report page with download button
```

## Pitfalls Addressed

1. **Division by zero** — DRR of 0 guarded with `max(drr, 0.1)`
2. **Empty dataset** — Early return for zero rows
3. **Vera font in Docker** — Path derived from `reportlab.__file__` at runtime
4. **Large tables** — Workload group summary (not per-VM) fits one page
5. **Session data shape** — `.get(key, default)` for all field accesses

## Sources

- ReportLab docs: Platypus framework, Table styling, TTF font registration
- NiceGUI docs: `ui.download`, file serving patterns
- Context7: `/websites/reportlab`, `/websites/nicegui_io`
