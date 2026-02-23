# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23 after v5.0 milestone started)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Phase 24 — Health Findings Export (v5.0)

## Current Position

Phase: 24 of 26 (Health Findings Export)
Plan: 2 of 2 in current phase
Status: Phase 24 complete — all plans done (including gap closure plan 03)
Last activity: 2026-02-23 — Phase 24 Plan 03 complete (HEXP-01/02 gap closure: findings in Playwright PDF via report_print.py)

Progress: [████████████████░░░░] 80% (milestones 1-4 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 47
- Average duration: ~20 min
- Total execution time: ~15.7 hours

**By Phase (v5.0 — not started):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23. Multi-Cluster Compute | TBD | - | - |
| 24. Health Findings Export | TBD | - | - |
| 25. vMSC & DR Modeling | TBD | - | - |
| 26. Documentation | TBD | - | - |

*Updated after each plan completion*
| Phase 23-multi-cluster-compute P01 | 4 | 3 tasks | 6 files |
| Phase 23-multi-cluster-compute P02 | 1 | 2 tasks | 2 files |
| Phase 24-health-findings-export P01 | 10 | 2 tasks | 3 files |
| Phase 24-health-findings-export P02 | 12 | 2 tasks | 4 files |
| Phase 24 P03 | 8 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

- [Phase 21]: HealthCheckResult recomputed per-visit, not cached in session storage
- [Phase 21]: Findings grouped by check_id prefix (data_quality/sizing_risk/best_practice)
- [Phase 22]: compute_sizing() AP values always computed; ap_enabled only controls UI display
- [Phase 22]: ComputeSizingResult uses flat fields not nested SiteResult; vmsc_hosts_per_site=0 (not None)
- [Phase 22]: AG Grid row grouping is Enterprise-only — cannot use for cluster grouping in Community edition
- [Phase 23-multi-cluster-compute]: Sentinel __no_cluster__ used in compute_cluster_breakdown() for groupby key; UI display handled in Plan 02
- [Phase 23-multi-cluster-compute]: _check_hw_version_per_cluster() replaces global HW check; cluster field on HealthFinding defaults to empty string
- [Phase 23-multi-cluster-compute]: _check_small_cluster_ha() skips (No Cluster) group — standalone hosts have no HA context
- [Phase 23-multi-cluster-compute]: __no_cluster__ sentinel translated to i18n label in display; sentinel check determines whether multi-cluster table is shown
- [Phase 23-multi-cluster-compute]: cluster badge in concerns.py uses raw cluster name not i18n key — cluster names are vCenter environment data
- [Phase 24-health-findings-export]: HealthCheckResult imported via TYPE_CHECKING only; duck typing used at runtime to avoid circular imports
- [Phase 24-health-findings-export]: _category_label() maps check_id prefix to translated category; findings sorted critical-first in appendix page
- [Phase 24-health-findings-export]: Reuse pdf.findings_category_* keys in Excel sheet to avoid duplicate i18n translations
- [Phase 24-health-findings-export]: Size-based PDF test assertions for backward-compatibility tests due to ReportLab non-deterministic bytes
- [Phase 24]: Serialize findings as list[dict] in print_session rather than re-running run_health_checks() in report_print.py — avoids duplicate computation and ensures PDF/UI consistency
- [Phase 24]: HealthFinding.affected_vms (tuple) serialized as list for JSON safety, reconstructed as tuple on deserialization in report_print.py

### Pending Todos

None.

### Blockers/Concerns

- AG Grid Community edition constraint: cluster grouping in VM grid not available; per-cluster breakdown must be a separate table, not AG Grid grouping (locked decision from v4.0)

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 24-health-findings-export 24-03-PLAN.md
Resume file: None

Next step: Execute Phase 25 (vMSC & DR Modeling)
