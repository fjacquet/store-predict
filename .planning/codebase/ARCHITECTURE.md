# Architecture

**Analysis Date:** 2026-02-23

## Pattern Overview

**Overall:** Three-layer pipeline with clear separation between business logic (pipeline), UI presentation (NiceGUI pages), and cross-cutting services (reporting, classification).

**Key Characteristics:**
- Pure functional pipeline layer (zero UI imports)
- Stateless service layer for calculations, PDF/Excel generation, charts
- NiceGUI-based UI layer with per-tab session storage
- Async-first UI with background task processing for long operations
- Type-safe with strict mypy checking

## Layers

**Pipeline (Business Logic):**
- Purpose: Parse files, detect formats, classify VMs, calculate capacity requirements
- Location: `src/store_predict/pipeline/`
- Contains: Ingestion, classification rules, calculation, validation, error definitions
- Depends on: pandas, openpyxl for data processing; no UI dependencies
- Used by: Upload page handler, report generation, health checks
- Characteristics: Pure functions, returns typed dataclasses, raises `IngestionError` for user-facing failures

**Services (Cross-Cutting):**
- Purpose: Data reduction ratio lookup, PDF/Excel report generation, charting, DRR calculation
- Location: `src/store_predict/services/`
- Contains: pdf_report, excel_report, charts, drr_table, pdf_charts, llm_config, playwright_pdf
- Depends on: pipeline models, ReportLab, xlsxwriter, matplotlib, playwright
- Used by: Report page, PDF/Excel download endpoints, chart rendering
- Characteristics: Stateless utilities, return bytes or objects; handle resource-intensive operations

**UI (Presentation & State):**
- Purpose: User interaction, session state management, page routing
- Location: `src/store_predict/ui/`
- Contains: Pages (/upload, /review, /report, /layout, /compute, /scope, /concerns), components (vm_table, workload_dialog, charts), layout template
- Depends on: NiceGUI, pipeline, services, i18n
- Characteristics: Async handlers, NiceGUI routes (side effects at module import), per-tab session state via `app.storage.tab`

**Configuration & Localization:**
- Purpose: Centralized config, secrets, internationalization
- Location: `src/store_predict/config.py`, `src/store_predict/i18n/`
- Contains: Paths, enum variants (StorageModel), locale switching, translation lookup
- Dependencies: i18n library, YAML locale files

## Data Flow

**File Upload → Classification → Calculation → Report:**

1. **Upload Page** (`ui/pages/upload.py`)
   - User drops file(s)
   - `validate_upload()` checks extension and magic bytes
   - `detect_format()` identifies RVTools vs LiveOptics
   - `ingest_file()` parses into normalized VMRecord list
   - `classify_dataframe()` applies rules-based pattern matching
   - `classify_unknown_vms_async()` (optional) uses LLM for unmatched VMs
   - `save_session_data()` persists DataFrame to `app.storage.tab["vm_data"]` with row_index tracking

2. **Review Page** (`ui/pages/review.py`)
   - `load_filtered_session_data()` retrieves DataFrame, applies datacenter/cluster scope filter
   - AG Grid displays trimmed row payload (selected columns only)
   - User edits workload_category, workload_subcategory, drr
   - `save_filtered_rows()` merges edited rows back into full session DataFrame by row_index

3. **Report Page** (`ui/pages/report.py`)
   - `load_filtered_session_data()` retrieves and filters DataFrame
   - `calculate()` produces CalculationSummary (per-VM and workload group totals)
   - `run_health_checks()` validates sizing constraints
   - Charts rendered via eChart/Sankey services
   - PDF and Excel exports via service layer

4. **State Management**
   - **Session Scope:** Per-browser-tab via NiceGUI's `app.storage.tab` (not global, isolated)
   - **Data Keys:** vm_data (DataFrame as JSON records), project_name, selected_datacenters, selected_clusters, rule_suggestions, storage_model
   - **Filtering:** Scope selection (DC/cluster) filters vm_data on read; full data preserved for unscoped exports

**State Management:**
- Tab-scoped isolation via NiceGUI's `app.storage.tab` (not app.storage.general)
- DataFrame serialized as JSON records with NaN → None conversion
- Preserves full data in session; filtered views on demand via `load_filtered_session_data()`
- Row identity stable via row_index field (added during ingestion)
- DRR table cached in memory after first load (static reference data)

## Key Abstractions

**VMRecord:**
- Purpose: Normalized representation of a VM from any input format
- Examples: `pipeline/models.py` lines 19-30
- Pattern: Frozen dataclass with source_format enum; acts as pipeline input contract

**CalculationSummary:**
- Purpose: Per-VM required capacity, workload group subtotals, aggregate stats
- Examples: `pipeline/calculation.py` lines 50-72
- Pattern: Frozen dataclass with vm_calculations list and workload_groups breakdown; output contract for report generation

**ClassificationRule:**
- Purpose: Pattern-matching rule for VM-to-workload-category assignment
- Examples: `pipeline/classification.py` lines 57-66
- Pattern: Frozen dataclass with vm_name_patterns and os_patterns (compiled regex tuples); rules evaluated in priority order (first match wins)

**DRRTable:**
- Purpose: Load DRR reference data from CSV, provide ratio lookup and storage model overrides
- Location: `services/drr_table.py`
- Pattern: Singleton-like cached load via `DRRTable.from_csv()`; supports flat DRR overrides for PowerFlex/PowerVault

**LayoutProposal:**
- Purpose: VMFS datastore layout recommendation with per-datastore sizing
- Location: `pipeline/layout_models.py`
- Pattern: Typed dataclass output from layout engine; contains isolated_vms, shared_datastores, summary

## Entry Points

**Application Entry:**
- Location: `src/store_predict/main.py`
- Triggers: `python -m store_predict.main` or container ENTRYPOINT
- Responsibilities: Initialize logging, import UI pages (side-effect routing registration), start NiceGUI server on port 8080

**Page Routes (Side-Effect Registration):**
- Location: `ui/pages/*.py` (each module has `@ui.page()` decorator at top level)
- Triggers: Page module import by `main.py`
- Responsibilities: Each page registers its route and async handler
- Files: upload.py, review.py, report.py, layout_page.py, compute.py, scope.py, concerns.py, report_print.py

**Pipeline Entry (File Upload):**
- Location: `upload.py` → `handle_upload()` → `run_analysis()`
- Triggers: User clicks "Analyser" button
- Responsibilities: Validate → detect format → ingest → classify → save session

**Report Generation:**
- Location: `report.py` → `generate_report_pdf()` via `pdf_report.generate_report_pdf()`
- Triggers: User clicks "Download PDF"
- Responsibilities: Calculate summary → render charts → generate ReportLab PDF in-memory

## Error Handling

**Strategy:** Explicit `IngestionError` exceptions with user-facing message + developer details

**Patterns:**
- **Ingestion Layer:** `detect_format()`, `ingest_file()`, `validate_upload()` raise `IngestionError(message, details)` on failure
- **UI Handlers:** Upload page catches `IngestionError`, displays message via snackbar, logs details (never VM names)
- **Validation:** Server-side magic byte + extension checks before pipeline processing
- **JSON Schema:** Pydantic models (e.g., LLMConfig in `services/llm_config.py`) validate external inputs

## Cross-Cutting Concerns

**Logging:**
- Setup in `logging_config.py`
- CRITICAL: Never log DataFrame contents, VM names, IPs, or customer data
- Log only metadata: file counts, format types, error messages
- Sanitized logging in lifecycle hooks (`log_sanitization.py` filters sensitive keys)

**Validation:**
- File upload: Magic bytes + extension in `pipeline/validation.py`
- DRR data: CSV parsing with fallback to DEFAULT_DRR in `services/drr_table.py`
- Session data: Row index tracking for stable identity, NaN conversion for JSON serialization

**Authentication:**
- None (pre-sales engineer tool, not multi-tenant)
- Session isolation via tab-scoped NiceGUI storage

**Internationalization:**
- French (primary, fallback to English)
- Implemented via `t()` wrapper around python-i18n
- Locale stored in `app.storage.tab`, read on every call
- YAML locale files in `i18n/locales/{locale}.yaml`

---

*Architecture analysis: 2026-02-23*
