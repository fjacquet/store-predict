# Changelog

All notable changes to StorePredict are documented here.

## [Unreleased]

## [v4.0.1] - 2026-02-22

### Bug fixes

- **Fix all event handlers on `/compute`** — replaced `.on("update:model-value")` with
  `.on_value_change()`. Every control (preset selector, overcommit ratio, vMSC toggle,
  A/P toggle, spec inputs) was silently broken due to `GenericEventArguments` having no
  `.value` attribute; `ValueChangeEventArguments` does.
- **Ruff TC003** — moved `from pathlib import Path` into a `TYPE_CHECKING` block in
  `compute_sizing.py` (annotation-only use, safe with `from __future__ import annotations`).

### UX improvements

- **vCPU / RAM breakdown in N+1 card** — displays both sub-counts (e.g.
  "vCPU-based: 11 · RAM-based: 20") so users can see exactly which constraint binds
  and how the other count moves when adjusting the overcommit ratio.
- **Host spec inputs always visible** — cores/socket, sockets, and RAM are no longer
  hidden behind a "Custom" preset selection; all three inputs appear at all times.
- **Preset auto-populate** — selecting a named preset fills the spec fields from its
  base config; selecting "Custom" leaves the current field values untouched.
- **One preset per server model** — dropdown simplified from 16 spec-laden variants
  (e.g. "R760 (2x28c / 512 GiB)") to 7 clean model names: R760, R770, R860, R960,
  R7725, XE7745, Custom.
- **Remove duplicate heading** — "Configuration de l'hôte" was rendering twice in the
  settings panel; the redundant card label was removed.

## [v4.0.0] - 2026-02-22

Grid UX improvements, per-VM hardware data, and a new health check concerns page.

### Grid UX & VM Data (Phase 20)

- **Quick-filter search box** above the VM review grid — filters all visible columns
  instantly on each keystroke via AG Grid `quickFilterText`
- **Column visibility panel** — collapsible expansion above the grid with four
  checkboxes (vCPUs, RAM, Avg IOPS, Peak IOPS) toggling column visibility via
  `setColumnsVisible`; replaces AG Grid sidebar (Enterprise-only, unavailable in
  Community edition)
- **Hidden column definitions** added to the VM grid: `num_cpus`, `memory_mib`,
  `avg_iops`, `peak_iops` — hidden by default, revealed on demand
- **Stable row identity** — AG Grid `getRowId` switched from `vm_name` to
  `String(params.data.row_index)`, fixing row corruption for customer files with
  duplicate VM names (linked clones, template copies)
- `row_index` added to `CANONICAL_COLUMNS` and assigned as a contiguous integer
  in `ingest_file()` after template filtering
- Cell-change and bulk-update handlers updated to match rows by `row_index` (int)
  instead of `vm_name` string comparison

### Health Check & Concerns Page (Phase 21)

- **New `/concerns` page** — surfaces data quality flags, sizing risks, and VMware
  best practice violations derived from the current session without re-classifying
- **11 health checks** across three categories:
  - *Data Quality*: missing OS, zero provisioned storage, missing vCPU/RAM, high
    powered-off VM ratio (>30%)
  - *Sizing Risks*: high Unknown VM ratio (>25%), large Unknown VMs (>1 TiB),
    single VM exceeding 100K IOPS/datastore budget
  - *VMware Best Practices*: no cluster assignment, old HW version (<vHW17 /
    ESXi 7.0), very old HW version (<vHW14 / ESXi 6.7, Critical), VMware Tools
    not installed (Critical), VMware Tools not running
- Findings colour-coded by severity: Critical=red, Warning=yellow, Info=blue
- Powered-off VMs and templates excluded from best-practice checks
- `hw_version=0` sentinel guard: LiveOptics exports skip hardware-version checks
  rather than falsely flagging every VM as old hardware
- `hw_version` and `tools_status` added to `CANONICAL_COLUMNS`; RVTools parser
  reads them with graceful fallback (0 / "") when column absent
- LiveOptics parser sets sentinel values `hw_version=0`, `tools_status=""`
- Page uses `load_session_data()` — user edits from the Review grid are preserved;
  `HealthCheckResult` is never cached in session storage

### Compute Sizing Module & Page (Phase 22)

- **New `/compute` page** — reactive ESXi host count recommendations from the
  uploaded session data, with no re-ingestion; uses `load_session_data()` only
- **N+1 HA sizing** — recommended host count = `max(hosts_by_vcpu, hosts_by_ram) + 1`
  with configurable vCPU overcommit ratio (0.5–20.0, default 4.0)
- **vMSC (stretch cluster) mode** — toggle reveals per-datacenter host counts;
  shows a warning card when no datacenter column data is available in the export
- **Active/Passive DR mode** — toggle reveals primary site hosts and secondary
  site = `ceil(primary / 2)` (minimum 1)
- **17 Dell PowerEdge presets** loaded from `compute_presets.csv` (editable without
  code changes), covering:
  - R760 (Xeon 5th Gen: 28c, 32c, 48c variants)
  - R770 (Xeon 6 P-core: 6748P 48c, 6780P 64c, 6786P 86c)
  - R860/R960 (Xeon 5th Gen 4-socket: up to 56c/6 TiB)
  - R7725 (EPYC 9005 Turin: 9555 64c, 9655 96c, 9755 128c, 9955 192c Zen5c)
  - XE7745 AI server (EPYC 9005 Turin: 64c, 96c)
  - Custom (user-defined cores/socket, sockets, RAM)
- Preset selector, overcommit input, and mode toggles are session-scoped
  (`app.storage.tab`); result cards refresh reactively on every change
- Aggregate cards: active vCPU total, RAM total (GiB), excluded VM count
- `HostConfig`, `ComputeSizingResult` frozen dataclasses; zero UI imports in
  `pipeline/compute_sizing.py`
- `load_presets(path)` public function for loading alternate CSV files

### LLM Classifier Enhancement

- `vm_description` field (RVTools Annotation / LiveOptics Description) now included
  in LLM classifier prompts as an optional classification signal
- Description truncated to 200 chars, newlines stripped; only included when
  non-empty to keep token usage lean

### Tests

- 49 new health check tests covering all 11 check IDs, sentinel guards,
  powered-off/template exclusion, and affected_vms tuple contract
- 386 total tests passing

## [v3.2.0] - 2026-02-22

Annotation-based VM classification for healthcare and application workloads.

### Classifier

- Fix two-pass classification logic: OS-fallback rules (priority ≥ 900) are now
  skipped in pass 1 when an annotation (`vm_description`) is present, allowing
  pass 2 to match richer annotation content before falling back to OS heuristics
- Expand HealthCare/EMR-EHR rule with 25+ application keywords:
  - Radiology & imaging: PACS, INTELLISPACE, GLEAMER, AZMED, RAYVOLVE, TRAUMACAD
  - Hospital IS (French/Swiss & European ecosystem): OPALE, CARIATIDE, HANDYLIFE,
    POLYPOINT, MEDIDATA, DATABICS, PROCAMED, SEDIA, DGLAB, STERIGEST, WINSCRIBE,
    SYNLAB, EXOLIS, SCENARA, MIRTH, KODIP
  - Regex anchors: `\bRIS\b` (Radiology IS), `\bSIEMS\b`, `\bHESTIA\b`, `Bloc-?Op`
- Add `TOMCAT`, `FORTIWEB` to Web Servers rule
- Add `PRTG` to Logging/Analytics rule
- Add `APP VOLUMES` / `APPVOL` to VDI Profiles rule
- Add `ALFRESCO` to File Content Servers rule
- Add `FILEMAKER`, `CLARIS`, `SQLITE` to MySQL/NoSQL rule
- Word-boundary guards: SIEMS (avoids SIEMENS), HESTIA (avoids HestiaCP)

## [v3.0.0] - 2026-02-21

Datastore layout recommendations for PowerStore sizing.

### Layout Engine

- Three layout strategies: Consolidation (BFD bin-packing), Performance (mission-critical isolation + tier BFD), Uniform (LPT equal distribution)
- Multi-dimensional BFD algorithm respecting capacity, IOPS budget, and VM count constraints per datastore
- Default 4 TiB datastores, 25 VMs/DS, 100K IOPS/DS (all tunable via PlacementConstraints)
- Oversized VMs (>usable capacity) automatically placed in dedicated datastores
- `generate_all_proposals()` public API returning all 3 strategy proposals

### Default IOPS Estimates

- Workload-based IOPS estimates for RVTools imports (no LiveOptics performance data)
- 8 workload categories: Database/SQL (500), Oracle (800), SAP HANA (1000), VDI (30-50), generic VMs (50), File (100)
- Configurable via `src/store_predict/data/IOPS.csv` (semicolon-delimited, same pattern as DRR.csv)
- Hardcoded fallback when CSV is missing — tests remain independent

### Documentation

- ADR-059: Workload-based IOPS defaults for RVTools sizing
- Research page: Default IOPS domain knowledge (sources, conservative bias, peak vs average)
- Architecture docs updated with layout engine as 4th pipeline stage

### Tests

- 46+ layout engine tests covering BFD packing, 3 strategies, metrics, IOPS injection, CSV loading

## [v2.2.0] - 2026-02-21

Observability, developer experience, and project health improvements.

### LLM Classification Improvements

- Live progress counter in UI notification during AI classification: "AI classification: 42 / 496 VMs"
- `on_progress` callback added to `classify_unknown_vms_async` for UI integration
- Ready-to-paste `ClassificationRule(...)` snippets now logged to server logs after LLM pass, allowing operators to promote LLM findings to deterministic rules without restarting

### CI / GitHub

- GitHub Release v2.1.0 created (was missing — tag existed but Release page had not been generated)
- `ci.yml`: added `permissions: contents: read` (workflow security hardening)
- `ci.yml`: added `codecov/codecov-action@v5` upload step with `CODECOV_TOKEN`
- `ci.yml`: added `--cov-report=xml` to generate Codecov-compatible report
- Coverage measurement scoped to testable backend code (UI layer omitted — NiceGUI pages require a live server)
- Effective coverage: **84%** (up from misleading 51% that included untestable UI)

### README

- Added badges: CI, Docs, Release, Codecov coverage, Python version, Version
- Fixed stale "29 classification rules" → **43 rules**

### Tests

246 tests passing (unchanged); ruff and mypy clean.

## [v2.1.0] - 2026-02-20

Application-level DRR variants, DDVE support, and AI classification UI toggle.

### DRR Reference Table (+14 entries, 28 → 42 total)

New subcategories covering application-layer encryption and compression scenarios
where PowerStore's inline dedup/compression is partially or fully defeated:

- `Database / Oracle - HCC (App Compressed)` → DRR 2.5
- `Database / Oracle - TDE (Encrypted)` → DRR 1.5
- `Database / Oracle - HCC + TDE` → DRR 1.2
- `Database / Microsoft SQL - Page Compressed` → DRR 2.5
- `Database / Microsoft SQL - TDE (Encrypted)` → DRR 1.5
- `Database / Microsoft SQL - Page Compressed + TDE` → DRR 1.2
- `Database / MongoDB - Encrypted` → DRR 1.3
- `Database / PostgreSQL - Encrypted` → DRR 1.3
- `Database / My SQL / NoSQL - Encrypted` → DRR 1.3
- `Containers / Kubernetes - Encrypted PVs` → DRR 1.3
- `VM Replication / Commvault` → DRR 1.5
- `VM Replication / Veeam - Compressed + Dedup` → DRR 1.2
- `VM Replication / Commvault - Compressed + Dedup` → DRR 1.2
- `VM Replication / Data Domain Virtual Edition (DDVE)` → DRR 1.0 (already deduplicated — 1:1 at most)

### Classifier (+14 rules, priorities 88–97 and 293–297)

Pattern matching for encrypted/compressed VM naming conventions. Combined scenarios
(e.g. Oracle HCC + TDE) use regex lookaheads for AND matching. DDVE, Commvault, and
compressed Veeam/Commvault variants also added.

### AI Classification UI Toggle

Per-session `ui.switch` on the upload page to disable LLM classification without
server restart. Greyed out with hint when `LLM_ENABLED=false`. State persisted in
`app.storage.tab["llm_ui_enabled"]`.

### Documentation

- ADR-052: Flat DRR override for non-PowerStore storage models
- ADR-053: Application-level DRR degradation as CSV subcategory variants
- ADR-054: AI classification toggle is per-session, not a server restart
- Research phase 14: application-level data reduction findings with source references
- `architecture.md` updated: storage model section, DRR/rule counts, session state

### Tests

246 tests passing (up from 230); ruff and mypy clean.

## [v2.0.0] - 2026-02-20

Multi-platform storage model selection — **breaking UX change**: DRR values now depend on the selected target storage platform, not only on workload type.

### Target Storage Model Selector

- New `StorageModel` enum in `config.py`: `POWERSTORE` (full dedup+compression, per-workload DRR), `POWERFLEX` (compression only, flat 2.0), `POWERVAULT` (no reduction, flat 1.0)
- `apply_storage_model()` added to `services/drr_table.py` — overwrites per-VM DRR in session based on selected platform
- `get_storage_model()` / `set_storage_model()` added to `ui/state.py` for tab-scoped session persistence
- Review page now shows a `ui.toggle` selector (PowerStore / PowerFlex / PowerVault) above the summary stats; switching instantly recalculates all DRR values, refreshes the grid and stats
- Model is applied at page load so navigating back from the report preserves the selection
- Report page picks up overridden DRR values automatically — no changes required
- 6 i18n keys added (`storage_model.label`, `.powerstore`, `.powerflex`, `.powervault`) in both `en.yaml` and `fr.yaml`
- 3 new tests for `apply_storage_model()` (PowerVault→1.0, PowerFlex→2.0, PowerStore→table values); 230 tests passing, ruff and mypy clean

## [v1.1] - 2026-02-20

i18n, Branding & Intelligence milestone.

### Phase 13: Graphics (COMPLETE)

- `src/store_predict/services/charts.py` — four ECharts option-dict builders: `echart_sankey_options`, `echart_pie_options`, `echart_drr_bar_options`, `echart_before_after_options`; all use Dell blue `#007DB8` palette; Sankey falls back to grouped bar when fewer than 2 workload groups
- `src/store_predict/services/pdf_charts.py` — four ReportLab/matplotlib builders: `make_sankey_image_flowable` (lazy matplotlib import, `Spacer` guard for empty data), `make_pie_drawing`, `make_drr_bar_drawing`, `make_before_after_bar_drawing`
- `report.py` — `_build_charts_section()` added: Sankey full-width, pie + DRR bar in two-column grid, before/after bar full-width; only rendered when workload groups exist
- `pdf_report.py` — second PDF page added via `PageBreak()` + chart flowables; `on_later_pages` callback ensures Dell branded header on page 2
- `matplotlib>=3.8` confirmed in runtime dependencies; mypy overrides for `matplotlib.*` added
- 6 i18n keys added across `en.yaml` and `fr.yaml` (`pdf.charts_heading`, `pdf.sankey_title`, `pdf.pie_title`, `pdf.drr_bar_title`, `pdf.before_after_title`, `report.charts_heading`)
- 227 tests passing, ruff and mypy clean

### Phase 12: UX Polish (COMPLETE)

- Upload page refactored with spinner, linear progress bar, and `run.io_bound` pipeline offloading for a responsive event loop during 2-10 second processing
- Persistent LLM ui.notification (spinner=True, timeout=None) updated in-place to positive/negative outcome instead of fire-and-forget notify
- Review and report pages upgraded from plain links to card-with-CTA empty states (icon + label + button)
- PDF and Excel download buttons now disable during generation and re-enable via try/finally guard
- Company logo upload error message replaced with `t("error.logo_upload_failed")` i18n key
- Added 8 new i18n keys across en.yaml and fr.yaml (upload.processing, llm.error, error.unexpected, error.logo_upload_failed)
- Raw exception strings replaced with i18n messages across all user-facing error paths
- All `ui.notify()` type values audited to canonical NiceGUI types (positive/negative/warning/info)
- 20-test suite in test_ux_polish.py locking in UX patterns; full suite grows to 227 passed, 1 skipped

### Phase 11: LLM Classification Fallback (COMPLETE)

- LLMConfig pydantic-settings class reads 6 env vars (LLM_ENABLED/MODEL/API_KEY/API_BASE/TIMEOUT/MAX_CONCURRENT) with SecretStr masking for the API key
- `classify_unknown_vms_async` async function filters only "default" confidence VMs, runs bounded concurrency via asyncio.Semaphore, and logs only counts (never VM names)
- `classify_single_vm` applies input sanitization against prompt injection (truncate vm_name/os_name, strip newlines), asyncio timeout, and circuit breaker (3 failures -> 60s cooldown)
- LLM fallback wired into upload pipeline behind `llm_cfg.enabled` guard — feature is opt-in via `LLM_ENABLED=true` env var, never active in CI
- User notifications: persistent spinner before LLM pass, count notification after
- docker-compose.yml updated with `env_file` (required: false) and LLM_* env var stubs pointing to OpenRouter/Mistral defaults
- `.env.example` added and tracked in git as operator onboarding guide
- 7-test suite for config and classifier; pydantic-settings added to runtime dependencies

### Phase 10: PDF Branding (COMPLETE)

- Dell partner logo PNG bundled as package data and loaded at import time (Docker-safe path resolution)
- `_preprocess_logo()` normalizes any image mode (RGBA/RGB/P/JPEG) to RGBA PNG before ReportLab embedding, preventing black-background palette images
- `validate_logo()` validates PNG/JPEG by extension, magic bytes, file size, and image dimensions, raising IngestionError for user-facing messages
- `generate_report_pdf()` extended with backwards-compatible `dell_logo_bytes` and `company_logo_bytes` kwargs
- Company logo upload UI: `ui.upload` card on report page accepting .png/.jpg/.jpeg up to 200 KB with remove button
- Logo stored as base64 in `app.storage.tab` (tab-scoped session isolation) and decoded on PDF download
- `_on_download()` passes decoded `company_logo_bytes` to `generate_report_pdf()`, embedding customer logo in PDF header
- Pillow added to runtime dependencies; 16 branding tests + 11 logo UI wiring tests; 200 total tests

### Phase 9: Excel Export (COMPLETE)

- `generate_report_xlsx(summary, project_name, locale) -> bytes` pure function mirroring the PDF service shape (same locale param, same BytesIO pattern)
- Three styled sheets: Summary (label-value metrics), Workload Breakdown (category subtotals + totals row), VM Detail (per-VM row with optional performance columns)
- Brand blue (#1e3a5f) header row with white bold text, freeze panes at row 1, autofit columns on all sheets
- Alternate row colouring on body rows; performance columns/rows gated on `has_performance_data` flag
- 18 new `excel.*` i18n keys in both en.yaml and fr.yaml; EN and FR outputs verified to differ in bytes
- Green "Download Excel Report" button wired on report page between PDF and Back buttons
- `_on_download_excel` handler mirrors `_on_download`: assert summary type, generate bytes, sanitize filename, `ui.download`
- XlsxWriter mypy override added; 8-test suite validating magic bytes, locale switching, performance guard, and sheet count

### Phase 8.1: LiveOptics ZIP Extraction (COMPLETE)

- ZIP accepted as a fourth upload format alongside .xlsx and .csv
- `extract_liveoptics_from_zip(content: bytes) -> tuple[bytes, str]` module finds the LiveOptics xlsx member by case-insensitive regex pattern
- Zip bomb guard rejects archives whose total uncompressed bytes exceed 100 MB (central directory header check, no extraction needed)
- ZIP extraction runs before `validate_upload()` so extracted xlsx bytes go through existing validation logic unchanged
- `validation.py` extended to accept "zip" extension and PK magic bytes; upload accept prop updated to `.xlsx,.csv,.zip`
- 7-test suite with real in-memory zipfile objects covering happy path, pattern mismatch, no match, invalid zip, multiple members, and bomb guard
- Zero regressions; 165 tests passing after addition

### Phase 8: i18n Foundation (COMPLETE)

- `t()` translation helper backed by python-i18n YAML files with `%{variable_name}` placeholder syntax
- Tab-scoped `get_locale()` / `set_locale()` session helpers safe outside NiceGUI context (catches RuntimeError for pytest)
- English and French YAML locale files with 73 strings across 8 namespaces (layout, upload, review, report, stats, dialog, columns, pdf)
- `add_locale_toggle()` FR/EN toggle button triggering full page reload (required because `ui.header` cannot be in `@ui.refreshable`)
- French is the default locale per project convention; toggle label shows the switch-target language
- All 65 UI-layer strings in 8 files wrapped in `t()` calls; no hardcoded labels remain
- AG Grid configured with French CDN locale pack (`ag-grid-community/locale@32.2.2`) and `:localeText` JS binding, injected only when locale is 'fr'
- PDF localized: `generate_report_pdf()` accepts `locale` param; `_i18n.set('locale', locale)` called once before all t() calls
- 13-test i18n unit suite covering EN/FR lookup, placeholder substitution, get_locale() safety, and PDF locale correctness

## [v1.0] - 2026-02-19

MVP Sizing Tool milestone.

### Phase 7: UI Bug Fixes & Report Enhancements (COMPLETE)

- Fixed AG Grid "No Rows To Show" — NiceGUI requires `:` prefix for JS function properties
- Fixed NaN serialization chain: `NaN → None` (not empty string) for JSON compatibility
- NiceGUI auto-reload with `__mp_main__` guard for multiprocessing
- LiveOptics performance columns: Peak IOPS, 8K Eq. IOPS, Peak MB/s (conditional on data)
- 8K IOPS normalization fix: `throughput_KB/s / 8` (was double-counting with avg_iops)
- Editable DRR column for custom overrides (min 0.1)
- Bulk workload update: select multiple VMs via checkboxes, mass-assign workload category
- Workload dropdown popup (`cellEditorPopup: True`) for readable category labels
- Filtered select-all: header checkbox selects only visible (filtered) rows
- CPU/memory metrics: `num_cpus` and `memory_mib` in parsers, calculation, report, and PDF
- Report reorganized into Totals and Averages sections (web + PDF)
- Replaced misleading "Total Peak IOPS" with "Hottest VM Peak IOPS" (single VM max)
- WorkloadDialog fixed to accept plain strings (not dicts) for NiceGUI ui.select
- 145 tests passing, 1 skipped

### Phase 6: Polish, Docs & Deployment (COMPLETE)

- Docker hardening: `.dockerignore`, `HEALTHCHECK` directive, env-var `STORAGE_SECRET`
- Server-side file upload validation with magic-byte checks (XLSX zip header, CSV UTF-8)
- Logging configuration with sanitization guidance (never log DataFrame contents)
- Session isolation verification via `app.storage.tab` (tab-scoped)
- Performance benchmark tests: 5000 VM classification < 10s, PDF generation < 5s
- MkDocs documentation: architecture page with 3 Mermaid diagrams, getting-started guide
- Project README with Docker and local dev quickstart
- GitHub Actions CI: ruff check, ruff format, mypy, pytest on push/PR to main
- GitHub Actions docs: MkDocs deployment to GitHub Pages on push to main
- 15 new tests (validation + log sanitization + performance), 121 total tests passing

### Phase 5: Calculation & PDF Report (COMPLETE)

- Calculation service with per-VM required capacity (`provisioned_mib / drr`)
- Workload grouping with subtotals (VM count, provisioned, in-use, required per category)
- Weighted average DRR (`total_provisioned / total_required`, not simple average)
- Division-by-zero guard: `max(drr, 0.1)` prevents invalid calculations
- Missing field defaults via `.get()` for robustness with incomplete data
- PDF report generator using ReportLab Platypus with branded one-page layout
- Dark blue header bar with StorePredict branding
- Workload breakdown table in PDF (Category, VMs, Provisioned, Avg DRR, Required)
- Vera/VeraBd TTF fonts for French character support (accents, special chars)
- Storage formatting helper: MiB to GiB with TiB display for large values
- Report page at `/report` with summary cards and workload breakdown table
- PDF download button triggering browser download
- Navigation wiring: Review → Report button, Report link in nav bar
- 24 new tests (12 calculation + 12 PDF), 106 total tests passing

### Phase 4: UI — Upload & Review Pages (COMPLETE)

- Session state module for per-tab DataFrame serialization (`ui/state.py`)
- Upload page with file dropzone, project name input, pipeline integration
- AG Grid VM table component with inline workload dropdown (ADR-007)
- Multi-select workload dialog for assigning multiple workload types (ADR-009)
- Summary statistics cards (Total VMs, Provisioned, Avg DRR, Effective Capacity)
- Review page wiring all components: table, dialog, stats, DRR recalculation
- Dark mode toggle with persistent user preference via `app.storage.user` (ADR-008)
- Navigation header with Home, Upload, and Review links
- Cell change handler: inline workload dropdown updates DRR and stats
- Row click handler: multi-select dialog applies conservative (lowest) DRR
- Per-tab session isolation for upload data, per-user storage for preferences (ADR-008)

### Phase 3: Workload Classification Engine

- Classification engine with 29 priority-ordered rules covering all 28 DRR subcategories
- ClassificationRule dataclass with pattern matching on VM name and OS field
- RuleRegistry with first-match-wins evaluation and confidence tracking
- Substring matching (CADSRVSQL001 -> SQL) with false positive prevention
- OS-based fallback rules (Windows Server -> Virtual Machines)
- classify_dataframe() for bulk DataFrame classification
- 0% Unknown rate on 594 real LiveOptics VMs (target was <20%)
- 28 unit tests + 11 integration tests with real sample data

### Phase 2: File Ingestion Pipeline

- RVTools .xlsx parser (vInfo tab)
- LiveOptics .xlsx and .csv parsers (VMs tab)
- Format auto-detection based on sheet names and column headers
- Column alias resolution for name variations
- Template VM filtering
- Unified ingest_file() orchestrator
- 29 ingestion tests with real sample files

### Phase 1: Project Foundation & DRR Table

- Python project structure with src layout
- DRR table service loading 28 workload categories from CSV
- Data models (VM, FileFormat, WorkloadCategory)
- NiceGUI app skeleton with page routing
- ruff + mypy configuration
- pytest setup with 14 initial tests
- Dockerfile + docker-compose.yml
