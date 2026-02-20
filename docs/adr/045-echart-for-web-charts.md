# ADR 045: ECharts (NiceGUI ui.echart) for interactive web charts

**Date:** 2026-02-20
**Status:** Accepted

## Context

Phase 13 adds data visualizations to the report page (Sankey, pie, bar charts). NiceGUI provides a built-in `ui.echart` component wrapping Apache ECharts. Alternative considered: `ui.plotly` (also built-in).

## Decision

Use NiceGUI's `ui.echart` (Apache ECharts) for all interactive charts on the web report page.

## Rationale

- Zero new runtime dependencies — `ui.echart` ships with NiceGUI
- Apache ECharts has native Sankey support, which is the centerpiece visualization
- ECharts supports all required chart types: Sankey, pie/donut, bar
- Theming via ECharts option object — Dell blue palette applied declaratively
- `ui.plotly` was rejected because Plotly adds a heavier client-side bundle and ECharts Sankey is cleaner

## Consequences

- Chart configs are Apache ECharts option dicts passed to `ui.echart`
- All web charts styled with Dell blue (#007DB8) primary, grey secondary
- Sankey nodes: Dell blue for "provisioned" input, lighter blue/green for "required" output
