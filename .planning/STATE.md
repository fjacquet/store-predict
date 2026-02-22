# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22 after v4.0 milestone)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Planning next milestone — run `/gsd:new-milestone`

## Current Position

Phase: 22 of 22 (v4.0 complete)
Status: v4.0 SHIPPED — archived, tagged, ready for next milestone
Last activity: 2026-02-22 — v4.0 milestone complete and archived

Progress: [██████████████████████████████] 22 phases complete

## Milestone

v4.0 VM Improvements & Compute Sizing — SHIPPED ✅

## Completed

- [x] v1.0 MVP Sizing Tool (Phases 1-7)
- [x] v1.1 i18n, Branding & Intelligence (Phases 8-13)
- [x] v2.x Storage Models, DRR Variants, Observability
- [x] v3.0 Datastore Layout Recommendations (Phases 14-19)
- [x] v4.0 VM Improvements & Compute Sizing (Phases 20-22) — shipped 2026-02-22

## Accumulated Context

- Full Python stack: NiceGUI + pandas + ReportLab + AG Grid
- 439 tests, 8,166 LOC at v4.0 close
- `row_index` is the stable AG Grid getRowId — never use vm_name for row identity
- Health checks must read session state after user edits, not re-run classification
- Compute presets loaded from CSV (`compute_presets.csv`); Custom entry must remain last
- TypedDict pattern for NiceGUI page session config dicts (ADR-063)
- AG Grid row grouping is Enterprise-only (Community edition constraint, locked decision)

## Session Continuity

Last session: 2026-02-22
Stopped at: v4.0 complete-milestone workflow — archived, tagged v4.0
Resume file: None

Next step: `/gsd:new-milestone` for v5.0

- **20-01**: Two-step placeholder approach — parsers set row_index=0, ingest_file overwrites with contiguous int after reset_index
- **20-01**: AG Grid getRowId uses String(params.data.row_index) for explicit type safety
- **20-01**: int() casts on both comparison sides prevent float/int mismatch from JSON round-trips
- **20-02**: Toolbar placed after grid assignment so closures reference valid variable name (Python captures name, not value)
- **20-02**: hide:True used instead of initialHide:True for reliable toggling with setColumnsVisible
- **20-02**: Custom NiceGUI expansion panel used for column toggle (AG Grid sidebar is Enterprise-only)
- [Phase 21-health-check-module-concerns-page]: hw_version sentinel 0 guards HW version checks; tools_status empty string guards tools checks
- [Phase 21]: Findings grouped by check_id prefix (data_quality/sizing_risk/best_practice) not by Severity
- [Phase 21]: HealthCheckResult recomputed per-visit, not cached in session storage
- [Phase 22-01]: ComputeSizingResult uses flat fields not nested SiteResult; vmsc_hosts_per_site=0 (not None); overcommit range [0.5, 20.0]
- [Phase 22]: dict[str, object] cfg type resolved via str() cast before int()/float() for mypy compliance
- [Phase 22]: compute_sizing() AP values always computed; ap_enabled only controls UI display
