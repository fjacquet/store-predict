# ADR-026: Vera TTF Fonts for French Characters

**Status:** Accepted
**Date:** 2026-02-19

## Context

The PDF report must render French text including accented characters (é, è, ê, à, ç). ReportLab's default Type 1 fonts do not cover the full Latin-1 extended range reliably.

## Decision

Register ReportLab's bundled Bitstream Vera TTF fonts for all PDF text rendering. The font path is computed relative to the reportlab package installation directory.

## Rationale

- Bitstream Vera fonts are bundled with every ReportLab installation; no download required
- TTF registration via `pdfmetrics.registerFont` provides full Unicode support
- Path computation is portable across operating systems and virtual environments

## Alternatives Considered

- **DejaVu Sans:** Excellent Unicode coverage but requires downloading and bundling the font files separately
- **System fonts:** Not portable; fonts available in the Docker container may differ from the developer's machine

## Consequences

- The font path computation must be updated if ReportLab changes its package layout
- All text styles in the PDF must explicitly reference the registered Vera font names
