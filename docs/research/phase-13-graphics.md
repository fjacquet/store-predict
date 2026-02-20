# Phase 13: Graphics - Research

**Researched:** 2026-02-20
**Domain:** Data Visualization — NiceGUI/ECharts (web), ReportLab charts + matplotlib Sankey (PDF)
**Confidence:** HIGH

## Summary

Phase 13 adds four chart types to both the web UI report page and a new PDF page 2. The technology stack is fully locked: `ui.echart` (Apache ECharts) for the browser and ReportLab built-in charts plus matplotlib Sankey for the PDF. No new library wiring is needed for the web side — `ui.echart` ships with NiceGUI. Matplotlib is added as a runtime dependency (`matplotlib>=3.8`).

The core integration patterns are well understood. For the web UI, charts are created by passing a Python dict matching ECharts option schema to `ui.echart(options)`. For the PDF, ReportLab `Drawing` objects containing `VerticalBarChart` or `Pie` instances are directly `Flowable` and can be appended to the Platypus story. Page breaks use `PageBreak()` from `reportlab.platypus`. The matplotlib Sankey → PNG → BytesIO → `ImageReader` pipeline reuses the logo embedding pattern from Phase 10.

Data is sourced entirely from `CalculationSummary.workload_groups` (list of `WorkloadGroupResult`) and the summary totals. No pipeline changes are needed.

## Chart Types Delivered

| Chart | Web (ECharts) | PDF (ReportLab/matplotlib) |
|-------|--------------|---------------------------|
| Sankey — data reduction flow | `type: 'sankey'` with gradient links | matplotlib `Sankey`, rendered to PNG via BytesIO |
| Pie/donut — workload distribution | `type: 'pie'`, radius array for donut | ReportLab `Pie` from `reportlab.graphics.charts.piecharts` |
| Bar — DRR by category | `type: 'bar'`, single series | ReportLab `VerticalBarChart`, single series |
| Grouped bar — before vs after | `type: 'bar'`, two series | ReportLab `VerticalBarChart`, two series |

## Key Findings

### ui.echart — Zero Extra Dependencies

`ui.echart` wraps Apache ECharts and ships with NiceGUI. Chart configs are Python dicts matching ECharts option schema. ECharts natively supports Sankey, pie/donut, and bar types. Dell blue palette applied via `color` array at option root.

### Sankey Fallback for Small Datasets

When fewer than 2 workload groups exist, a Sankey diagram cannot render meaningfully (requires at least 2 intermediate nodes). The `echart_sankey_options()` function falls back to the before/after grouped bar chart in this case.

### matplotlib Lazy Import

`matplotlib` must not be imported at module level in `pdf_charts.py`. The import is deferred to inside `make_sankey_image_flowable()` to avoid startup overhead. `matplotlib.use("Agg")` must be called before importing `pyplot` to select the non-interactive backend required for server-side PNG rendering.

### Empty Data Guard — Spacer not Image

When `workload_groups` is empty, `make_sankey_image_flowable()` returns a `Spacer(width, 0)` rather than `Image(BytesIO(b""), ...)`. ReportLab's `Image` immediately tries to read the provided bytes — passing empty bytes raises `UnidentifiedImageError`. A `Spacer` is the correct zero-height placeholder.

### PDF Page 2 Header

The `doc.build()` call accepts both `onFirstPage` and `onLaterPages` callbacks. Passing the same `_draw_header()` call to both ensures the Dell branded header appears on the chart page as well as the summary page.

### Dell Colour Palette

- Primary: `#007DB8` (Dell blue) — provisioned nodes, main bars
- Secondary: `#40A8D8` (light blue) — required/after nodes and bars
- Greys: `#6C757D`, `#ADB5BD`, `#CED4DA`, `#DEE2E6` — workload category nodes, pie slices
