# ADR 047: Sankey diagram strategy for PDF (ReportLab constraint)

**Date:** 2026-02-20
**Status:** Proposed — researcher must resolve

## Context

Phase 13 requires a Sankey diagram in the PDF report (Provisioned → Required capacity flow). ReportLab's built-in `reportlab.graphics.charts` module does not include a Sankey chart type. User preference is to avoid adding new dependencies (no matplotlib).

## Options Considered

1. **Custom ReportLab drawing** — Implement Sankey using `reportlab.graphics.shapes` primitives (rectangles, lines, bezier curves). No new deps. High implementation effort.
2. **matplotlib (Sankey only)** — Add matplotlib as a dep, render Sankey to PNG, embed via `reportlab.lib.utils.ImageReader`. Clean output. New dep (~50 MB).
3. **Simplified flow diagram** — Replace full Sankey with a simpler before/after horizontal bar showing the reduction ratio, built with ReportLab bar charts. No new deps. Less visually impactful than Sankey.

## Decision

**Researcher must investigate and recommend.** The constraint is:
- User chose "ReportLab built-in charts" (no extra deps)
- User also explicitly wants a Sankey as the centerpiece visualization

## Acceptance Criteria for Resolution

The researcher should evaluate whether:
- A convincing Sankey can be built with ReportLab primitives at acceptable complexity
- matplotlib is justified for Sankey-only (user may accept it once trade-off is explained)
- A simplified "flow arrow" visualization satisfies the Sankey intent without the complexity

## Consequences

This ADR gates the Phase 13 research and planning. The researcher should produce a concrete recommendation with a code sketch or complexity estimate.
