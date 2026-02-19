# ADR-025: PDF with ReportLab Platypus (not WeasyPrint)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The sizing report must be exported as a one-page PDF. Two Python PDF libraries were evaluated: ReportLab and WeasyPrint.

## Decision

Use ReportLab with the Platypus layout engine for PDF generation.

## Rationale

- ReportLab is approximately 5 MB and is pure Python with no native dependencies
- WeasyPrint requires cairo and pango system libraries (200-400 MB total), complicating Docker images
- Platypus handles multi-column layout and automatic page flow
- ReportLab is widely used in enterprise Python contexts with stable API

## Alternatives Considered

- **WeasyPrint:** HTML+CSS authoring is more intuitive, but the native library dependency makes it unsuitable for a minimal Docker deployment

## Consequences

- PDF layout is coded in Python using ReportLab primitives, not HTML/CSS (more verbose)
- The Docker image remains slim because no native rendering libraries are required
- Font handling requires explicit registration (see ADR-026)
