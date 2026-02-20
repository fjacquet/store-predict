# ADR 047: matplotlib for Sankey diagram in PDF

**Date:** 2026-02-20
**Status:** Accepted

## Context

Phase 13 requires a Sankey diagram in the PDF report (Provisioned → Required capacity flow, both aggregate and per-workload breakdown). ReportLab's built-in `reportlab.graphics.charts` has no native Sankey support. A custom ReportLab implementation using drawing primitives would be complex to build and hard to maintain as the workload category set evolves.

## Decision

Add **matplotlib** as a runtime dependency, used exclusively to render the Sankey diagram. The rendered figure is saved to a `BytesIO` PNG buffer and embedded in the ReportLab PDF via `reportlab.lib.utils.ImageReader`. All other PDF charts continue to use ReportLab built-ins.

## Rationale

- **Maintainability is the priority.** `matplotlib.sankey.Sankey` provides a declarative API — updating node labels, colors, or adding a new workload category is a one-liner change. Custom ReportLab bezier curves would require geometric recalculation on every data change.
- matplotlib is a well-maintained, stable library with long-term support. Its presence in the scientific Python ecosystem is essentially permanent.
- The PNG-embed pattern is already established in the codebase via Pillow (`_preprocess_logo` in Phase 10) — the same `ImageReader` path is used here.
- matplotlib is only imported in the PDF chart module, keeping the dependency surface minimal and the import cost isolated.

## Implementation Notes

- Sankey rendered at high DPI (150+) for print quality, then scaled to fit PDF column width
- Figure background set to white to match PDF page background
- Dell blue (#007DB8) for input nodes, lighter blue-green for output nodes — matches web ECharts palette
- `plt.close(fig)` called immediately after `savefig()` to avoid memory leaks in long-running server context

## Consequences

- `matplotlib>=3.8` added to runtime dependencies in `pyproject.toml`
- All other PDF charts (bar, pie) remain ReportLab built-in — matplotlib usage is strictly Sankey-only
- Tests for the Sankey chart compare PNG buffer size / non-emptiness (not pixel content)
