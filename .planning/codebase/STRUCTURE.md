# Codebase Structure

**Analysis Date:** 2026-02-23

## Directory Layout

```
store-predict/
├── src/store_predict/              # Main package
│   ├── __init__.py                 # Package marker
│   ├── main.py                     # Application entry point
│   ├── config.py                   # Configuration and constants
│   ├── logging_config.py           # Logging setup (no customer data)
│   ├── pipeline/                   # Business logic layer (zero UI imports)
│   │   ├── __init__.py             # Public API exports
│   │   ├── models.py               # Core data types (FileFormat, VMRecord)
│   │   ├── errors.py               # IngestionError exception
│   │   ├── validation.py           # File upload validation (magic bytes)
│   │   ├── ingestion.py            # Format detection, dispatch to parsers
│   │   ├── parsers/                # Format-specific parsers
│   │   │   ├── __init__.py         # Public parse_* exports
│   │   │   ├── columns.py          # Canonical column mapping (VM Name, provisioned_mib)
│   │   │   ├── rvtools.py          # RVTools .xlsx parser (vInfo sheet)
│   │   │   └── liveoptics.py       # LiveOptics .xlsx/.csv parser (VMs sheet)
│   │   ├── classification.py       # Rules-based VM classification
│   │   ├── llm_classifier.py       # LLM-assisted classification for unmatched VMs
│   │   ├── calculation.py          # Required capacity calculation, summaries
│   │   ├── merger.py               # Merge multiple uploads
│   │   ├── zip_extraction.py       # Extract LiveOptics from .zip
│   │   ├── health_checks.py        # Validation of sizing results
│   │   ├── layout_models.py        # VMFS layout proposal data types
│   │   ├── layout_engine.py        # VMFS layout recommendation algorithm
│   │   └── compute_sizing.py       # Dell PowerEdge host sizing
│   ├── services/                   # Cross-cutting services (stateless utilities)
│   │   ├── __init__.py             # Public service exports
│   │   ├── drr_table.py            # DRR reference data loader, model override logic
│   │   ├── pdf_report.py           # ReportLab PDF generation (Platypus + Vera fonts)
│   │   ├── pdf_charts.py           # Chart rendering to ReportLab Flowables
│   │   ├── excel_report.py         # xlsxwriter Excel export
│   │   ├── charts.py               # eChart and Sankey configuration (JSON for echarts-js)
│   │   ├── playwright_pdf.py       # Playwright-based browser PDF capture
│   │   ├── print_session.py        # Session debug utility
│   │   ├── llm_config.py           # LLM (litellm) configuration and prompts
│   │   └── log_sanitization.py     # Filter sensitive keys from logs
│   ├── ui/                         # Presentation layer (NiceGUI pages and components)
│   │   ├── __init__.py
│   │   ├── state.py                # Session state helpers (save/load/clear)
│   │   ├── layout.py               # Shared page layout template (header, nav, toggles)
│   │   ├── pages/                  # UI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── upload.py           # File upload, ingestion, classification
│   │   │   ├── review.py           # VM table, workload edit, AG Grid
│   │   │   ├── scope.py            # Datacenter/cluster filtering
│   │   │   ├── report.py           # Calculation, charts, PDF/Excel download
│   │   │   ├── layout_page.py      # VMFS layout visualization
│   │   │   ├── compute.py          # PowerEdge host sizing calculator
│   │   │   ├── concerns.py         # Health check warnings page
│   │   │   └── report_print.py     # Print-optimized report view
│   │   └── components/             # Reusable UI widgets
│   │       ├── __init__.py
│   │       ├── vm_table.py         # AG Grid configuration
│   │       ├── workload_dialog.py  # Multi-workload selection dialog
│   │       ├── summary_stats.py    # KPI card display
│   │       ├── dark_mode_toggle.py # Theme switcher
│   │       ├── locale_toggle.py    # Language switcher (fr/en)
│   │       └── charts.py           # eChart component wrappers
│   ├── i18n/                       # Internationalization
│   │   ├── __init__.py             # t() translation wrapper
│   │   ├── locale.py               # get_locale() helper
│   │   └── locales/
│   │       ├── en.yaml             # English strings
│   │       └── fr.yaml             # French strings (primary)
│   ├── data/                       # Static reference data (CSV, images)
│   │   ├── DRR.csv                 # Data Reduction Ratio reference table
│   │   ├── compute_presets.csv     # Dell PowerEdge host presets
│   │   └── dell_logo.png           # Brand logo
│   └── __init__.py
├── tests/                          # Test suite (158+ tests)
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures and shared test utilities
│   ├── test_ingestion.py           # File format detection, parsing
│   ├── test_classification.py      # Rule matching
│   ├── test_classification_*.py    # Specific classification scenarios (prefix, SQL, etc.)
│   ├── test_calculation.py         # Required capacity math
│   ├── test_calculation_enhanced.py # Performance metrics
│   ├── test_merger.py              # Multi-file merging
│   ├── test_validation.py          # Magic byte validation
│   ├── test_drr_table.py           # DRR lookup and overrides
│   ├── test_pdf_report.py          # PDF generation
│   ├── test_pdf_enhanced.py        # PDF with performance data
│   ├── test_pdf_branding.py        # Logo handling
│   ├── test_excel_report.py        # Excel export
│   ├── test_zip_extraction.py      # LiveOptics .zip unpacking
│   ├── test_scope_filtering.py     # DC/cluster scope filtering
│   ├── test_layout_engine.py       # VMFS layout recommendations
│   ├── test_compute_sizing.py      # PowerEdge host sizing
│   ├── test_health_checks.py       # Validation constraints
│   ├── test_i18n.py                # Translation system
│   ├── test_log_sanitization.py    # Sensitive data filtering
│   ├── test_llm_classifier.py      # LLM classification fallback
│   ├── test_ux_polish.py           # UI/UX scenarios
│   ├── test_liveoptics_performance.py  # Performance column parsing
│   ├── test_report_print.py        # Print report page
│   ├── test_logo_ui_wiring.py      # Logo upload and display
│   └── test_performance.py         # Performance metrics, IOPS
├── docs/                           # MkDocs documentation
│   ├── index.md                    # Home page
│   ├── getting-started.md          # User guide
│   ├── architecture.md             # System overview
│   ├── prd.md                      # Product requirements
│   ├── adr/                        # Architecture Decision Records (65 ADRs)
│   │   ├── 001-nicegui-framework.md
│   │   ├── 002-drr-csv-reference.md
│   │   └── ... (065 total)
│   ├── research/                   # Phase research docs
│   │   ├── phase-01-foundation.md
│   │   ├── phase-02-ingestion.md
│   │   └── ... (phase docs)
│   └── changelog.md -> ../CHANGELOG.md (symlinked)
├── samples/                        # Sample data for testing
│   ├── DRR.csv                     # Reference DRR table
│   ├── rvtools_example.xlsx        # Sample RVTools export
│   └── liveoptics_example.xlsx     # Sample LiveOptics export
├── .github/workflows/              # GitHub Actions
│   ├── ci.yml                      # Lint, type check, test pipeline
│   └── docs.yml                    # MkDocs build and deploy to Pages
├── scripts/                        # Dev/build utilities
├── pyproject.toml                  # Project metadata, dependencies, tool config
├── docker-compose.yml              # Local dev container (single store-predict service)
├── Dockerfile                      # Multi-stage build, Alpine runtime
├── .dockerignore                   # Excludes .venv, .git, tests, docs
├── .env.example                    # Template for environment variables
├── .env                            # Local env (STORAGE_SECRET, LLM settings)
├── CLAUDE.md                       # Project instructions for Claude Code
├── CHANGELOG.md                    # Release notes
└── pyrightconfig.json              # Pyright type checking config
```

## Directory Purposes

**src/store_predict/:**
- Purpose: Main package code (production + test dependencies imported here)
- Contains: All business logic, UI, services
- Key files: `main.py` (entry), `config.py` (constants)

**src/store_predict/pipeline/:**
- Purpose: Pure business logic for ingestion, classification, calculation
- Contains: File parsers, classification rules, capacity math
- Characteristic: Zero UI imports (testable in isolation)

**src/store_predict/pipeline/parsers/:**
- Purpose: Format-specific file parsing (RVTools xlsx, LiveOptics xlsx/csv)
- Contains: Parser functions, column mapping logic
- Pattern: `parse_rvtools()`, `parse_liveoptics_xlsx()`, `parse_liveoptics_csv()` all return list of VMRecord

**src/store_predict/services/:**
- Purpose: Stateless utilities for cross-cutting concerns
- Contains: PDF/Excel generation, charting, DRR lookup, LLM config
- Characteristic: Depend on pipeline models; zero UI imports

**src/store_predict/ui/:**
- Purpose: User-facing pages and components
- Contains: NiceGUI routes, session state management, UI components
- Characteristic: Imports pipeline and services; uses `app.storage.tab` for per-tab isolation

**src/store_predict/ui/pages/:**
- Purpose: Individual page handlers (each is a route)
- Characteristic: Side-effect registration via `@ui.page()` at module level (imported by `main.py`)
- Files: One per major feature (upload, review, report, etc.)

**src/store_predict/ui/components/:**
- Purpose: Reusable UI building blocks
- Contains: AG Grid configuration, dialogs, charts, toggles
- Pattern: Composition via context managers and helper functions

**src/store_predict/i18n/:**
- Purpose: Translation system
- Contains: `t()` wrapper, locale getter, YAML locale files
- Pattern: `t()` reads locale from `app.storage.tab` on every call (tab-scoped, not global)

**src/store_predict/data/:**
- Purpose: Static reference data and assets
- Contains: DRR.csv, compute_presets.csv, dell_logo.png
- Build: Copied into package via `[tool.setuptools.package-data]` in pyproject.toml

**tests/:**
- Purpose: Test suite (pytest)
- Characteristic: 158+ tests across ingestion, classification, calculation, PDF, i18n, validation, performance
- Fixtures: `conftest.py` provides sample data, DRR table, DataFrame factories

**docs/:**
- Purpose: User and developer documentation
- Contains: MkDocs with Material theme, 65 ADRs, phase research docs
- Build: GitHub Actions deploy to GitHub Pages on push to main

## Key File Locations

**Entry Points:**
- `src/store_predict/main.py`: Application startup, logging setup, route registration
- `src/store_predict/ui/pages/upload.py`: File upload and ingestion entry point

**Configuration:**
- `src/store_predict/config.py`: Paths, constants (APP_PORT, DEFAULT_DRR, StorageModel enum)
- `pyproject.toml`: Dependencies, tool settings (ruff, mypy, pytest)
- `.env`: Runtime environment variables (STORAGE_SECRET, LLM_API_KEY, etc.)
- `pyrightconfig.json`: Pyright type checking configuration

**Core Logic:**
- `src/store_predict/pipeline/ingestion.py`: Format detection and file parsing dispatcher
- `src/store_predict/pipeline/classification.py`: Rules-based VM classification
- `src/store_predict/pipeline/calculation.py`: Required capacity math and summaries
- `src/store_predict/services/drr_table.py`: DRR reference data and model overrides

**Testing:**
- `tests/conftest.py`: Shared fixtures (sample DRR, DataFrames, parsed data)
- `tests/test_ingestion.py`: Parser tests (RVTools, LiveOptics formats)
- `tests/test_classification.py`: Classification rule matching
- `tests/test_calculation.py`: Required capacity calculations

**Reporting:**
- `src/store_predict/services/pdf_report.py`: ReportLab PDF generation
- `src/store_predict/services/excel_report.py`: xlsxwriter Excel export
- `src/store_predict/services/charts.py`: eChart/Sankey JSON configuration

## Naming Conventions

**Files:**
- **Pages:** `{feature}.py` in `ui/pages/` (e.g., `upload.py`, `review.py`, `report.py`)
- **Components:** `{widget_name}.py` in `ui/components/` (e.g., `vm_table.py`, `dark_mode_toggle.py`)
- **Parsers:** `{format}.py` in `pipeline/parsers/` (e.g., `rvtools.py`, `liveoptics.py`)
- **Tests:** `test_{module}.py` in `tests/` (e.g., `test_ingestion.py`, `test_classification.py`)
- **Services:** `{service_name}.py` in `services/` (e.g., `pdf_report.py`, `drr_table.py`)

**Directories:**
- **Feature modules:** Singular noun (e.g., `pipeline`, `services`, `ui`)
- **Sub-packages:** Plural noun for collections (e.g., `parsers`, `pages`, `components`, `locales`)

**Functions:**
- **Pipeline (pure):** Verb phrase (e.g., `detect_format()`, `ingest_file()`, `classify_dataframe()`, `calculate()`)
- **UI handlers:** Async verb phrase (e.g., `async def upload_page()`, `async def handle_upload()`)
- **Service utilities:** Verb phrase (e.g., `generate_report_pdf()`, `validate_logo()`, `apply_storage_model()`)
- **Private helpers:** `_snake_case()` (underscore prefix)

**Variables:**
- **camelCase:** Not used; always snake_case
- **Constants:** SCREAMING_SNAKE_CASE (e.g., `MAX_FILE_SIZE`, `DEFAULT_DRR`, `XLSX_MAGIC`)
- **Boolean flags:** `is_*` or `has_*` prefix (e.g., `is_powered_on`, `has_performance_data`)
- **Loop iterables:** Avoid shadowing `t` (translation function); use `wt` for workload type

**Types:**
- **Enums:** PascalCase (e.g., `FileFormat`, `StorageModel`)
- **Dataclasses:** PascalCase (e.g., `VMRecord`, `CalculationSummary`, `ClassificationRule`)
- **TypedDict:** PascalCase suffix `Config` or `Options` (e.g., `SessionConfig`)

## Where to Add New Code

**New Feature (multi-page workflow):**
- **Primary code:** `src/store_predict/ui/pages/{feature}.py` (async page handler)
- **Supporting components:** `src/store_predict/ui/components/{widget}.py` (reusable parts)
- **Business logic:** `src/store_predict/pipeline/{feature}.py` or new module
- **Tests:** `tests/test_{feature}.py`

**New Component/Widget:**
- **Implementation:** `src/store_predict/ui/components/{component_name}.py`
- **Usage:** Import and use in page handlers or other components
- **Tests:** `tests/test_{component_name}.py` (or inline in page tests)

**New Classification Rule:**
- **Implementation:** `src/store_predict/pipeline/classification.py` (add to `RULES` list)
- **No separate file:** Rules are data-driven, not code-driven
- **Tests:** `tests/test_classification.py` or `tests/test_classification_{scenario}.py`

**New Report Format:**
- **Service:** `src/store_predict/services/{format}_report.py` (e.g., `json_report.py`)
- **UI entry:** Add download button to `src/store_predict/ui/pages/report.py`
- **Tests:** `tests/test_{format}_report.py`

**New Utility Function:**
- **Shared helpers:** `src/store_predict/services/{topic}.py` (e.g., `csv_export.py`, `api_client.py`)
- **Pipeline helpers:** `src/store_predict/pipeline/{topic}.py` if pure logic

**New Locale/Translation:**
- **Locale files:** `src/store_predict/i18n/locales/{locale}.yaml` (YAML key/value pairs)
- **Usage:** `t("namespace.key")` in any UI code (resolved at runtime via `app.storage.tab` locale)

## Special Directories

**src/store_predict/data/:**
- Purpose: Static reference data and brand assets
- Generated: No (manually curated CSVs and PNG)
- Committed: Yes
- Build inclusion: Declared in `pyproject.toml` `[tool.setuptools.package-data]`

**tests/:**
- Purpose: Test suite
- Generated: No (tests are manual)
- Committed: Yes
- CI: Runs on push via `.github/workflows/ci.yml`

**docs/:**
- Purpose: User and developer documentation
- Generated: No (ADRs, phase docs, architecture are manual)
- Committed: Yes
- Deploy: GitHub Actions build and push to Pages on merge to main

**.nicegui/:**
- Purpose: NiceGUI runtime cache (compiled pages, static assets)
- Generated: Yes (auto-created on `ui.run()`)
- Committed: No (in `.gitignore`)

**.mypy_cache/, .ruff_cache/, .pytest_cache/:**
- Purpose: Tool cache directories
- Generated: Yes (auto-created by tools)
- Committed: No (in `.gitignore`)

**.venv/:**
- Purpose: Virtual environment (Python packages)
- Generated: Yes
- Committed: No
- Install: `uv pip install -e ".[dev]"` (uv creates/manages .venv automatically)

**site/:**
- Purpose: Built documentation (MkDocs HTML output)
- Generated: Yes (`mkdocs build`)
- Committed: No (built on CI for Pages deployment)

---

*Structure analysis: 2026-02-23*
