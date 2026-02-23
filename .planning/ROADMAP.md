# Roadmap — StorePredict

## Milestones

- ✅ **v1.0 MVP Sizing Tool** — Phases 1-7 (shipped 2026-02-19) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 i18n, Branding & Intelligence** — Phases 8-13 (shipped 2026-02-20) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v2.x Storage Models, DRR Variants, Observability** — shipped outside GSD (v2.0–v2.2, 2026-02-20/21)
- ✅ **v3.0 Datastore Layout Recommendations** — Phases 14-19 (shipped 2026-02-21) — [Archive](milestones/v3.0-ROADMAP.md)
- ✅ **v4.0 VM Improvements & Compute Sizing** — Phases 20-22 (shipped 2026-02-22) — [Archive](milestones/v4.0-ROADMAP.md)
- 🚧 **v5.0 Multi-Cluster & Export Completeness** — Phases 23-26 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-02-19</summary>

- [x] Phase 1: Project Foundation & DRR Table (2/2 plans)
- [x] Phase 2: File Ingestion Pipeline (2/2 plans)
- [x] Phase 3: Workload Classification Engine (2/2 plans)
- [x] Phase 4: UI — Upload & Review Pages (3/3 plans)
- [x] Phase 5: Calculation & PDF Report (3/3 plans)
- [x] Phase 6: Polish, Docs & Deployment (5/5 plans)
- [x] Phase 7: UI Bug Fixes & Report Enhancements (5/5 plans)

See [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.1 i18n, Branding & Intelligence (Phases 8-13) — SHIPPED 2026-02-20</summary>

- [x] Phase 8: i18n Foundation (3/3 plans) — completed 2026-02-20
- [x] Phase 8.1: LiveOptics ZIP extraction (1/1 plan) — completed 2026-02-20
- [x] Phase 9: Excel Export (2/2 plans) — completed 2026-02-20
- [x] Phase 10: PDF Branding (2/2 plans) — completed 2026-02-20
- [x] Phase 11: LLM Classification Fallback (2/2 plans) — completed 2026-02-20
- [x] Phase 12: UX Polish (2/2 plans) — completed 2026-02-20
- [x] Phase 13: Graphics / Data Visualizations (3/3 plans) — completed 2026-02-20

See [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v2.x Storage Models, DRR Variants, Observability — SHIPPED 2026-02-20/21</summary>

Shipped outside GSD planning:

- v2.0: Multi-platform storage model selection (PowerStore/PowerFlex/PowerVault)
- v2.1: Application-level DRR variants (+14 entries), DDVE, AI classification UI toggle
- v2.2: LLM progress counter, rule suggestions in logs, Codecov, CI lean, README badges

</details>

<details>
<summary>✅ v3.0 Datastore Layout Recommendations (Phases 14-19) — SHIPPED 2026-02-21</summary>

- [x] Phase 14: Layout Engine Core (2/2 plans) — completed 2026-02-21
- [x] Phase 15: Default IOPS & Research Docs (2/2 plans) — completed 2026-02-21
- [x] Phase 16: Layout Page UI (2/2 plans) — completed 2026-02-21
- [x] Phase 17: PDF & Excel Integration (1/1 plan) — completed 2026-02-21
- [x] Phase 18: i18n & Polish (1/1 plan) — completed 2026-02-21
- [x] Phase 19: Batch LLM Classification (2/2 plans) — completed 2026-02-21

See [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v4.0 VM Improvements & Compute Sizing (Phases 20-22) — SHIPPED 2026-02-22</summary>

- [x] Phase 20: Grid UX & VM Data Columns (2/2 plans) — completed 2026-02-22
- [x] Phase 21: Health Check Module & Concerns Page (2/2 plans) — completed 2026-02-22
- [x] Phase 22: Compute Sizing Module & Page (2/2 plans) — completed 2026-02-22

See [v4.0-ROADMAP.md](milestones/v4.0-ROADMAP.md) for full details.

</details>

### 🚧 v5.0 Multi-Cluster & Export Completeness (In Progress)

**Milestone Goal:** Add per-cluster compute breakdown, export health findings to PDF and Excel, and improve vMSC/DR modeling granularity.

- [ ] **Phase 23: Multi-Cluster Compute** - Parse cluster data and show per-cluster breakdown with health check context
- [ ] **Phase 24: Health Findings Export** - Surface health findings in PDF and Excel exports
- [ ] **Phase 25: vMSC & DR Modeling** - Make site split ratios configurable and show per-site host counts
- [ ] **Phase 26: Documentation** - PRD (already complete)

## Phase Details

### Phase 23: Multi-Cluster Compute
**Goal**: Engineers can see host count recommendations broken down per cluster, with health findings scoped to cluster where applicable
**Depends on**: Phase 22 (Compute Sizing Module)
**Requirements**: CLUS-01, CLUS-02, CLUS-03, CLUS-04
**Success Criteria** (what must be TRUE):
  1. Engineer uploads an RVTools file with a Cluster column and sees VMs grouped by cluster name on the compute page
  2. The /compute page displays a per-cluster table showing cluster name, VM count, vCPU total, RAM total, and hosts needed for each cluster
  3. The per-cluster table includes a grand total row that sums all clusters
  4. Health check findings that apply per-cluster (HW version spread, HA ratio) display the cluster name alongside the finding
**Plans**: 2 plans
Plans:
- [ ] 23-01-PLAN.md — Pipeline: ClusterSizingRow, compute_cluster_breakdown(), per-cluster health checks, i18n keys, tests
- [ ] 23-02-PLAN.md — UI: per-cluster breakdown table on /compute, cluster badge on /concerns finding cards

### Phase 24: Health Findings Export
**Goal**: Health check findings are included in both PDF and Excel exports so engineers can share environment concerns alongside sizing recommendations
**Depends on**: Phase 23
**Requirements**: HEXP-01, HEXP-02, HEXP-03
**Success Criteria** (what must be TRUE):
  1. The main PDF sizing page includes a findings summary table showing count of findings grouped by severity (Critical, Warning, Info)
  2. The PDF report includes a dedicated findings detail appendix page listing every finding with its severity, category, and description
  3. The Excel export includes a "Findings" worksheet containing all health check results with columns for finding, severity, category, and detail
**Plans**: TBD

### Phase 25: vMSC & DR Modeling
**Goal**: Engineers can configure site-specific VM distribution for stretched cluster and disaster recovery scenarios, and see per-site host counts on the compute page
**Depends on**: Phase 22 (Compute Sizing Module)
**Requirements**: VMSC-01, VMSC-02, VMSC-03
**Success Criteria** (what must be TRUE):
  1. In vMSC mode, engineer can set any VM split percentage between sites (e.g., 60/40) instead of the fixed 50/50
  2. In A/P DR mode, engineer can configure what percentage of VMs are active on the primary site
  3. The /compute page shows per-site host counts for vMSC and A/P DR as distinct labeled rows (Site A / Site B)
**Plans**: TBD

### Phase 26: Documentation
**Goal**: PRD exists as a formal reference document for the project
**Depends on**: Nothing (standalone documentation)
**Requirements**: DOCS-01
**Success Criteria** (what must be TRUE):
  1. A PRD document exists covering tool scope, user personas, use cases, feature rationale, and non-functional requirements
**Plans**: TBD

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-02-19 |
| 2. Ingestion | v1.0 | 2/2 | Complete | 2026-02-19 |
| 3. Classification | v1.0 | 2/2 | Complete | 2026-02-19 |
| 4. UI Upload & Review | v1.0 | 3/3 | Complete | 2026-02-19 |
| 5. Calculation & PDF | v1.0 | 3/3 | Complete | 2026-02-19 |
| 6. Polish & Deploy | v1.0 | 5/5 | Complete | 2026-02-19 |
| 7. UI Fixes & Report | v1.0 | 5/5 | Complete | 2026-02-19 |
| 8. i18n Foundation | v1.1 | 3/3 | Complete | 2026-02-20 |
| 8.1. LiveOptics ZIP | v1.1 | 1/1 | Complete | 2026-02-20 |
| 9. Excel Export | v1.1 | 2/2 | Complete | 2026-02-20 |
| 10. PDF Branding | v1.1 | 2/2 | Complete | 2026-02-20 |
| 11. LLM Classification | v1.1 | 2/2 | Complete | 2026-02-20 |
| 12. UX Polish | v1.1 | 2/2 | Complete | 2026-02-20 |
| 13. Graphics | v1.1 | 3/3 | Complete | 2026-02-20 |
| 14. Layout Engine Core | v3.0 | 2/2 | Complete | 2026-02-21 |
| 15. Default IOPS & Docs | v3.0 | 2/2 | Complete | 2026-02-21 |
| 16. Layout Page UI | v3.0 | 2/2 | Complete | 2026-02-21 |
| 17. PDF & Excel Integration | v3.0 | 1/1 | Complete | 2026-02-21 |
| 18. i18n & Polish | v3.0 | 1/1 | Complete | 2026-02-21 |
| 19. Batch LLM Classification | v3.0 | 2/2 | Complete | 2026-02-21 |
| 20. Grid UX & VM Data Columns | v4.0 | 2/2 | Complete | 2026-02-22 |
| 21. Health Check & Concerns | v4.0 | 2/2 | Complete | 2026-02-22 |
| 22. Compute Sizing | v4.0 | 2/2 | Complete | 2026-02-22 |
| 23. Multi-Cluster Compute | v5.0 | 0/2 | Planned | - |
| 24. Health Findings Export | v5.0 | 0/TBD | Not started | - |
| 25. vMSC & DR Modeling | v5.0 | 0/TBD | Not started | - |
| 26. Documentation | v5.0 | 0/TBD | Not started | - |
