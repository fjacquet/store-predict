# StorePredict

## What This Is

A web-based tool for pre-sales engineers that analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv/.zip) to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays. It classifies VMs by workload category using rules-based patterns (with optional LLM fallback), applies DRR coefficients, parses LiveOptics performance data (IOPS, throughput), and generates a bilingual (FR/EN) PDF sizing report with capacity and performance metrics plus data visualization charts.

## Core Value

Accurately predict real-world PowerStore DRR per workload instead of relying on vendor marketing ratios, so pre-sales engineers can deliver honest, defensible sizing to customers.

## Requirements

### Validated

- Import RVTools .xlsx files (vInfo tab) — v1.0
- Import LiveOptics .xlsx/.csv files (VMs tab + VM Performance) — v1.0
- Import LiveOptics .zip archives (auto-extract xlsx) — v1.1
- Auto-classify VMs by workload category using 29 rules-based patterns — v1.0
- DRR lookup table with 28 workload categories from DRR.csv — v1.0
- Editable AG Grid table with inline workload dropdown and bulk update — v1.0
- Multi-select workload types with conservative (lowest) DRR — v1.0
- Editable DRR column for custom overrides — v1.0
- Calculate required PowerStore capacity with Totals/Averages sections — v1.0
- LiveOptics performance sizing: Peak IOPS, 8K Eq. IOPS, throughput — v1.0
- One-page PDF report with VM statistics, performance summary, workload breakdown — v1.0
- Docker Compose deployment with health check and env-var secrets — v1.0
- MkDocs documentation with GitHub Actions deployment — v1.0
- GitHub Actions CI (ruff, mypy, pytest) — v1.0
- 145 tests passing, file validation, log sanitization — v1.0
- ✓ i18n framework with FR/EN toggle — v1.1
- ✓ PDF branding with Dell + custom company logo — v1.1
- ✓ Excel export (.xlsx multi-sheet workbook) — v1.1
- ✓ LLM classification fallback (litellm, disabled by default) — v1.1
- ✓ UX polish: spinners, error toasts, button guards, no-data cards — v1.1
- ✓ Data visualizations: ECharts web charts + ReportLab/matplotlib PDF charts — v1.1

### Active

(None — planning next milestone)

### Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-page detailed PDF report | One-page synthesis sufficient for pre-sales |
| SIOKit (.siokit) binary format | Focus on xlsx/csv exports |
| PowerStore model recommendation | Capacity-only sizing, defer to v2 |
| Real-time data collection | Tool works with exported files only |
| User authentication | Internal tool, single-user sessions |
| Data persistence between sessions | In-memory per tab by design |
| LLM as primary classifier | Rules remain primary, LLM is fallback only |
| Babel/gettext for i18n | Overkill for 2 languages; python-i18n with YAML is simpler |
| LangChain | Massive dependency, overkill for single classification call |
| WeasyPrint | Adds 200-400MB to Docker image |
| Date/number locale formatting | Deferred to v2 |
| Third language support (DE, ES) | Deferred to v2 |

## Context

Shipped v1.1 with 4,140 LOC Python (35+ modules) + 227 tests passing.
Tech stack: NiceGUI 3.7.1, pandas, openpyxl, ReportLab, AG Grid 34.2.0, XlsxWriter, Pillow, litellm, matplotlib, python-i18n.
Docker Compose deployment, MkDocs on GitHub Pages, GitHub Actions CI.

## Constraints

- **Tech stack:** NiceGUI + Tailwind CSS (full Python)
- **Data processing:** pandas + openpyxl
- **PDF generation:** ReportLab Platypus with Vera fonts
- **Deployment:** Docker Compose, single container, port 8080
- **Documentation:** MkDocs with Material theme + Mermaid diagrams
- **Code quality:** ruff + mypy strict + pytest (227 tests)
- **CI/CD:** GitHub Actions (lint, test, docs deploy)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Python (NiceGUI) over React+FastAPI | Single language, simpler deployment, native Tailwind | ✓ Good |
| NiceGUI over Streamlit | More UI control, AG Grid integration, Tailwind support | ✓ Good |
| Rules-based classification first | 29 rules cover 100% of sample VMs, no ML training data needed | ✓ Good |
| Conservative DRR for multi-workload VMs | Pre-sales needs defensible numbers | ✓ Good |
| Docker Compose deployment | Simple, fits internal tool usage | ✓ Good |
| AG Grid with `:` prefix for JS functions | NiceGUI convention, required for getRowId/valueFormatter | ✓ Good |
| NaN → None (not empty string) | Prevents downstream float("") errors in JSON chain | ✓ Good |
| 8K IOPS = throughput/8 only | Avoids double-counting with avg_iops | ✓ Good |
| Hottest VM peak, not sum of peaks | Sum of peaks is statistically meaningless | ✓ Good |
| Editable DRR column | Pre-sales needs custom overrides for edge cases | ✓ Good |
| Totals/Averages report layout | Clearer grouping for pre-sales readability | ✓ Good |
| python-i18n with YAML over Babel/gettext | Simpler for 2 languages, YAML readable by non-devs | ✓ Good |
| Default locale = French | Primary user language per customer base | ✓ Good |
| t() sets global locale per call | Safe in NiceGUI single-threaded async | ✓ Good |
| litellm for LLM abstraction | Single API for OpenAI/Anthropic/Ollama/OpenRouter | ✓ Good |
| LLM disabled by default (LLM_ENABLED=false) | Safest default; opt-in reduces surprise costs | ✓ Good |
| `background_tasks.create()` for async upload | `asyncio.ensure_future` loses NiceGUI slot context after await | ✓ Good |
| ECharts for web charts (NiceGUI ui.echart) | Native NiceGUI support, interactive, no JS dependencies | ✓ Good |
| ReportLab + matplotlib for PDF charts | ReportLab for bar/pie, matplotlib for Sankey (no ReportLab equivalent) | ✓ Good |
| Sankey fallback to before/after bar | Sankey requires ≥2 workload groups; single-workload data fails gracefully | ✓ Good |
| Spacer not Image for empty PDF chart | Image(BytesIO(b"")) raises UnidentifiedImageError immediately | ✓ Good |

---
*Last updated: 2026-02-20 after v1.1 milestone*
