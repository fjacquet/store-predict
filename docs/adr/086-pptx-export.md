# ADR-086: PowerPoint (PPTX) export

## Status
Accepted — 2026-05-23

## Context
Pre-sales engineers present StorePredict sizing results to customers in
PowerPoint. The existing PDF and Excel exports cover the technical report and
the data workbook, but not a presentation-ready deliverable.

## Decision
Add a `.pptx` export to the `/report` page using `python-pptx`. The deck is a
hybrid: a concise customer-facing pitch (title, executive summary, DRR story,
workload mix, recommendation) followed by a technical appendix (full breakdown
table, layout strategies, health findings, charts). Charts with a native
PowerPoint equivalent (pie, column) are added as editable charts; the Sankey
flow has no native type and is embedded as an image rendered by the shared
matplotlib renderer (`pdf_charts.render_sankey_png`). Branding matches the PDF
deliverable and the deck is self-contained (no template upload in v1).

The code mirrors the existing export pattern: `services/pptx_report.py`
(composition) + `services/pptx_charts.py` (charts), called from `report.py` via
`run.io_bound` and `ui.download`.

## Consequences
- New runtime dependency: `python-pptx`.
- The Sankey renderer was refactored to a reusable `render_sankey_png()` shared
  by the PDF flowable and the PPTX picture.
- The layout-planner page keeps its own PDF/Excel exports; PPTX is scoped to the
  main report page for now. A corporate-template-injection mode is a possible
  future enhancement.
