# Changelog

All notable changes to StorePredict are documented here.

## [Unreleased]

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
