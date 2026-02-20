# Technical Research

Research documents produced during project development. Each document captures domain analysis, technology decisions, and findings from investigating sample data.

## Phase Research

| Phase | Topic | Key Findings |
|-------|-------|-------------|
| [Phase 1](phase-01-foundation.md) | Project Foundation | Python stack, NiceGUI, DRR.csv parsing quirks |
| [Phase 2](phase-02-ingestion.md) | File Ingestion | RVTools "MB" = MiB, Template NaN pitfall, column aliases |
| [Phase 3](phase-03-classification.md) | Workload Classification | 28 DRR categories, false positive patterns (ORA/SAP/EX), OS fallback strategy |
| [Phase 4](phase-04-ui.md) | UI Upload & Review Pages | AG Grid table, session storage split, multi-workload dialog, dark mode |
| [Phase 5](phase-05-calculation.md) | Calculation & PDF Report | ReportLab Platypus, Vera fonts, weighted avg DRR, BytesIO PDF |
| [Phase 6](phase-06-polish.md) | Polish, Docs & Deployment | Docker hardening, file validation, CI/CD, MkDocs, performance tests |
| [Phase 7](phase-07-ui-enhancements.md) | UI Enhancements | AG Grid advanced features, NiceGUI component patterns, session state |
| [Phase 8](phase-08-i18n.md) | i18n Foundation | python-i18n global locale, AG Grid FR locale CDN, ReportLab CID encoding |
| [Phase 8.1](phase-08.1-liveoptics-zip.md) | LiveOptics ZIP | ZIP bomb guard via central directory sum, tuple return pattern |
| [Phase 9](phase-09-excel-export.md) | Excel Export | XlsxWriter write-only, BytesIO seek(0), _i18n.t() vs t() wrapper |
| [Phase 10](phase-10-pdf-branding.md) | PDF Branding | Pillow mode normalization, Docker-safe Path resolution, base64 decode guard |
| [Phase 11](phase-11-llm-classification.md) | LLM Classification | litellm.acompletion() async, pydantic-settings SecretStr, circuit breaker pattern |
| [Phase 12](phase-12-ux-polish.md) | UX Polish | run.io_bound for spinner rendering, ui.notification in-place update, button disable/enable |

## Sample Data Analysis

- **RVTools sample:** 24 VMs, 70 columns in vInfo tab
- **LiveOptics sample:** 610 VMs, 38 columns in VMs tab
- **DRR reference:** 28 valid categories, semicolon-delimited CSV with parsing quirks

## Key Technical Findings

### RVTools "MB" values are MiB

Despite column headers saying "MB", RVTools uses base-2 (MiB) values. No unit conversion needed between RVTools and LiveOptics formats.

### VM Naming Conventions

Corporate VM names embed functional keywords: `CADSRVSQL001` (SQL), `CITADM-01` (Citrix), `CIGES-FAZ` (FortiAnalyzer). Classification relies on substring matching against these patterns.

### False Positive Patterns

- "ORA" matches LORADB (LoRa radio protocol database) — use "ORACLE" instead
- "SAP" matches GISAPP (GIS application server) — use word-boundary match
- "EX" matches EXTRANET — use "EXCHANGE" instead
- "ABAC" is Swiss Abacus ERP, not SAP ABAP

### v1.1 Findings

#### python-i18n Global State

`python-i18n` stores locale as process-global state. In a multi-tab NiceGUI app, switching locale in one tab affects all tabs. Solution: always call `i18n.set('locale', ...)` at the start of each request handler and store the user's locale choice in `app.storage.tab`.

#### run.io_bound for NiceGUI Spinner Rendering

NiceGUI's `ui.spinner` only renders when the event loop yields. Long synchronous operations (file parsing, PDF generation) must be wrapped in `await run.io_bound(fn, *args)` so the spinner actually appears during processing rather than only after completion.

#### litellm async Pattern

`litellm.acompletion()` is the async entry point for LLM calls. Use `asyncio.wait_for()` with a timeout to enforce circuit-breaker behaviour. Always set `SecretStr` via `pydantic-settings` so API keys are never logged or exposed in repr output.

#### ReportLab CID Font Encoding

ReportLab encodes text strings via CIDFont/FlateDecode, making them non-searchable as raw bytes in the PDF bytestream. Test locale-specific PDF content by comparing FR output bytes != EN output bytes rather than checking for string presence.

#### ZIP Bomb Guard

For LiveOptics ZIP ingestion, sum all `file.file_size` entries from the ZIP central directory before extracting. Reject any archive where the total uncompressed size exceeds the configured limit (default 512 MB). This prevents decompression bombs without requiring full extraction.
