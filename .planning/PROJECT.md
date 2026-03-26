# StorePredict

## What This Is

A web-based pre-sales assessment platform for pre-sales engineers. It analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv/.zip) to predict Data Reduction Ratios (DRR) on Dell storage platforms, classify VMs, compute capacity requirements, **generate optimal datastore layout recommendations**, **surface environment health concerns**, and **recommend ESXi host counts** — transforming raw VM exports into a complete, defensible pre-sales package.

## Core Value

Accurately predict real-world PowerStore DRR per workload, recommend optimal datastore layouts, flag environment risks, and right-size ESXi compute — all from a static export file with no live vCenter required — so pre-sales engineers can deliver honest, defensible sizing AND migration plans to customers.

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
- Data visualizations: ECharts web charts + ReportLab PDF charts — v1.1
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
- Stable AG Grid row identity via `row_index` integer (eliminates duplicate VM name corruption) — v4.0
- Quick-filter search + column visibility toggle (CPU/RAM/IOPS columns) in VM review grid — v4.0
- Health checks engine (11 checks: data quality, sizing risks, VMware best practices) + `/concerns` page — v4.0
- Compute sizing pipeline (N+1 HA, vMSC, A/P DR) + `/compute` reactive page with 17 Dell PowerEdge presets — v4.0
- Per-cluster compute breakdown table with grand total row on `/compute` — v5.0
- Health findings in PDF export (severity summary + detail appendix) and Excel (Findings worksheet with Cluster column) — v5.0
- Configurable vMSC split ratio (1–99%) and A/P DR active % with per-site Site A/B host count rows on `/compute` — v5.0
- CycloneDX SBOM generation and Sigstore attestation on GitHub release — v5.0
- PRD v5.0 formal product requirements document — v5.0
- Datacenter & cluster scope filtering — `/scope` page between upload and review, scope badge in headers, DC/cluster suffix on exported filenames — v6.0
- Improved workload classification: Windows 10/11 → VDI Linked Clone, Tanzu nodes, SharePoint abbreviations, Logstash/Kibana, EXCHG — v6.0
- Dual-source merge: upload RVTools + LiveOptics simultaneously, merge on VM name — v6.1
- Session save/restore: self-contained .zip archive with session.json snapshot — v7.0
- Concerns remediation hints: actionable hint per health finding in /concerns — v7.0
- Standalone /concerns export as PDF and CSV — v7.0
- Playwright + matplotlib removed; Plotly+kaleido for PDF charts; Docker image 0.6 GB (−77%) — v7.0.4
- Single comprehensive PDF: layout datastore detail merged into main report — v7.0.6
- Auto dark mode: OS prefers-color-scheme detection on first visit — v7.0.7
- DRR category split: separate rows per (category, drr) pair in web UI, PDF, Excel — v8.0
- Classification expanded: Veritas/NetBackup, Nagios/SolarWinds, Redis patterns added — v8.0
- PDF Sankey at 300 DPI with palette aligned to ECharts web UI — v8.0

### Active

(None — v8.0 complete, start fresh with `/gsd:new-milestone`)

### Out of Scope

| Feature | Reason |
|---------|--------|
| PowerStore model recommendation | Layout-only; model selection is a separate conversation |
| SIOKit (.siokit) binary format | Focus on xlsx/csv exports |
| Real-time data collection | Tool works with exported files only |
| User authentication | Internal tool, single-user sessions |
| Browser auto-save (localStorage) | File-based save is more explicit and portable; no server-side state |
| Named project library / server-side persistence | File-based approach is simpler; users manage files in their filesystem |
| Custom concern thresholds | Adds complexity; default thresholds cover standard VMware best practices |
| Severity filtering on /concerns | Current page is already scannable; filtering deferred to v8+ |
| LLM as primary classifier | Rules remain primary, LLM is fallback only |
| Babel/gettext for i18n | Overkill for 2 languages; python-i18n with YAML is simpler |
| LangChain | Massive dependency, overkill for single classification call |
| WeasyPrint | Adds 200-400MB to Docker image |
| ILP/OR-Tools for exact optimal placement | Heuristic BFD is fast and within 10-15% of optimal; no heavy dependency needed |
| vVol layout recommendations | VMFS is the practical reality for migration projects |
| Storage DRS/SIOC integration | Deprecated in vSphere 8.0 U3 |

## Context

Shipped v7.0 (2026-02-24) + v7.0.4–v7.0.7 polish (2026-02-25). Latest release: v7.0.7.
Tech stack: NiceGUI, pandas, openpyxl, ReportLab, AG Grid, XlsxWriter, Pillow, litellm, plotly, kaleido, python-i18n.
Docker Compose deployment (single container, 0.6 GB image), MkDocs on GitHub Pages, GitHub Actions CI with Codecov + CycloneDX SBOM.
552 tests, 88% backend coverage.
Tool covers storage sizing, datastore layout, health checks with remediation hints, compute sizing, full findings/concerns export, session save/restore, and auto dark mode — a complete pre-sales assessment platform.

## Constraints

- **Tech stack:** NiceGUI + Tailwind CSS (full Python)
- **Data processing:** pandas + openpyxl
- **PDF generation:** ReportLab Platypus with Vera fonts
- **Deployment:** Docker Compose, single container, port 8080
- **Documentation:** MkDocs with Material theme + Mermaid diagrams
- **Code quality:** ruff + mypy strict + pytest (552 tests, 88% coverage)
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
| ReportLab + Plotly/kaleido for PDF charts | ReportLab for bar/pie/table; Plotly+kaleido for Sankey (ADR-071: replaces matplotlib+Playwright) | Good |
| Multi-dimensional BFD for VM placement | Best tradeoff: fast, good packing quality, pure Python | Good |
| Three strategies not one | Different customers have different priorities; choice is the value | Good |
| VMFS focus (not vVol) | Practical reality for migration projects; vVol adoption is nascent | Good |
| 4 TB default datastore size | Dell best practice sweet spot; balances density, snapshots, management | Good |
| 15-25 VMs/datastore default | Dell recommendation; validated by queue depth and VMFS metadata analysis | Good |
| ~~Playwright for layout PDF~~ → ReportLab direct | Playwright+Chromium removed in v7.0.4 (ADR-071); ReportLab wired directly, −430 MB Docker | Superseded |
| IOPS.csv as package data | Configurable defaults without code changes; CSV lives in src/data/ | Good |

## Key Decisions (v4.0 additions)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `row_index` as AG Grid row identity | vm_name fails on duplicates (linked clones); integer index is stable | Good |
| Health checks as pure pipeline module | Zero UI imports; testable in isolation; computed fresh per visit | Good |
| Compute presets from CSV | CPU landscape changes faster than code releases; engineers edit CSV directly | Good |
| TypedDict for NiceGUI session config | `dict[str, object]` too broad for Pyright; TypedDict coerces at read time | Good |
| A/P DR always computed (no `ap_enabled` param) | Tests rely on values always being present; UI controls display only | Good |

## Key Decisions (v5.0 additions)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `__no_cluster__` sentinel in compute groupby | Allows groupby without NaN/None; translated to i18n label in UI | Good |
| HealthFinding.cluster as str (not Optional) | Empty string avoids None guards; `if finding.cluster:` is idiomatic | Good |
| Serialize findings as list[dict] through print_session | Avoids re-running health checks in Playwright worker; PDF/UI consistency | Good |
| vmsc_site_a_hosts / vmsc_site_b_hosts replace vmsc_hosts_per_site | Enables asymmetric site display; symmetric case still works with equal values | Good |
| Split/active ratio as float [0.01, 0.99] / [0.01, 1.0] | Clamped to prevent degenerate single-site results; UI enforces 1–99/1–100 range | Good |
| CycloneDX SBOM via anchore/sbom-action + Sigstore attestation | Supply chain transparency; auto-attached to GitHub releases | Good |

## Key Decisions (v6.0 additions)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| /scope page between upload and review | Scope selection is a distinct step; filters propagate to all downstream pages | Good |
| Unselected VMs preserved in session | Re-scoping never requires re-upload; filtered VMs stay in memory | Good |

## Key Decisions (v7.0 additions)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| File-based session persistence (.zip) over localStorage/server-side | Portable, human-inspectable, no server state | Good |
| SESSION_ZIP_SENTINEL = "session.json" to detect session archives | Robust structural check; LiveOptics zips never contain session.json | Good |
| Session zip detection before LiveOptics zip extraction | Prevents false positive extraction; existing LiveOptics path unchanged | Good |
| Remediation hints as hardcoded English (not i18n) | Pre-sales engineering audience; EN acceptable for technical hints | Good |
| concerns_export.py as pure service module (zero UI imports) | Same pattern as health_checks.py; independently testable | Good |
| `or`-fallback in _load_constraints / _load_compute_config | Handles restored falsy values (0/"") that bypass dict.get defaults | Good |

## Key Decisions (v7.0.x polish additions)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Plotly+kaleido replaces matplotlib+Playwright | −430 MB Docker (no Chromium); kaleido renders Plotly to PNG natively for ReportLab | Good |
| `_build_ds_detail_pages()` merges layout detail into main PDF | Single PDF simpler for pre-sales; no standalone layout print page needed | Good |
| `ui.dark_mode().auto()` on first visit (ADR-072) | NiceGUI native API; respects OS `prefers-color-scheme`; stored preference still wins | Good |
| MkDocs nav collapsed to index pages | 82 individual nav entries removed; `adr/index.md` and `research/index.md` already have full tables | Good |

## Current Milestone: v8.0 Reporting Fidelity

**Goal:** Fix DRR category display, improve PDF chart quality, and reduce Unknown Reducible VMs through expanded classification patterns.

**Target features:**
- DRR category split in reports (no merging when DRR differs) — Issue #5
- Expanded classification patterns to reduce Unknown Reducible rate
- Print-quality PDF charts (Sankey/bar resolution, colors, labels)

---
*Last updated: 2026-03-26 after v8.0 Reporting Fidelity complete*
