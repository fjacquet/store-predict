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

## v3.0 — Datastore Layout Recommendations (ACTIVE)

**Started:** 2026-02-21
**Phases:** 14-18 (7 plans)
**Goal:** Transform StorePredict from sizing tool into migration planning tool

### Planned Capabilities

1. Layout engine — 3 strategies (Consolidation, Performance, Uniform) using multi-dimensional bin packing
2. Dedicated /layout page — comparison table + per-datastore detail view with drill-down
3. Advanced settings — tunable placement parameters (DS size, VMs/DS, IOPS budget, reserves)
4. PDF/Excel integration — layout comparison in exports
5. Default IOPS estimates — workload-based fallback when no LiveOptics performance data
6. Full FR/EN localization for all new UI elements

---
