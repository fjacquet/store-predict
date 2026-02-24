# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24 after v7.0 milestone started)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Phase 27 — Session Save & Restore

## Current Position

Phase: 27 of 28 (Session Save & Restore)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-02-24 — v7.0 roadmap created (Phases 27–28)

Progress: [░░░░░░░░░░] 0% (v7.0 milestone)

## Performance Metrics

**Velocity (v5.0 carry-forward):**
- Total plans completed v5.0: 8 (avg ~7 min/plan)

| Phase | Plans | Duration | Files |
|-------|-------|----------|-------|
| Phase 23-multi-cluster-compute | 2 | ~5 min | 8 |
| Phase 24-health-findings-export | 3 | ~30 min | 10 |
| Phase 25-vmsc-dr-modeling | 2 | ~20 min | 8 |
| Phase 26-documentation | 1 | ~2 min | 1 |

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

### Pending Todos

None.

### Blockers/Concerns

- CONC-01: Verify HealthCheckResult dataclass structure before extending with remediation field
- CONC-02: Confirm PDF approach (reuse Platypus pipeline vs new standalone ReportLab route)
- SAVE restore: Define JSON schema for session snapshot (vm_df serialization via orient="records" + dtypes map)

## Session Continuity

Last session: 2026-02-24
Stopped at: v7.0 roadmap created — Phases 27–28 defined, ready to plan Phase 27
Resume file: None

Next step: /gsd:plan-phase 27
