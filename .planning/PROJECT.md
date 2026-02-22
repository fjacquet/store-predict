# StorePredict

## What This Is

A web-based migration planning tool for pre-sales engineers. It analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv/.zip) to predict Data Reduction Ratios (DRR) on Dell storage platforms, classifies VMs by workload category, computes capacity requirements, and **generates optimal datastore layout recommendations** with three strategies (Consolidation, Performance, Uniform) — transforming raw VM data into an actionable migration plan.

## Core Value

Accurately predict real-world PowerStore DRR per workload and **recommend optimal datastore layouts** considering capacity, IOPS, workload segregation, snapshot granularity, and copy data management — so pre-sales engineers can deliver honest, defensible sizing AND migration plans to customers.

## Requirements

### Validated

- Import RVTools .xlsx files (vInfo tab) — v1.0
- Import LiveOptics .xlsx/.csv files (VMs tab + VM Performance) — v1.0
- Import LiveOptics .zip archives (auto-extract xlsx) — v1.1
- Auto-classify VMs by workload category using 43 rules-based patterns — v1.0
- DRR lookup table with 28 workload categories from DRR.csv — v1.0
- Editable AG Grid table with inline workload dropdown and bulk update — v1.0
- Multi-select workload types with conservative (lowest) DRR — v1.0
- Editable DRR column for custom overrides — v1.0
- Calculate required PowerStore capacity with Totals/Averages sections — v1.0
- LiveOptics performance sizing: Peak IOPS, 8K Eq. IOPS, throughput — v1.0
- One-page PDF report with VM statistics, performance summary, workload breakdown — v1.0
- Docker Compose deployment with health check and env-var secrets — v1.0
- MkDocs documentation with GitHub Actions deployment — v1.0
- GitHub Actions CI (ruff, mypy, pytest) with Codecov coverage — v1.0
- 246 tests passing, file validation, log sanitization — v2.2
- i18n framework with FR/EN toggle — v1.1
- PDF branding with Dell + custom company logo — v1.1
- Excel export (.xlsx multi-sheet workbook) — v1.1
- LLM classification fallback (litellm, disabled by default) — v1.1
- UX polish: spinners, error toasts, button guards, no-data cards — v1.1
- Data visualizations: ECharts web charts + ReportLab/matplotlib PDF charts — v1.1
- Multi-platform storage model selection (PowerStore/PowerFlex/PowerVault) — v2.0
- Application-level DRR variants (encrypted, compressed, DDVE) — v2.1
- AI classification UI toggle + LLM progress counter + rule suggestions in logs — v2.2
- Datastore layout recommendation engine — 3 strategies (Consolidation, Performance, Uniform) with BFD placement — v3.0
- Dedicated /layout page with comparison table, expandable datastore tables, and VM drill-down — v3.0
- Advanced settings panel (growth margin, snapshot reserve, VMs/DS limit, IOPS budget) with reactive regeneration — v3.0
- Layout summary in PDF (dedicated print page) and Excel exports (layout sheet with VM detail) — v3.0
- Default IOPS estimates from configurable CSV for RVTools imports — v3.0
- Full i18n with tooltips on all UI controls — v3.0
- Batch LLM classification for reduced latency on unknown VMs — v3.0

### Active

<!-- v4.0 VM Improvements & Compute Sizing -->
- [ ] Improve classification rules to reduce Unknown VMs (OS-based fallbacks, new patterns)
- [ ] Grid UX: filtering by workload, column visibility, grouping, search, better bulk actions
- [ ] Per-VM IOPS data from LiveOptics shown in the VM grid
- [ ] Concerns/Health Check page: data quality flags, layout/sizing risks, VMware best practice violations
- [ ] Compute Sizing page: extract vCPU+RAM from RVTools, recommend host count, stretch cluster (vMSC + Active/Passive) toggles

### Out of Scope

| Feature | Reason |
|---------|--------|
| PowerStore model recommendation | Layout-only; model selection is a separate conversation |
| SIOKit (.siokit) binary format | Focus on xlsx/csv exports |
| Real-time data collection | Tool works with exported files only |
| User authentication | Internal tool, single-user sessions |
| Data persistence between sessions | In-memory per tab by design |
| LLM as primary classifier | Rules remain primary, LLM is fallback only |
| Babel/gettext for i18n | Overkill for 2 languages; python-i18n with YAML is simpler |
| LangChain | Massive dependency, overkill for single classification call |
| WeasyPrint | Adds 200-400MB to Docker image |
| ILP/OR-Tools for exact optimal placement | Heuristic BFD is fast and within 10-15% of optimal; no heavy dependency needed |
| vVol layout recommendations | VMFS is the practical reality for migration projects |
| Storage DRS/SIOC integration | Deprecated in vSphere 8.0 U3 |

## Context

Shipped v3.0 with 353 tests passing, 86% backend coverage, 6,802 LOC Python.
Tech stack: NiceGUI, pandas, openpyxl, ReportLab, AG Grid, XlsxWriter, Pillow, litellm, matplotlib, python-i18n, Playwright.
Docker Compose deployment, MkDocs on GitHub Pages, GitHub Actions CI with Codecov.
Layout engine adds migration planning capability — tool now sizes AND recommends datastore layouts.

## Constraints

- **Tech stack:** NiceGUI + Tailwind CSS (full Python)
- **Data processing:** pandas + openpyxl
- **PDF generation:** ReportLab Platypus with Vera fonts
- **Deployment:** Docker Compose, single container, port 8080
- **Documentation:** MkDocs with Material theme + Mermaid diagrams
- **Code quality:** ruff + mypy strict + pytest (353 tests, 86% coverage)
- **CI/CD:** GitHub Actions (lint, test, docs deploy, Codecov)
- **Layout engine:** Pure Python heuristics (no external optimization libraries)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Python (NiceGUI) over React+FastAPI | Single language, simpler deployment, native Tailwind | Good |
| NiceGUI over Streamlit | More UI control, AG Grid integration, Tailwind support | Good |
| Rules-based classification first | 43 rules cover 100% of sample VMs, no ML training data needed | Good |
| Conservative DRR for multi-workload VMs | Pre-sales needs defensible numbers | Good |
| Docker Compose deployment | Simple, fits internal tool usage | Good |
| python-i18n with YAML over Babel/gettext | Simpler for 2 languages, YAML readable by non-devs | Good |
| litellm for LLM abstraction | Single API for OpenAI/Anthropic/Ollama/OpenRouter | Good |
| LLM disabled by default (LLM_ENABLED=false) | Safest default; opt-in reduces surprise costs | Good |
| ECharts for web charts (NiceGUI ui.echart) | Native NiceGUI support, interactive, no JS dependencies | Good |
| ReportLab + matplotlib for PDF charts | ReportLab for bar/pie, matplotlib for Sankey | Good |
| Multi-dimensional BFD for VM placement | Best tradeoff: fast, good packing quality, pure Python | Good |
| Three strategies not one | Different customers have different priorities; choice is the value | Good |
| VMFS focus (not vVol) | Practical reality for migration projects; vVol adoption is nascent | Good |
| 4 TB default datastore size | Dell best practice sweet spot; balances density, snapshots, management | Good |
| 15-25 VMs/datastore default | Dell recommendation; validated by queue depth and VMFS metadata analysis | Good |
| Playwright for layout PDF | Dedicated /layout/print route, always-expanded VM detail for print | Good |
| IOPS.csv as package data | Configurable defaults without code changes; CSV lives in src/data/ | Good |

## Current Milestone: v4.0 VM Improvements & Compute Sizing

**Goal:** Transform StorePredict from a storage-only sizing tool into a full pre-sales assessment platform by adding compute sizing, health checks, and deeper VM data quality.

**Target features:**
- Classification rule improvements (fewer Unknown VMs)
- Grid UX enhancements (filter, group, search, column visibility)
- Per-VM IOPS from LiveOptics in the grid
- Concerns/Health Check page (data quality, sizing risks, VMware best practices)
- Compute Sizing page (vCPU/RAM from RVTools, host recommendations, stretch cluster support)

---
*Last updated: 2026-02-22 after v4.0 milestone started*
