# Changelog

All notable changes to StorePredict are documented here.

## [Unreleased]

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
