# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24 after v7.0 milestone started)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Phase 27 — Session Save & Restore

## Current Position

Phase: 27 of 28 (Session Save & Restore)
Plan: 2 of 2 in current phase (27-01, 27-02 complete)
Status: Phase 27 complete
Last activity: 2026-02-24 — 27-02 complete (Save Session button in report.py + session restore branch in upload.py)

Progress: [██░░░░░░░░] 20% (v7.0 milestone — 2 plans done)

## Performance Metrics

**Velocity (v5.0 carry-forward):**
- Total plans completed v5.0: 8 (avg ~7 min/plan)

| Phase | Plans | Duration | Files |
|-------|-------|----------|-------|
| Phase 23-multi-cluster-compute | 2 | ~5 min | 8 |
| Phase 24-health-findings-export | 3 | ~30 min | 10 |
| Phase 25-vmsc-dr-modeling | 2 | ~20 min | 8 |
| Phase 26-documentation | 1 | ~2 min | 1 |
| Phase 27-session-save-restore P01 | 1 | ~3 min | 4 |
| Phase 27-session-save-restore P02 | 8 | 2 tasks | 2 files |

## Accumulated Context

### Key Architecture Decisions (carry forward)

- HealthCheckResult recomputed per-visit, not cached in session storage
- compute_sizing() AP values always computed; ap_enabled only controls UI display
- AG Grid row grouping is Enterprise-only — cluster grouping uses a separate table
- Playwright PDF path: serialize in report.py → print_session token → deserialize in report_print.py
- __no_cluster__ sentinel in compute groupby (not None/NaN); translated to i18n in UI
- vmsc_site_a_hosts / vmsc_site_b_hosts enable asymmetric site display
- ap_secondary = max(1, ceil(primary/2)) — cold standby convention

### Decisions (v7.0 planning)

- Session .zip format: original uploaded file + JSON snapshot (not DB, not pickle — portable and human-inspectable)
- Restore entry point: Upload page (not a separate route — keeps UX simple, users already know Upload page)
- CONC-01 remediation hints: extend HealthCheckResult dataclass with remediation: str field
- CONC-02/03 exports: standalone from /concerns page — independent of main report pipeline
- Session archive schema_version=1 in JSON for forward compatibility; is_session_zip() never raises
- restore_session_zip() uses IngestionError (not ValueError/KeyError) to integrate cleanly with pipeline error handling
- Layout/compute sub-dict types: dict[str, float | int] / dict[str, float | int | bool | str] for mypy compliance
- Save Session button uses purple styling to differentiate from PDF (blue) and Excel (green) download buttons
- Session zip detection runs BEFORE LiveOptics zip extraction in handle_upload to avoid false positive extraction

### Pending Todos

None.

### Blockers/Concerns

- CONC-01: Verify HealthCheckResult dataclass structure before extending with remediation field
- CONC-02: Confirm PDF approach (reuse Platypus pipeline vs new standalone ReportLab route)

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 27-02-PLAN.md — Save Session button + session restore UI wiring
Resume file: None

Next step: Phase 27 complete — proceed to Phase 28
