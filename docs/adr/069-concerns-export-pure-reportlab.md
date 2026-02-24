# ADR-069: Standalone concerns export as pure ReportLab (no Playwright)

**Date:** 2026-02-24
**Status:** Accepted

## Context

CONC-02 requires a standalone PDF export of the `/concerns` page. Three
approaches were considered:

1. **Playwright print-to-PDF** — render the `/concerns` page in a headless
   browser and print it. Already used for the main sizing report.
2. **WeasyPrint** — convert HTML to PDF. Large Docker image (~200–400 MB
   additional dependencies).
3. **Pure ReportLab** — generate the PDF programmatically using ReportLab
   Platypus, the same library used for the main sizing PDF.

## Decision

Implement `generate_concerns_pdf()` in a new pure-service module
`services/concerns_export.py` using ReportLab Platypus directly. The module
has zero UI imports and is callable from anywhere in the pipeline.

The PDF uses A4 format, Vera TTF fonts (French character support), and a
severity-colour-coded table layout with italic remediation hint text per
finding. A companion `generate_concerns_csv()` function in the same module
produces a UTF-8 BOM CSV for Excel compatibility.

## Rationale

- **Playwright path is complex:** The main sizing report PDF uses a
  serialize-in-report.py → print_session token → deserialize-in-report_print.py
  round-trip. Adding a second Playwright path for concerns would replicate this
  complexity.
- **Independence:** A pure service function is simpler to test (no browser
  needed), works offline, and runs synchronously without async plumbing.
- **Reuse of existing stack:** ReportLab and Vera fonts are already
  dependencies; no new packages required.
- **`concerns_export.py` as a pure service module:** Follows the established
  pattern of `health_checks.py` — zero UI imports, pure function interface,
  independently testable.

## Consequences

- **Positive:** `generate_concerns_pdf()` and `generate_concerns_csv()` are
  independently testable with 10 automated tests (no browser, no async).
- **Positive:** Export is available from any context — UI button, CLI, test
  suite — without NiceGUI running.
- **Positive:** PDF styling is consistent with the main report (same fonts,
  same colour palette).
- **Negative:** PDF layout is a programmatic approximation of the web UI;
  does not pixel-match the browser-rendered `/concerns` page.
- **Note:** The CSV export uses a UTF-8 BOM (`\xef\xbb\xbf`) header for
  Excel compatibility. This is intentional and tested (see
  `test_generate_concerns_csv_utf8_bom`).
