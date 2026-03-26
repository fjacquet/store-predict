# Roadmap: StorePredict

## Milestones

- ✅ **v1.0 MVP** — Phases 1–7 (shipped 2026-02-19)
- ✅ **v1.1 i18n, Branding & Intelligence** — Phases 8–13 (shipped 2026-02-20)
- ✅ **v2.x Storage Models, DRR Variants, Observability** — shipped outside GSD planning (2026-02-20/21)
- ✅ **v3.0 Datastore Layout** — Phases 14–19 (shipped 2026-02-21)
- ✅ **v4.0 VM Improvements & Compute Sizing** — Phases 20–22 (shipped 2026-02-22)
- ✅ **v5.0 Multi-Cluster & Export Completeness** — Phases 23–26 (shipped 2026-02-23)
- ✅ **v6.0/v6.1 Scope Filtering & Dual-Source Merge** — shipped outside GSD planning (2026-02-24)
- ✅ **v7.0 Save & Restore + Concerns** — Phases 27–28 (shipped 2026-02-24)
- 🚧 **v8.0 Reporting Fidelity** — Phase 29 (in progress)

## Phases

<details>
<summary>✅ v1.0 through v6.1 (Phases 1–26) — SHIPPED</summary>

Phases 1–26 covered MVP, i18n/branding, storage models, datastore layout,
VM improvements, compute sizing, multi-cluster export, scope filtering, and
dual-source merge. See MILESTONES.md and milestones/ archives for detail.

</details>

<details>
<summary>✅ v7.0 Save & Restore + Concerns (Phases 27–28) — SHIPPED 2026-02-24</summary>

- [x] **Phase 27: Session Save & Restore** — User can save and restore a full sizing session via a self-contained .zip file (completed 2026-02-24)
- [x] **Phase 28: Concerns Enrichment** — Each health finding displays a remediation hint; /concerns is exportable as standalone PDF and CSV (completed 2026-02-24)

Archive: `.planning/milestones/v7.0-ROADMAP.md`

</details>

### 🚧 v8.0 Reporting Fidelity (In Progress)

**Milestone Goal:** Fix DRR category display, expand VM classification coverage, and deliver print-quality PDF charts — so pre-sales reports are accurate and presentation-ready.

- [ ] **Phase 29: Reporting Fidelity** — All 8 requirements executed in parallel waves (DRR fix, classification expansion, PDF chart quality)

## Phase Details

### Phase 29: Reporting Fidelity
**Goal**: Deliver all v8.0 improvements in a single phase with parallel execution waves — DRR category split across all report surfaces, expanded classification patterns for common infrastructure VMs, and print-quality Sankey diagram in PDF
**Depends on**: Nothing (Phase 28 complete)
**Requirements**: DRR-01, DRR-02, DRR-03, CLASSIF-01, CLASSIF-02, CLASSIF-03, REPORT-01, REPORT-02

**Execution waves (parallel):**
- Wave A: DRR-01/02/03 — Fix groupby logic in calculation pipeline, propagate to PDF and Excel
- Wave B: CLASSIF-01/02/03 — Add backup, monitoring, and database classification patterns
- Wave C: REPORT-01/02 — Improve Plotly/kaleido rendering resolution and label legibility

**Success Criteria** (what must be TRUE):
  1. User uploads a file where the same workload category has VMs with different DRR values — separate rows appear in the web UI workload summary table, one per DRR value
  2. PDF workload breakdown shows separate rows — no merging of rows that differ in DRR
  3. Excel workload sheet shows separate rows — no merging of rows that differ in DRR
  4. A workload category with a single uniform DRR still appears as one row (no spurious splits)
  5. A VM named "Veeam-Backup-01" or "CommvaultProxy" is classified to a backup/archive category rather than Unknown Reducible
  6. A VM named "Zabbix-Server" or "PRTG-Monitor" or "SolarWinds-NPM" is classified to a monitoring/infrastructure category rather than Unknown Reducible
  7. A VM named "MySQL-Prod" or "PostgreSQL-DB" or "MongoDB-Primary" is classified to an appropriate database category rather than Unknown Reducible
  8. Previously-classified VMs (SQL Server, Oracle, VDI, etc.) retain their existing classification — no regressions
  9. Sankey diagram in PDF shows no visible pixelation at 100% zoom in a PDF reader
  10. Every Sankey node and edge label is legible at standard print resolution (300 DPI equivalent)
  11. Sankey colors in PDF match the web UI color scheme
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 27. Session Save & Restore | v7.0 | 2/2 | Complete | 2026-02-24 |
| 28. Concerns Enrichment | v7.0 | 2/2 | Complete | 2026-02-24 |
| 29. Reporting Fidelity | v8.0 | 0/? | Not started | - |
