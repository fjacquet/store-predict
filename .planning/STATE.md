# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25 after v7.0.x polish complete)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Between milestones — v7.0.7 shipped, ready for `/gsd:new-milestone`

## Current Position

Phase: 28 of 28 (v7.0 complete)
Plan: 4 of 4 (milestone complete)
Status: v7.0.7 SHIPPED — milestone archived, v7.0.x polish complete

Last activity: 2026-02-25 — v7.0.x polish (Playwright removed, Plotly+kaleido, single PDF, auto dark mode, MkDocs nav cleanup, GSD status updated)

Progress: [██████████] 100% (v7.0 + v7.0.x polish done)

## Performance Metrics

| Phase | Plans | Duration | Files |
|-------|-------|----------|-------|
| Phase 27 P01 | 1 | ~3 min | 4 |
| Phase 27 P02 | 1 | ~5 min | 2 |
| Phase 28 P01 | 1 | ~10 min | 5 |
| Phase 28 P02 | 1 | ~8 min | 3 |

## Accumulated Context

### Key Architecture Decisions (carry forward)

- HealthCheckResult recomputed per-visit, not cached in session storage
- compute_sizing() AP values always computed; ap_enabled only controls UI display
- AG Grid row grouping is Enterprise-only — cluster grouping uses a separate table
- PDF path: ReportLab direct (no Playwright); generate_report_pdf() includes layout DS detail pages via _build_ds_detail_pages()
- __no_cluster__ sentinel in compute groupby (not None/NaN); translated to i18n in UI
- vmsc_site_a_hosts / vmsc_site_b_hosts enable asymmetric site display
- ap_secondary = max(1, ceil(primary/2)) — cold standby convention
- SESSION_ZIP_SENTINEL = "session.json" — presence in zip root identifies StorePredict archives
- session zip detection runs BEFORE LiveOptics zip extraction in handle_upload
- `or`-fallback in _load_constraints() and _load_compute_config() handles restored falsy values

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-25
Stopped at: v7.0.x polish complete — Playwright removed, Plotly+kaleido, single PDF, auto dark mode, MkDocs nav cleanup, GSD status updated
Resume file: None

Next step: `/gsd:new-milestone` to start next milestone planning.
