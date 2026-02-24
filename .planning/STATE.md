# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24 after v7.0 milestone started)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** v7.0 Save & Restore + Concerns

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v7.0
Last activity: 2026-02-24 — Milestone v7.0 started

Progress: [░░░░░░░░░░░░░░░░░░░░] 0% (v7.0 starting)

## Performance Metrics

**Velocity (v5.0):**
- Total plans completed: 8
- Total execution time: ~57 min (avg ~7 min/plan)

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
- AG Grid row grouping is Enterprise-only — cannot use for cluster grouping (Community edition)
- Playwright PDF path: serialize in report.py → print_session token → deserialize in report_print.py
- __no_cluster__ sentinel in compute groupby (not None/NaN); translated to i18n in UI
- vmsc_site_a_hosts / vmsc_site_b_hosts (not vmsc_hosts_per_site) — enables asymmetric display
- ap_secondary = max(1, ceil(primary/2)) regardless of ap_active_ratio — cold standby convention

### Pending Todos

None.

### Blockers/Concerns

- AG Grid Community edition: cluster grouping in VM grid not available — per-cluster breakdown uses a separate table (locked decision)

## Session Continuity

Last session: 2026-02-23
Stopped at: v5.0 milestone archived and released
Resume file: None

Next step: /gsd:plan-phase 27 — plan first phase of v7.0
