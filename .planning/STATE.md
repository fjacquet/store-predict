# Project State — StorePredict

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required
**Current focus:** Phase 20 — Grid UX & VM Data Columns

## Current Position

Phase: 20 of 22 (Grid UX & VM Data Columns)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-02-22 — v4.0 roadmap created (Phases 20-22)

Progress: [████████████████████░░░░░░░░░░] 19 phases complete, 3 planned

## Milestone

v4.0 VM Improvements & Compute Sizing — IN PROGRESS

## Completed

- [x] v1.0 MVP Sizing Tool (Phases 1-7)
- [x] v1.1 i18n, Branding & Intelligence (Phases 8-13)
- [x] v2.x Storage Models, DRR Variants, Observability
- [x] v3.0 Datastore Layout Recommendations (Phases 14-19, 10 plans, 353 tests, 86% coverage)

## Accumulated Context

- Full Python stack: NiceGUI + pandas + ReportLab + AG Grid
- 353 tests, 86% coverage at v3.0 close
- RVTools vInfo tab has: VM Name, OS, Provisioned MiB, In Use MiB, vCPU, Memory (MB)
- LiveOptics VMs tab has: VM Name, VM OS, Virtual Disk Size (MiB), IOPS per VM
- `CANONICAL_COLUMNS` already contains num_cpus, memory_mib, peak_iops, avg_iops — no parser changes needed for v4.0
- AG Grid row grouping is Enterprise-only — use pandas-backed filter chips (Community edition constraint, locked decision)
- `getRowId` must switch from vm_name to row_index to handle duplicate VM names (fix in Phase 20)
- Health checks must read session state after user edits, not re-run classification (architectural constraint)
- Phase numbering: v4.0 is Phases 20-22

## Blockers/Concerns

- [Phase 22]: vMSC sizing requires 2+ distinct datacenter values — implement with graceful degradation warning
- [Phase 22]: Dell PowerEdge preset specs need validation against current product catalog
- [Phase 21/22]: i18n key parity — add pytest assertion set(en_keys)==set(fr_keys) before first new-page PR

## Session Continuity

Last session: 2026-02-22
Stopped at: Roadmap created for v4.0 (Phases 20-22). Ready to plan Phase 20.
Resume file: None
