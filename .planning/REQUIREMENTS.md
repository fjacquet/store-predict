# Requirements: StorePredict

**Defined:** 2026-02-23
**Core Value:** Accurately predict real-world PowerStore DRR per workload, recommend optimal datastore layouts, flag environment risks, and right-size ESXi compute — all from a static export file with no live vCenter required — so pre-sales engineers can deliver honest, defensible sizing AND migration plans to customers.

## v5.0 Requirements — Multi-Cluster & Export Completeness

### Multi-Cluster Compute

- [x] **CLUS-01**: Tool parses Cluster column from RVTools vInfo tab and groups VMs by cluster
- [x] **CLUS-02**: `/compute` page shows per-cluster breakdown table (cluster name, VM count, vCPU/RAM totals, hosts needed per cluster)
- [x] **CLUS-03**: Per-cluster breakdown table includes a grand total row summing all clusters
- [x] **CLUS-04**: Health checks surface findings per cluster where applicable (e.g., HW version spread, HA host ratio per cluster)

### Health Findings Export

- [x] **HEXP-01**: PDF report includes a findings summary table (count by severity) on the main sizing page
- [x] **HEXP-02**: PDF report appends a dedicated findings detail page listing all findings with severity, category, and description
- [x] **HEXP-03**: Excel export includes a "Findings" worksheet with all health check results (finding, severity, category, detail)

### vMSC / DR Modeling

- [x] **VMSC-01**: vMSC mode allows engineer to configure VM split ratio between sites (not locked to 50/50)
- [x] **VMSC-02**: A/P DR mode allows engineer to configure what percentage of VMs run active on primary site
- [ ] **VMSC-03**: Compute page shows per-site host count for vMSC and A/P DR scenarios as separate rows

### Documentation

- [x] **DOCS-01**: Product Requirements Document (PRD) created — formal document covering tool scope, user personas, use cases, feature rationale, and non-functional requirements

## v6 Requirements (Deferred)

*(None yet — will accumulate as v5.0 is built)*

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time vCenter API integration | Tool works with exported files only — by design |
| Cluster-specific preset selection per cluster | Complexity; all clusters use same preset selection in v5.0 |
| Automatic cluster detection for LiveOptics | LiveOptics exports don't reliably include cluster metadata |
| Migration wave planning | High complexity; separate milestone topic |
| PowerStore model recommendation | Layout-only; model selection is a separate sales conversation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLUS-01 | Phase 23 | Complete |
| CLUS-02 | Phase 23 | Complete |
| CLUS-03 | Phase 23 | Complete |
| CLUS-04 | Phase 23 | Complete |
| HEXP-01 | Phase 24 | Complete |
| HEXP-02 | Phase 24 | Complete |
| HEXP-03 | Phase 24 | Complete |
| VMSC-01 | Phase 25 | Complete |
| VMSC-02 | Phase 25 | Complete |
| VMSC-03 | Phase 25 | Pending |
| DOCS-01 | Phase 26 | Complete |

**Coverage:**
- v5.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 after roadmap creation (Phases 23-26)*
