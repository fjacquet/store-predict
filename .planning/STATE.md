# Project State — StorePredict

## Current Phase

Phase: 15-default-iops-and-docs (Plan 2 of 2 — COMPLETE)

## Milestone

v3.0 — Datastore Layout Recommendations

## Completed

- [x] PROJECT.md updated for v3.0
- [x] Research: PowerStore layout best practices, VM placement algorithms
- [x] REQUIREMENTS.md written (14 REQs + 4 NFRs)
- [x] ROADMAP.md written (5 phases, 7 plans)
- [x] Phase 14-01: layout_models.py + layout_engine.py (consolidation strategy, BFD core)
- [x] Phase 14-02: Performance strategy (Phase 0 isolation + tier BFD) + Uniform strategy (LPT) + generate_all_proposals() orchestrator
- [x] Phase 15-01: IOPS.csv package data + CSV loader for configurable IOPS defaults (REQ-014)
- [x] Phase 15-02: ADR-059, research page, architecture.md (4-stage pipeline), CHANGELOG.md v3.0.0

## Current Phase Progress

Phase 15: Plan 2/2 complete (15-01-SUMMARY.md and 15-02-SUMMARY.md exist)

## Next Action

Execute Phase 16 (next phase per ROADMAP.md)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Accurate DRR sizing + optimal datastore layout recommendations
**Current focus:** v3.0 — Datastore Layout Recommendations

## Decisions

(Carried from previous milestones — see v1.0/v1.1 archives)

- Multi-dimensional BFD chosen over ILP/OR-Tools (fast, no dependency, within 10-15% of optimal)
- Three fixed strategies with tunable parameters (Consolidation/Performance/Uniform)
- VMFS focus, not vVol (practical reality for migration projects)
- 4 TB default datastore size (Dell best practice sweet spot)
- 15-25 VMs/datastore default (Dell recommendation, queue depth validated)
- SDRS/SIOC deprecated in vSphere 8.0 U3 — use PowerStore QoS instead
- No PowerStore model recommendation (layout-only scope per user decision)
- Default IOPS estimates for RVTools imports (no performance data)
- TYPE_CHECKING guard for VMCalculation/CalculationSummary imports in layout modules (safe with from **future** import annotations)
- Oversized VM datastores use _OVER_ in name as the distinguishing marker
- generate_all_proposals() returns all 3 strategies (consolidation, performance, uniform)
- _classify_tier uses startswith("Database") not "in" — avoids false HOT match on "No Database, File nor Email" category string
- Workload-based prefix (DS_ORA, DS_HANA, DS_EXCHANGE) takes priority over generic DS_ISOLATED in _isolate_vms()
- Online help/tooltips added to Phase 18 (i18n & Polish) — all UI pages, FR+EN keys
- IOPS.csv stored in src/store_predict/data/ alongside DRR.csv (package data, not samples/) — samples/ is gitignored for customer data privacy
- stdlib csv.DictReader used for IOPS loader (not pandas) — keeps layout_models.py lightweight with zero extra dependencies
- ADR-059: workload-based IOPS defaults accepted; Linux/Windows IOPS split not implemented (documented as known limitation)
- mkdocs.yml nav corrected: ADRs 048-058 added, ADRs 015-033 filenames fixed (pre-existing bug resolved)

## Last Session

- **Stopped at:** Completed 15-02-PLAN.md
- **Timestamp:** 2026-02-21
