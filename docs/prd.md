# Product Requirements Document — StorePredict

**Version:** 4.0 (current as of 2026-02-22)
**Status:** Living document — updated after each milestone
**Owner:** Pre-Sales Engineering

---

## 1. Overview

### 1.1 Product Summary

StorePredict is a web-based pre-sales assessment platform for pre-sales engineers. It ingests static VMware workload exports (RVTools `.xlsx`, LiveOptics `.xlsx`/`.csv`/`.zip`) and produces a complete, defensible pre-sales sizing package without requiring live vCenter access.

The tool covers four analytical domains:

| Domain | Output |
|--------|--------|
| Storage sizing | Required capacity per workload with Data Reduction Ratios |
| Datastore layout | Optimal VMFS datastore placement across three strategies |
| Environment health | 11 checks surfacing data quality issues and VMware best practices violations |
| Compute sizing | ESXi host count for N+1 HA, vMSC, and A/P DR scenarios |

### 1.2 Problem Statement

Pre-sales engineers spend significant time manually sizing Dell storage for VMware environments. The process involves:

1. Exporting VM inventory from RVTools or LiveOptics
2. Manually categorizing each VM by workload type
3. Looking up DRR coefficients per category
4. Calculating required capacity per workload and totaling
5. Estimating ESXi host counts from vCPU/RAM totals
6. Checking for sizing risks and VMware anti-patterns
7. Formatting findings into a customer-facing report

This process is error-prone, time-consuming, and produces inconsistent results across engineers. StorePredict automates all seven steps from a single file upload.

### 1.3 Core Value

> Accurately predict real-world PowerStore DRR per workload, recommend optimal datastore layouts, flag environment risks, and right-size ESXi compute — all from a static export file with no live vCenter required — so pre-sales engineers can deliver honest, defensible sizing AND migration plans to customers.

---

## 2. User Personas

### 2.1 Primary: Pre-Sales Storage Engineer

**Who:** Dell storage pre-sales engineer or partner SE presenting PowerStore/PowerFlex/PowerVault proposals.

**Context:**
- Visits customer sites or works remotely with customer-provided exports
- Has no access to live vCenter
- Needs defensible numbers to put in proposals
- Presents to both technical architects and procurement stakeholders
- Works in French (primary) or English

**Goals:**
- Produce accurate capacity sizing in minutes, not hours
- Generate a customer-ready PDF without manual formatting
- Identify risks in the customer environment before the proposal is challenged
- Justify recommended ESXi host counts with formula-backed calculations

**Pain points:**
- Manual workload classification is tedious and inconsistent
- DRR lookups require opening multiple reference documents
- Datastore sizing rules (15-25 VMs, 4 TB) are applied inconsistently
- Computing N+1 HA hosts from raw vCPU/RAM requires spreadsheet work
- Health issues (old HW versions, HA misconfigurations) are discovered late

### 2.2 Secondary: Pre-Sales Solutions Architect

**Who:** Technical architect reviewing or co-authoring the pre-sales package.

**Context:**
- Reviews proposals before customer delivery
- Validates that sizing assumptions are defensible
- May override automated classifications for known workloads

**Goals:**
- Quickly validate that all VMs are correctly classified
- Override individual VM classifications where business context is known
- Review datastore layout strategy choices and adjust parameters
- Export findings for inclusion in broader proposal documents

---

## 3. User Journeys

### 3.1 Standard RVTools Sizing

1. Export vInfo tab from RVTools as `.xlsx`
2. Upload file on StorePredict home page
3. Review auto-classified VM grid; adjust workload types inline or via multi-select dialog
4. Navigate to `/report` to review capacity totals, workload breakdown, and performance summary
5. Navigate to `/layout` to select preferred datastore strategy (Consolidation / Performance / Uniform)
6. Navigate to `/concerns` to review health check findings
7. Navigate to `/compute` to review ESXi host count recommendations
8. Download one-page PDF and `.xlsx` export for customer delivery

### 3.2 LiveOptics Sizing with Performance Data

1. Export LiveOptics `.xlsx` (or `.zip` containing it)
2. Upload on home page — auto-detection parses VMs tab + VM Performance tab
3. Performance metrics (Peak IOPS, 8K Eq. IOPS, throughput) are extracted automatically
4. Review and classify VMs; performance data is pre-populated in the grid
5. PDF report includes performance sizing section (not shown for RVTools imports)
6. All remaining steps identical to RVTools journey

### 3.3 Multi-Platform Sizing (PowerFlex / PowerVault)

1. Upload any supported file
2. Select storage platform from the platform dropdown (PowerStore / PowerFlex / PowerVault)
3. PowerFlex applies a flat 2.0 DRR; PowerVault applies flat 1.0 — overriding per-workload DRRs
4. All calculations and PDF reflect the selected platform

### 3.4 AI-Assisted Classification

1. Set `LLM_ENABLED=true` in Docker environment
2. Upload file — rules-based classifier runs first
3. Enable the AI classification toggle on the upload page
4. Unknown Reducible VMs are sent in batches to the configured LLM (OpenAI / Anthropic / Ollama / OpenRouter)
5. LLM suggests keyword-based rule improvements logged to console
6. Results appear in the grid; engineer reviews and confirms

---

## 4. Feature Inventory

### 4.1 Ingestion

| Feature | Detail | Shipped |
|---------|--------|---------|
| RVTools `.xlsx` import | Parses `vInfo` tab; resolves column aliases for variant exports | v1.0 |
| LiveOptics `.xlsx` import | Parses `VMs` tab + `VM Performance` tab | v1.0 |
| LiveOptics `.csv` import | Same schema as `.xlsx` VMs tab | v1.0 |
| LiveOptics `.zip` import | Auto-extracts xlsx from zip archive before validation | v1.1 |
| Server-side file validation | Extension check + magic byte validation before processing | v1.0 |
| Template VM filtering | Templates excluded at orchestrator level, not in parsers | v1.0 |
| Canonical DataFrame schema | 9 columns: `vm_name`, `os_name`, `provisioned_mib`, `in_use_mib`, `datacenter`, `cluster`, `is_template`, `is_powered_on`, `source_format` | v1.0 |

### 4.2 Classification

| Feature | Detail | Shipped |
|---------|--------|---------|
| Rules-based classifier | 43 priority-ordered patterns, first-match-wins | v1.0 |
| Substring matching | `re.search()` without word boundaries (SAP excepted) | v1.0 |
| SAP word-boundary rule | `SAP-`, `SAP_` prefix patterns + word boundary | v1.0 |
| 28 workload categories | Loaded from `DRR.csv` at runtime | v1.0 |
| Application-level DRR variants | +14 entries: Oracle HCC/TDE, SQL TDE, DDVE, compressed | v2.1 |
| LLM classification fallback | litellm async circuit-breaker; disabled by default | v1.1 |
| Batch LLM classification | Prompt-level batching for reduced latency | v3.0 |
| AI toggle (per-session) | `ui.switch` enables/disables LLM per session | v2.2 |
| Rule suggestion feedback | LLM suggests ready-to-paste `ClassificationRule` snippets | v2.2 |

### 4.3 VM Review Grid

| Feature | Detail | Shipped |
|---------|--------|---------|
| AG Grid (Community edition) | `ui.aggrid`; editable inline workload dropdown | v1.0 |
| Multi-workload dialog | Awaitable `WorkloadDialog` for multi-workload assignment | v1.0 |
| Conservative multi-DRR | Lowest DRR across all selected workload types | v1.0 |
| Editable DRR column | Custom DRR override per VM | v1.0 |
| Stable row identity | `row_index` integer as `getRowId` — no duplicate corruption | v4.0 |
| Quick-filter search | Text filter across VM name/OS in the grid | v4.0 |
| Column visibility toggle | vCPU/RAM/IOPS columns hidden by default; user-toggleable | v4.0 |
| Bulk workload update | Update multiple selected VMs in one action | v1.0 |
| AI classification progress | Live "42 / 496 VMs" counter during LLM pass | v2.2 |

### 4.4 Calculation

| Feature | Detail | Shipped |
|---------|--------|---------|
| Per-workload DRR lookup | Weighted average: `total_provisioned / total_required` | v1.0 |
| DRR guard | `max(drr, 0.1)` clamp prevents division by zero | v1.0 |
| Totals and averages | Summary section with grand total required capacity | v1.0 |
| Performance sizing | Peak IOPS, 8K Eq. IOPS, throughput (LiveOptics only) | v1.0 |
| Multi-platform DRR override | PowerFlex=2.0, PowerVault=1.0 flat override | v2.0 |
| Workload-based IOPS defaults | Applied for RVTools imports lacking performance data | v3.0 |

### 4.5 Health Checks (`/concerns`)

| Feature | Detail | Shipped |
|---------|--------|---------|
| Health checks engine | Pure pipeline module; 11 checks, 3 categories | v4.0 |
| Data quality checks | Missing OS, zero storage/CPU/RAM, powered-off ratio | v4.0 |
| Sizing risk checks | Unknown VM inflation, IOPS budget | v4.0 |
| VMware best practice checks | HW version, cluster assignment, VMware Tools status | v4.0 |
| `/concerns` page | Severity-coded cards; recomputed fresh per visit | v4.0 |

### 4.6 Compute Sizing (`/compute`)

| Feature | Detail | Shipped |
|---------|--------|---------|
| N+1 HA sizing | Host count formula with configurable overcommit ratio | v4.0 |
| vMSC sizing | Per-site host count for stretched cluster | v4.0 |
| A/P DR sizing | Primary + secondary site host count | v4.0 |
| 17 PowerEdge presets | R760/R770/R860/R960/R7725/XE7745 from CSV | v4.0 |
| Custom preset row | Engineer-defined spec for unlisted servers | v4.0 |
| Reactive page | Results update immediately on preset/overcommit change | v4.0 |

### 4.7 Datastore Layout (`/layout`)

| Feature | Detail | Shipped |
|---------|--------|---------|
| Three strategies | Consolidation (density), Performance (isolation), Uniform (balance) | v3.0 |
| Multi-dimensional BFD engine | Normalized scoring heuristic; 1000 VMs in <2s | v3.0 |
| Mission-critical isolation | Phase 0 isolation pass for SAP HANA, Exchange, large DBs | v3.0 |
| Advanced settings panel | Growth margin, snapshot reserve, VMs/DS limit, IOPS budget | v3.0 |
| VM drill-down | Expandable datastore rows showing VM detail | v3.0 |
| IOPS.csv defaults | Configurable default IOPS per workload for RVTools imports | v3.0 |

### 4.8 Exports

| Feature | Detail | Shipped |
|---------|--------|---------|
| One-page PDF | ReportLab Platypus; sizing summary + performance + workload table | v1.0 |
| PDF page 2 — charts | ECharts-equivalent bar/pie + Sankey diagram | v1.1 |
| PDF branding | Dell partner logo + optional custom company logo (PNG transparency) | v1.1 |
| PDF layout page | Dedicated print page with always-expanded VM detail | v3.0 |
| Excel export | Multi-sheet `.xlsx`: Summary, Workload Breakdown, VM Detail, Layout | v1.1 |
| French character support | Vera TTF fonts in ReportLab | v1.0 |

### 4.9 Internationalization

| Feature | Detail | Shipped |
|---------|--------|---------|
| FR/EN toggle | Per-tab locale via `t()` wrapper reading `app.storage.tab['locale']` | v1.1 |
| 150+ translated strings | All UI labels, AG Grid locale pack, PDF labels | v1.1 |
| Tooltips on all controls | 50+ new FR/EN keys with tooltip bindings | v3.0 |
| Language switch | Full page reload via `ui.run_javascript('location.reload()')` | v1.1 |

### 4.10 Infrastructure

| Feature | Detail | Shipped |
|---------|--------|---------|
| Docker Compose | Single container, port 8080, in-memory state | v1.0 |
| `STORAGE_SECRET` from env | No hardcoded secrets | v1.0 |
| `HEALTHCHECK` directive | Port 8080 liveness check | v1.0 |
| GitHub Actions CI | ruff lint, mypy strict, pytest with Codecov | v1.0 |
| MkDocs on GitHub Pages | Material theme, Mermaid diagrams, ADR library | v1.0 |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Requirement | Target |
|-------------|--------|
| File parsing | < 5 seconds for a 10,000-VM RVTools export |
| Classification | < 2 seconds for 1,000 VMs (rules-based) |
| Layout engine | < 2 seconds for 1,000 VMs (BFD heuristic) |
| PDF generation | < 10 seconds |
| Page load | < 1 second for all pages after initial file load |

### 5.2 Accuracy

| Requirement | Detail |
|-------------|--------|
| DRR values | Loaded from editable CSV; engineers validate against Dell reference |
| Conservative bias | Multi-workload VMs use the lowest (most conservative) DRR |
| IOPS defaults | Loaded from configurable `IOPS.csv`; overridden by LiveOptics actuals |
| Compute formula | Industry-standard N+1 HA formula with configurable overcommit |

### 5.3 Security

| Requirement | Detail |
|-------------|--------|
| File validation | Extension check + magic byte check on every upload |
| Log sanitization | VM names and DataFrame contents never logged |
| Session isolation | All data scoped to `app.storage.tab`; no cross-user leakage |
| No persistent storage | All data in-memory; cleared on tab close |
| Secret management | `STORAGE_SECRET` from environment variable only |

### 5.4 Reliability

| Requirement | Detail |
|-------------|--------|
| LLM fallback safety | LLM disabled by default; enabled only via explicit env var + toggle |
| DRR guard | `max(drr, 0.1)` prevents zero-division on malformed data |
| No external dependencies | Tool works fully offline (LLM disabled) |

### 5.5 Maintainability

| Requirement | Detail |
|-------------|--------|
| Three-layer architecture | `pipeline/` → `services/` → `ui/`; no UI imports in pipeline |
| Test coverage | 439 tests, 86% backend coverage (v4.0) |
| Code quality | ruff lint + mypy strict enforced in CI |
| Reference data as CSV | DRR.csv, IOPS.csv, compute_presets.csv editable without code changes |
| ADR library | 63 decisions documented; next is ADR-064 |

---

## 6. Constraints

| Type | Constraint | Rationale |
|------|-----------|-----------|
| Language | Full Python (NiceGUI) | Single language, simpler deployment, no JS build step |
| Data processing | pandas + openpyxl | Standard Python data stack; no heavy ML dependencies |
| PDF | ReportLab Platypus + Vera fonts | Not WeasyPrint (200-400 MB Docker image overhead) |
| Deployment | Docker Compose, single container | Internal tool; no orchestration complexity needed |
| Grid | AG Grid Community edition | Enterprise edition not licensed; master-detail unavailable |
| Layout engine | Pure Python heuristics | No ILP/OR-Tools; BFD within 10-15% of optimal |
| i18n | python-i18n with YAML | Not Babel/gettext; simpler for 2 languages |
| LLM abstraction | litellm | Not LangChain (overkill for a single classification call) |
| File sources | Static exports only | No live vCenter API; no SIOKit binary format |

---

## 7. Out of Scope

| Feature | Reason |
|---------|--------|
| PowerStore model recommendation | Model selection is a separate sales conversation |
| SIOKit `.siokit` binary format | Xlsx/csv exports are the practical reality |
| Real-time vCenter data collection | Tool works with exported files only — by design |
| User authentication | Internal tool; single-user sessions are sufficient |
| Data persistence between sessions | In-memory per tab; no database |
| LLM as primary classifier | Rules remain primary; LLM is opt-in fallback only |
| ILP/OR-Tools for exact optimal placement | BFD heuristic is within 10-15% of optimal; no heavy dependency |
| vVol layout recommendations | VMFS is the practical reality for migration projects |
| Storage DRS/SIOC integration | Deprecated in vSphere 8.0 U3 |
| Mobile app | Web-first; internal tool usage on desktop |
| Real-time chat/collaboration | Not needed for internal pre-sales tool |
| Video posts | Not applicable |
| OAuth login | Email/password unnecessary; no auth by design |

---

## 8. Success Metrics

| Metric | Definition |
|--------|-----------|
| Classification accuracy | % of VMs classified to a non-Unknown category on real customer exports |
| Time to first PDF | Minutes from file upload to downloaded PDF |
| Engineer adoption | Number of engineers using the tool per month |
| Test coverage | Backend coverage percentage maintained above 85% |
| Build reliability | CI pass rate on main branch |

---

## 9. Milestone History

| Version | Name | Key Capabilities Added |
|---------|------|----------------------|
| v1.0 | MVP Sizing Tool | Ingestion, classification, VM review grid, PDF, CI/CD |
| v1.1 | i18n, Branding & Intelligence | FR/EN i18n, LiveOptics ZIP, Excel export, PDF branding, LLM fallback, UX polish, charts |
| v2.0 | Multi-Platform Storage | PowerStore / PowerFlex / PowerVault platform selection |
| v2.1 | DRR Variants | +14 DRR entries for encrypted/compressed scenarios |
| v2.2 | AI Observability | AI toggle, LLM progress counter, rule suggestions |
| v3.0 | Datastore Layout | BFD layout engine, 3 strategies, `/layout` page, IOPS defaults |
| v4.0 | VM Improvements & Compute Sizing | Stable row identity, grid UX, health checks engine, `/concerns` page, compute sizing, `/compute` page |

---

## 10. Planned: v5.0 — Multi-Cluster & Export Completeness

| Requirement | Description |
|-------------|-------------|
| CLUS-01–04 | Parse Cluster column; per-cluster compute breakdown + grand total; per-cluster health findings |
| HEXP-01–03 | PDF findings summary on page 1 + detail appendix; Excel Findings worksheet |
| VMSC-01–03 | Configurable vMSC split ratio; configurable A/P DR active %; per-site host count rows |
| DOCS-01 | This PRD (completed) |

---

*Last updated: 2026-02-23 after v4.0 milestone shipped and v5.0 started*
