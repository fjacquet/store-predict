# Roadmap: StorePredict v7.0 — Save & Restore + Concerns

## Milestones

- ✅ **v1.0 MVP** - Phases 1–7 (shipped 2026-02-19)
- ✅ **v1.1 i18n, Branding & Intelligence** - Phases 8–13 (shipped 2026-02-20)
- ✅ **v2.x Storage Models, DRR Variants, Observability** - Phases shipped outside GSD planning (2026-02-20/21)
- ✅ **v3.0 Datastore Layout** - Phases 14–19 (shipped 2026-02-21)
- ✅ **v4.0 VM Improvements & Compute Sizing** - Phases 20–22 (shipped 2026-02-22)
- ✅ **v5.0 Multi-Cluster & Export Completeness** - Phases 23–26 (shipped 2026-02-23)
- ✅ **v6.0/v6.1 Scope Filtering & Dual-Source Merge** - shipped outside GSD planning (2026-02-24)
- 🚧 **v7.0 Save & Restore + Concerns** - Phases 27–28 (in progress)

## Phases

<details>
<summary>✅ v1.0 through v6.1 (Phases 1–26) — SHIPPED</summary>

Phases 1–26 covered MVP, i18n/branding, storage models, datastore layout,
VM improvements, compute sizing, multi-cluster export, scope filtering, and
dual-source merge. See MILESTONES.md for detail.

</details>

### 🚧 v7.0 Save & Restore + Concerns (In Progress)

**Milestone Goal:** Enable pre-sales engineers to save a complete sizing session
to a portable .zip archive and restore it later, plus enrich the /concerns page
with actionable remediation hints and standalone PDF/CSV exports.

- [ ] **Phase 27: Session Save & Restore** - User can save and restore a full sizing session via a self-contained .zip file
- [ ] **Phase 28: Concerns Enrichment** - Each health finding displays a remediation hint; /concerns is exportable as standalone PDF and CSV

## Phase Details

### Phase 27: Session Save & Restore
**Goal**: Users can persist a complete sizing session to a portable .zip file and restore it from the Upload page with all state intact
**Depends on**: Phase 26 (prior milestone complete)
**Requirements**: SAVE-01, SAVE-02, SAVE-03, SAVE-04, SAVE-05
**Success Criteria** (what must be TRUE):
  1. User can click a Save Session button and download a .zip containing the original uploaded file plus a JSON snapshot of all session state
  2. The saved .zip captures VM list, workload classifications, DRR overrides, layout settings, and compute settings
  3. User can upload a .zip file on the Upload page and have the tool recognize it as a session restore
  4. After restore, the tool lands on the Upload page with all VM data, classifications, and settings loaded exactly as they were when saved
  5. Save and restore work regardless of whether the original input was RVTools .xlsx, LiveOptics .xlsx, LiveOptics .csv, or a dual-source merge
**Plans**: 2 plans

Plans:
- [ ] 27-01-PLAN.md — Session archive module (save_session_zip, restore_session_zip) + i18n keys + tests
- [ ] 27-02-PLAN.md — Upload page session restore branch + report page Save Session button

### Phase 28: Concerns Enrichment
**Goal**: Each health finding on /concerns includes an actionable remediation hint, and the full concerns report is exportable as a standalone PDF or CSV
**Depends on**: Phase 27
**Requirements**: CONC-01, CONC-02, CONC-03
**Success Criteria** (what must be TRUE):
  1. Every health finding card on /concerns displays a concise text hint explaining what action to take to address the issue
  2. User can click an Export PDF button on /concerns and download a standalone PDF report containing all findings and remediation hints
  3. User can click an Export CSV button on /concerns and download a CSV file with one row per finding, including severity, description, and remediation hint columns
  4. The standalone PDF and CSV exports are independent of the main sizing report and can be generated without navigating away from /concerns
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 27. Session Save & Restore | v7.0 | 0/2 | In planning | - |
| 28. Concerns Enrichment | v7.0 | 0/? | Not started | - |
