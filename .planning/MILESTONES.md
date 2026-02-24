# Milestones — StorePredict

## v1.0 — MVP Sizing Tool

**Shipped:** 2026-02-19
**Phases:** 1-7 (22 plans)
**Source:** 2,840 LOC (30 modules) + 2,097 LOC tests (145 passing)

### Key Accomplishments

1. Full ingestion pipeline — Parses RVTools .xlsx, LiveOptics .xlsx/.csv with auto-detection and column alias resolution
2. Rules-based classification engine — 29 priority-ordered rules, 0% unknown rate on 594 real VMs
3. Interactive review UI — AG Grid with inline editing, bulk workload update, filtered selection, editable DRR
4. One-page PDF sizing report — ReportLab with Totals/Averages/Performance sections, French character support
5. LiveOptics performance sizing — Peak IOPS, 8K equivalent IOPS, throughput metrics with correct normalization
6. Production-ready deployment — Docker Compose, GitHub Actions CI/CD, MkDocs documentation

### Known Gaps

- No milestone audit performed (UAT passed 9/10 tests, 1 skipped)
- Company name prefix stripping not fully implemented (classification still works via substring matching)

### Archives

- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

## v1.1 — i18n, Branding & Intelligence

**Shipped:** 2026-02-20
**Phases:** 8–13 (15 plans)
**Source:** 4,140 LOC Python + 227 tests passing

### Key Accomplishments

1. FR/EN internationalization — `t()` helper backed by YAML locale files; all 150+ strings, AG Grid locale pack, PDF labels fully localizable with per-tab locale persistence
2. LiveOptics ZIP upload — Auto-extracts LiveOptics xlsx from .zip archives before validation
3. Excel export — Styled multi-sheet .xlsx workbook (Summary, Workload Breakdown, VM Detail) with XlsxWriter
4. PDF branding — Dell partner logo + optional custom company logo with PNG transparency handling via Pillow
5. LLM classification fallback — litellm async circuit-breaker classifier for "Unknown Reducible" VMs; disabled by default, supports OpenAI/Anthropic/Ollama/OpenRouter
6. UX polish — Loading spinners, progress bars, error toasts, button guards, no-data cards across all pages
7. Data visualizations — ECharts interactive charts on report page + ReportLab/matplotlib charts on PDF page 2

### Archives

- [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)

## v2.x — Storage Models, DRR Variants, Observability

**Shipped:** 2026-02-20/21 (v2.0, v2.1, v2.2)
**Phases:** shipped outside GSD planning
**Source:** 246 tests passing, 84% backend coverage

### Key Accomplishments

1. Multi-platform storage model selection — PowerStore (full DRR), PowerFlex (flat 2.0), PowerVault (flat 1.0)
2. Application-level DRR variants — +14 DRR entries for encrypted/compressed scenarios (Oracle HCC/TDE, SQL TDE, DDVE)
3. AI classification UI toggle — per-session switch, greyed out when LLM_ENABLED=false
4. LLM progress counter — live "42 / 496 VMs" notification during AI classification
5. Rule suggestions in logs — ready-to-paste ClassificationRule snippets logged after LLM pass
6. CI/CD hardening — Codecov coverage badge (84%), JUnit test analytics, workflow deduplication, permissions

## v3.0 — Datastore Layout Recommendations

**Shipped:** 2026-02-21
**Phases:** 14-19 (10 plans)
**Source:** 6,802 LOC Python + 353 tests passing, 86% coverage

### Key Accomplishments

1. Layout engine — Multi-dimensional BFD with 3 strategies (Consolidation, Performance, Uniform), pure Python heuristics, 1000 VMs in <2s
2. Performance strategy — Mission-critical VM isolation (SAP HANA, Exchange, large DB), tier-based placement (Hot/Warm/Cold), anti-affinity rules
3. Interactive /layout page — Side-by-side comparison table, expandable datastore tables with VM drill-down, reactive advanced settings panel
4. PDF & Excel integration — Dedicated layout print page with always-expanded VM detail, Excel layout sheet with indented VM rows under datastores
5. Full i18n & tooltips — 50+ new FR/EN keys, tooltips on all UI controls, chart legends localized, Quasar slot templates i18n-aware
6. Batch LLM classification — Prompt-level batching for unknown VMs reduces latency; tech debt cleanup (orphaned keys, benchmark test)

### Archives

- [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md)
- [v3.0-REQUIREMENTS.md](milestones/v3.0-REQUIREMENTS.md)
- [v3.0-MILESTONE-AUDIT.md](milestones/v3.0-MILESTONE-AUDIT.md)

## v4.0 — VM Improvements & Compute Sizing

**Shipped:** 2026-02-22
**Phases:** 20-22 (6 plans)
**Source:** 8,166 LOC Python + 439 tests passing
**Git range:** 2106184..b972b8d (39 commits, 56 files changed, +10,838/−1,259 lines)

### Key Accomplishments

1. Stable row identity — Replaced AG Grid getRowId from vm_name to integer `row_index`, fixing silent row corruption on customer files with duplicate VM names (linked clones, templates)
2. Grid UX — Quick-filter search box + column visibility toggle panel; vCPU, RAM, and IOPS columns hidden by default and user-toggleable
3. Health checks engine — `health_checks.py` with 11 checks across 3 categories: data quality (missing OS, zero storage/CPU/RAM, powered-off ratio), sizing risks (Unknown VM inflation, IOPS budget), VMware best practices (HW version, cluster assignment, Tools status)
4. `/concerns` page — Dedicated page surfacing health findings in severity-coded cards, computed fresh from session state on every visit
5. Compute sizing pipeline — `compute_sizing.py` pure module with N+1 HA formula, vMSC per-site counts, A/P DR sizing; 17 Dell PowerEdge presets (R760/R770/R860/R960/R7725/XE7745) loaded from CSV
6. `/compute` reactive page — Preset selector, configurable overcommit ratio, vMSC/AP toggles; `_ComputeConfig(TypedDict)` fixes Pyright type safety

### Archives

- [v4.0-ROADMAP.md](milestones/v4.0-ROADMAP.md)
- [v4.0-REQUIREMENTS.md](milestones/v4.0-REQUIREMENTS.md)
- [v4.0-MILESTONE-AUDIT.md](milestones/v4.0-MILESTONE-AUDIT.md)

---

## v5.0 Multi-Cluster & Export Completeness (Shipped: 2026-02-23)

**Phases completed:** 4 phases, 8 plans, 5 tasks

**Key accomplishments:**
- (none recorded)

---


## v7.0 Save & Restore + Concerns (Shipped: 2026-02-24)

**Phases completed:** 2 phases, 4 plans, 7 tasks

**Key accomplishments:**
- (none recorded)

---

