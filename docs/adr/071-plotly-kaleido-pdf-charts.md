# ADR-071: Plotly + Kaleido for PDF Charts, Playwright Removed

**Status:** Accepted
**Date:** 2026-02-25

## Context

PDF export previously relied on Playwright (headless Chromium) to capture the NiceGUI
report page — including its interactive ECharts visualisations — and print it as PDF.
While this produced high-fidelity output, it introduced several problems:

- **Docker image bloat:** Chromium and its system dependencies add ~400 MB to the image.
- **Non-root permission complexity:** A dedicated `PLAYWRIGHT_BROWSERS_PATH` env var plus
  `chmod -R o+rX` were required to make the browser accessible to the non-root `appuser`
  (ADR-070).
- **Startup fragility:** Any mismatch between the installed Chromium and the `playwright`
  Python package version breaks all PDF exports silently.
- **Async constraint:** Playwright requires a running NiceGUI server reachable on
  `localhost`, making PDF generation impossible outside the web context.

A full ReportLab PDF generator (`pdf_report.py`) already existed and was tested, but
was bypassed in favour of the Playwright path. The only part lacking a pure-Python
equivalent was the Sankey diagram, which was rendered via matplotlib — producing an
aesthetically poor result compared with the ECharts Sankey in the web UI.

## Decision

1. **Replace matplotlib Sankey with Plotly Sankey** (`plotly.graph_objects.Sankey`).
   The chart is exported as a PNG via **kaleido** and embedded into the ReportLab PDF
   as an `Image` flowable — the same interface as before.

2. **Wire the existing ReportLab path** in both the Report page and the new
   `generate_layout_pdf()` function, replacing the Playwright call in both download
   handlers.

3. **Remove Playwright** from `pyproject.toml` and the `Dockerfile`. The Playwright
   browser install layer is deleted entirely.

4. **Remove matplotlib** from `pyproject.toml` (it was only used for the Sankey).

5. **Delete dead code:** `playwright_pdf.py`, `report_print.py`, `print_session.py`.

## Rationale

- **Kaleido** is a self-contained binary (~50 MB) with zero system dependencies — no
  browser engine, no X11, no GTK. It is substantially lighter than Chromium (~400 MB).
- **Plotly Sankey** closely matches the ECharts Sankey style: visible nodes, link flows,
  Dell brand colours, white background.
- **ReportLab** already handles text, styled tables, Vera fonts, and page headers; it
  is the right tool for document layout and is kept as-is.
- The net Docker image saving is **~430 MB** (Playwright Chromium ~400 MB + matplotlib
  ~30 MB − kaleido ~50 MB).

## Alternatives Considered

- **Keep Playwright, replace matplotlib only:** Reduces image by ~30 MB but leaves
  Chromium (~400 MB) and all associated complexity in place. Rejected.
- **Replace ReportLab with Plotly entirely:** Plotly `go.Table` lacks the styling
  precision of `ReportLab.TableStyle` (no per-cell borders, limited padding). The
  migration would rewrite ~1,000 lines of tested code for no meaningful gain. Rejected.
- **WeasyPrint:** Requires cairo + pango (~200–400 MB of system libs) and does not
  execute JavaScript, so ECharts charts would be blank. Already rejected in ADR-025.

## Consequences

- All four PDF charts (Sankey, Pie, DRR bar, Before/After bar) are preserved; only
  the Sankey rendering engine changes (matplotlib → Plotly/kaleido).
- The Docker image shrinks by ~430 MB.
- `generate_layout_pdf()` is a new public function in `pdf_report.py`; it accepts an
  optional `PlacementConstraints` argument so the Layout page can pass user-configured
  constraints.
- The HTML print routes (`/report/print`, `/layout/print`) and the one-time print
  session token mechanism are removed — they existed solely to serve Playwright.
- ADR-070 is superseded: `PLAYWRIGHT_BROWSERS_PATH` is no longer set in the Dockerfile.
