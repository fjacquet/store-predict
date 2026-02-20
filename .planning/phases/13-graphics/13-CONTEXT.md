# Phase 13: graphics - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add data visualizations (charts and diagrams) to both the PDF report and the web UI report page. The goal is to make the capacity analysis and DRR story more compelling for pre-sales customer presentations. This phase delivers the chart library wiring, chart rendering logic, and placement — not new analysis capabilities.

</domain>

<decisions>
## Implementation Decisions

### What to visualize
- **Sankey diagram** — data reduction flow: Provisioned → Required (the core "savings story")
  - Show both aggregate flow AND per-workload-category breakdown (two representations)
- **Workload category breakdown** — pie/donut chart: % of capacity per workload type
- **DRR by category** — bar chart: which workloads compress best (justifies sizing)
- **Before/after capacity** — side-by-side bar: raw provisioned vs required after DRR

Total: 4 chart types (Sankey aggregate, Sankey breakdown, pie, DRR bar, before/after bar — researcher may merge Sankey representations)

### Chart placement in PDF
- Add a **second page** dedicated to visuals
- Page 1 stays unchanged (summary stats + workload breakdown table)
- Page 2 = all charts
- Pre-sales can print both pages or present page 2 on screen to customers

### Chart placement in web UI
- Charts appear on the **report page** alongside existing summary cards and table
- Interactive (ECharts) in browser, static equivalents embedded in PDF page 2

### Web UI chart library
- **NiceGUI `ui.echart`** (Apache ECharts) — already in NiceGUI, no extra dep
- ECharts supports Sankey, bar, pie natively with rich theming

### PDF chart library
- **ReportLab built-in charts** for bar and pie charts (no extra dep)
- **matplotlib** for Sankey only — render to PNG buffer via `BytesIO`, embed in PDF via `ImageReader` (same pattern as logo embedding in Phase 10)
- Maintainability justifies the dep: `matplotlib.sankey.Sankey` is declarative; adding a new workload category is a one-liner. Custom ReportLab primitives would require geometric recalculation.
- `matplotlib>=3.8` added to runtime dependencies; import isolated to PDF chart module

### Color scheme
- **Dell blue (#007DB8) as primary**, greys as secondary — consistent with existing PDF header
- **Sankey node colors:** Dell blue for "provisioned" (before) node, lighter blue/green for "required" (after) node — visually encodes the reduction/savings
- Workload category charts use Dell blue + grey tones (not per-category distinct colors)

### Claude's Discretion
- Exact chart dimensions and spacing on PDF page 2
- ECharts theme/option details for web UI
- How to handle very small datasets (1-2 workload categories) — researcher/planner decides

</decisions>

<specifics>
## Specific Ideas

- Sankey is the centerpiece visualization — shows the DRR "magic" in a single compelling diagram
- PDF page 2 should be printable and look good standalone (self-contained visuals page)
- Web charts should be interactive (hover tooltips, etc.) — ECharts provides this by default
- Dell blue → green gradient on Sankey "after" node creates a positive "savings" visual impression

</specifics>

<deferred>
## Deferred Ideas

- None raised — discussion stayed within phase scope

</deferred>

---

*Phase: 13-graphics*
*Context gathered: 2026-02-20*
