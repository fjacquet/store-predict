# Project State — StorePredict

## Current Phase

Phase: 14-layout-engine-core (Plan 2 of 2)

## Milestone

v3.0 — Datastore Layout Recommendations

## Completed

- [x] PROJECT.md updated for v3.0
- [x] Research: PowerStore layout best practices, VM placement algorithms
- [x] REQUIREMENTS.md written (14 REQs + 4 NFRs)
- [x] ROADMAP.md written (5 phases, 7 plans)
- [x] Phase 14-01: layout_models.py + layout_engine.py (consolidation strategy, BFD core)

## Current Phase Progress

Phase 14: Plan 1/2 complete (14-01-SUMMARY.md exists)

## Next Action

Execute Plan 14-02: Performance and Uniform strategies.

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
- TYPE_CHECKING guard for VMCalculation/CalculationSummary imports in layout modules (safe with from __future__ import annotations)
- Oversized VM datastores use _OVER_ in name as the distinguishing marker
- generate_all_proposals() returns consolidation only in Plan 14-01; Performance/Uniform added in 14-02

## Last Session

- **Stopped at:** Completed 14-01-PLAN.md — layout engine data models and consolidation strategy
- **Timestamp:** 2026-02-21
