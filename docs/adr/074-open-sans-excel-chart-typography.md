# ADR-074 — Open Sans typography in Excel export and PDF charts

**Date:** 2026-02-25
**Status:** Accepted
**Deciders:** Pre-sales engineering team
**Tags:** typography, excel, pdf, charts

---

## Context

After ADR-073 introduced Open Sans fonts for the PDF report body text and KPI cards (v7.1.2), two areas remained in their default fonts:

1. **PDF charts** (bar charts, pie chart, Sankey) — ReportLab `VerticalBarChart` and `Pie` axis/slice labels defaulted to Helvetica; matplotlib `ax.text()` in the Sankey used the system default sans-serif.
2. **Excel export** — all XlsxWriter `add_format()` calls omitted `font_name`, resulting in Calibri (Excel's default) regardless of the brand font used in the PDF.

Both issues created visual inconsistency: an Open Sans PDF paired with Calibri Excel and Helvetica chart labels.

---

## Decisions

### D1 — Apply Open Sans to all PDF chart labels

**Decision:** Add `fontName = FONT_REGULAR` to `VerticalBarChart.categoryAxis.labels`, `valueAxis.labels`, and `Pie.slices`; pass `FontProperties(fname=FONT_PATH_LIGHT)` to all matplotlib `ax.text()` calls in the Sankey.

**Rationale:** Charts are part of the same PDF document and must match body typography. Both ReportLab drawing primitives and matplotlib accept explicit font configuration.

**Note:** `Pie.slices.label_fontName` is **not** a valid attribute (`WedgeProperties` raises `validateSetattr`). The correct attribute is `Pie.slices.fontName`.

---

### D2 — Shared `_fonts.py` module for font constants

**Decision:** `FONT_REGULAR`, `FONT_BOLD`, `FONT_PATH_LIGHT`, and `FONT_PATH_BOLD` are defined once in `src/store_predict/services/_fonts.py` and imported by both `pdf_report.py` and `pdf_charts.py`.

**Rationale:** `pdf_report.py` imports `pdf_charts.py`; a back-import would create a circular dependency. A dedicated shared module resolves this cleanly without duplicating font registration logic.

---

### D3 — Apply Open Sans to Excel cell formats

**Decision:** All `wb.add_format()` calls in `excel_report.py` specify:
- `"font_name": "Open Sans"` — bold, header, and totals formats
- `"font_name": "Open Sans Light"` — body, number, and alternate-row formats

**Rationale:** A pre-sales engagement typically delivers both a PDF summary and an Excel workbook. Consistent typography across both outputs projects a more professional, brand-aligned appearance.

---

### D4 — No font embedding in Excel; no fallback chain

**Decision:** XlsxWriter does not support font embedding or fallback font stacks. The font name is written as-is into the `.xlsx`. If the recipient lacks Open Sans, Excel will auto-substitute a visually similar font (typically Calibri or Arial).

**Alternatives considered:**
- Switch to `"Calibri Light"` (universal on Windows/macOS) — rejected; departs from brand typography.
- Embed font subset — not supported by XlsxWriter or the `.xlsx` format for cell fonts.

**Accepted trade-off:** Recipients without Open Sans installed see a substituted font; those with it (common on modern systems where it ships with Office 365 or is freely downloadable) see the intended appearance.

---

## Consequences

- `_fonts.py` is now the single source of truth for font registration and path constants across all PDF and Excel output services.
- PDF charts (bar, pie, Sankey) render in Open Sans, matching document body text.
- Excel workbook uses Open Sans / Open Sans Light, matching the PDF report.
- No new dependencies introduced.
- Font fallback in Excel is handled implicitly by the Excel application on the recipient's machine.
