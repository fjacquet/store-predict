# Requirements: StorePredict

**Defined:** 2026-03-26
**Core Value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required

## v8.0 Requirements

Requirements for v8.0 Reporting Fidelity milestone. Closes Issue #5 and improves classification coverage and PDF chart quality.

### DRR Fix

- [x] **DRR-01**: User sees separate rows in the web UI workload summary table when same-named workloads have different DRR values
- [x] **DRR-02**: User sees separate rows in the PDF workload breakdown section when same-named workloads have different DRR values
- [x] **DRR-03**: User sees separate rows in the Excel workload breakdown sheet when same-named workloads have different DRR values

### Classification

- [ ] **CLASSIF-01**: Backup/archive infrastructure VMs (Veeam, Commvault, Veritas, NetBackup agents) are classified instead of showing as Unknown Reducible
- [ ] **CLASSIF-02**: Monitoring/infrastructure VMs (Zabbix, Nagios, PRTG, SolarWinds, management hosts) are classified instead of Unknown Reducible
- [ ] **CLASSIF-03**: Common database VMs (MySQL, PostgreSQL, MongoDB, Redis, MariaDB) are classified instead of Unknown Reducible

### Report Quality

- [ ] **REPORT-01**: Sankey diagram in PDF renders at print quality (no pixelation at standard print resolution)
- [ ] **REPORT-02**: Sankey diagram nodes and edges have legible labels and correct colors

## Future Requirements

### UX
- Consider severity filtering on /concerns page (deferred — page currently scannable without it)

## Out of Scope

| Feature | Reason |
|---------|--------|
| PowerStore model recommendation | Layout-only scope |
| Real-time vCenter data | Static export file only |
| Custom concern thresholds | Default thresholds cover VMware best practices |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DRR-01 | Phase 29 | Complete |
| DRR-02 | Phase 29 | Complete |
| DRR-03 | Phase 29 | Complete |
| CLASSIF-01 | Phase 29 | Pending |
| CLASSIF-02 | Phase 29 | Pending |
| CLASSIF-03 | Phase 29 | Pending |
| REPORT-01 | Phase 29 | Pending |
| REPORT-02 | Phase 29 | Pending |

**Coverage:**
- v8.0 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 — traceability confirmed after roadmap creation*
