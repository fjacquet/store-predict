# Requirements: StorePredict v1.1

**Defined:** 2026-02-19
**Core Value:** Accurate, defensible PowerStore DRR sizing per workload — now internationalized and intelligence-enhanced

## v1.1 Requirements

Requirements for v1.1 milestone. Each maps to roadmap phases (continuing from Phase 8+).

### Internationalization (I18N)

- [x] **I18N-01**: All UI strings (labels, buttons, tooltips, notifications) served via `t()` helper from YAML locale files
- [x] **I18N-02**: FR/EN language toggle in header, persisted in `app.storage.tab['locale']`
- [x] **I18N-03**: AG Grid column headers and built-in text displayed in selected language
- [x] **I18N-04**: PDF report labels (headers, section titles, column names) rendered in selected language
- [x] **I18N-05**: Language switch updates all visible UI elements (implemented via full page reload — NiceGUI 1.5+ prohibits `ui.header` inside `@ui.refreshable`)

### PDF Branding (BRAND)

- [x] **BRAND-01**: Dell partner logo displayed in PDF report header (static asset shipped with app)
- [x] **BRAND-02**: User can upload a custom company logo (PNG/JPEG) via UI
- [x] **BRAND-03**: Uploaded logo embedded in PDF report alongside Dell logo
- [x] **BRAND-04**: Logo images validated (format, dimensions) and scaled to fit without breaking one-page layout
- [x] **BRAND-05**: PNG transparency handled correctly (no black background in PDF)

### Excel Export (XLSX)

- [x] **XLSX-01**: Download Excel button on report page exports .xlsx file
- [x] **XLSX-02**: Excel workbook contains Summary sheet with capacity/performance metrics
- [x] **XLSX-03**: Excel workbook contains Workload Breakdown sheet with per-category aggregations
- [x] **XLSX-04**: Excel workbook contains VM Detail sheet with all VMs, workloads, and DRR values
- [x] **XLSX-05**: Excel sheets have styled headers, auto-sized columns, and frozen header rows

### LLM Classification Fallback (LLM)

- [ ] **LLM-01**: VMs classified as "Unknown Reducible" by rules engine are sent to LLM for classification
- [x] **LLM-02**: LLM provider configurable via env vars (supports OpenAI, Anthropic, Ollama, OpenRouter via litellm)
- [x] **LLM-03**: LLM feature disabled by default (`LLM_ENABLED=false`), opt-in via configuration
- [x] **LLM-04**: LLM calls are async (non-blocking) with 30s timeout and circuit breaker
- [ ] **LLM-05**: Classification source indicator in AG Grid (rules / LLM / manual) for transparency
- [x] **LLM-06**: LLM responses validated against known DRR workload categories (reject hallucinated categories)
- [x] **LLM-07**: API keys managed via pydantic-settings with SecretStr (never logged or exposed in UI)

### UX Polish (UX)

- [ ] **UX-01**: Loading/progress indicators during file upload, LLM classification, and report generation
- [ ] **UX-02**: Meaningful error messages for upload failures, LLM errors, and export failures
- [ ] **UX-03**: Consistent notification pattern (success/warning/error) across all pages
- [ ] **UX-04**: Navigation flow improvements (clear next-step guidance after upload, after review)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced i18n

- **I18N-V2-01**: Date/number locale formatting (dd/mm/yyyy, comma decimals for FR)
- **I18N-V2-02**: Third language support (DE, ES, etc.)
- **I18N-V2-03**: User-contributed translation workflow

### Advanced LLM

- **LLM-V2-01**: LLM provider selection UI (dropdown instead of env vars)
- **LLM-V2-02**: LLM fine-tuning on historical classifications
- **LLM-V2-03**: Batch mode for 20-50 VMs per LLM request to reduce latency
- **LLM-V2-04**: Classification confidence score display

### Advanced Reporting

- **RPT-V2-01**: Multi-page detailed PDF report option
- **RPT-V2-02**: PowerStore model recommendation based on capacity/performance

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM as primary classifier | Rules engine covers 100% of sample data; LLM is fallback only |
| SIOKit binary format | Focus on xlsx/csv exports |
| Real-time data collection | Tool works with exported files only |
| User authentication | Internal tool, single-user sessions |
| Data persistence between sessions | In-memory per tab by design |
| Babel/gettext for i18n | Overkill for 2 languages; python-i18n with YAML is simpler |
| LangChain | Massive dependency, overkill for single classification call |
| WeasyPrint | Adds 200-400MB to Docker image |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| I18N-01 | Phase 8 | Complete |
| I18N-02 | Phase 8 | Complete |
| I18N-03 | Phase 8 | Complete |
| I18N-04 | Phase 8 | Complete |
| I18N-05 | Phase 8 | Complete |
| XLSX-01 | Phase 9 | Complete |
| XLSX-02 | Phase 9 | Complete |
| XLSX-03 | Phase 9 | Complete |
| XLSX-04 | Phase 9 | Complete |
| XLSX-05 | Phase 9 | Complete |
| BRAND-01 | Phase 10 | Complete |
| BRAND-02 | Phase 10 | Complete |
| BRAND-03 | Phase 10 | Complete |
| BRAND-04 | Phase 10 | Complete |
| BRAND-05 | Phase 10 | Complete |
| LLM-01 | Phase 11 | Pending |
| LLM-02 | Phase 11 | Complete |
| LLM-03 | Phase 11 | Complete |
| LLM-04 | Phase 11 | Complete |
| LLM-05 | Phase 11 | Pending |
| LLM-06 | Phase 11 | Complete |
| LLM-07 | Phase 11 | Complete |
| UX-01 | Phase 12 | Pending |
| UX-02 | Phase 12 | Pending |
| UX-03 | Phase 12 | Pending |
| UX-04 | Phase 12 | Pending |

**Coverage:**

- v1.1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after research synthesis*
