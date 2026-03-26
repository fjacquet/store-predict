# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v8.0 — Reporting Fidelity

**Shipped:** 2026-03-26
**Phases:** 1 | **Plans:** 3 | **Sessions:** 1

### What Was Built

- DRR category split — `calculate()` groupby key changed from `workload_category` to `(category, drr)` tuple; closes Issue #5; separate rows in web UI, PDF, Excel
- Classification expansion — Veritas/NetBackup, Nagios/SolarWinds/Icinga/LibreNMS/OpenNMS, Redis patterns added; fewer Unknown Reducible VMs
- PDF Sankey at 300 DPI with ECharts palette alignment (`#DEE2E6`) and legible font sizes (mid-node 6, axis 7)

### What Worked

- **Parallel wave execution** — All 3 plans had zero inter-dependencies so they ran simultaneously as subagents; 3 tasks in ~20 min total
- **TDD red-green cycle** — Every feature had failing tests committed before implementation; verification was mechanical not investigative
- **Backward-compatible defaults** — `drr: float = 0.0` on frozen dataclass avoided breaking 30+ test fixtures; zero regressions
- **Source-level assertions** — `inspect.getsource()` for palette tests: faster and more deterministic than rendering+color-sampling

### What Was Inefficient

- **gsd-tools phase resolution** — `init execute-phase "29"` returned `phase_found: false` despite the directory existing; workaround required manual branch creation and STATE.md update
- **`milestone complete` accomplishment extraction** — gsd-tools couldn't parse SUMMARY.md frontmatter; MILESTONES.md entry required manual fixup after the CLI ran

### Patterns Established

- `(category, drr)` tuple as groupby key — if DRR can differ within a category, composite key is required throughout the pipeline
- Counter-based collision guard pattern — when generating node names from a list where duplicates are possible but rare, Counter pre-scan + conditional suffix is cleaner than always-suffix
- `img.imageWidth` (ReportLab native) for DPI verification in tests — avoids PIL dependency; pixel dimensions are a reliable proxy for render quality

### Key Lessons

1. **Fix the groupby key, not the display layer** — Issue #5 was a pipeline bug, not a reporting bug; fixing calculate() automatically fixed PDF and Excel with no extra work
2. **Source-code assertions beat rendering assertions for style properties** — palette, font size, DPI are constants in source; testing them at source level is 10x faster and zero false negatives
3. **gsd-tools CLI fragility on phase number matching** — when planning creates phase dirs with prefix (e.g., `029-reporting-fidelity`), the CLI's phase number matching may not resolve; prefer explicit file paths in subagent prompts

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: 1 (full milestone in single session + context compaction)
- Notable: Parallel wave execution cut wall-clock time by ~3x vs sequential execution

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v7.0 | 1 | 2 (27-28) | Introduced session save/restore + concerns export |
| v8.0 | 1 | 1 (29) | Merged 3 phases into 1 with parallel wave execution |

### Cumulative Quality

| Milestone | Tests | Coverage | New Tests Added |
|-----------|-------|----------|----------------|
| v7.0 | 519 | ~87% | ~30 |
| v8.0 | 552 | 88% | 33 (4 DRR + 18 classification + 3 PDF + 8 integration) |

### Top Lessons (Verified Across Milestones)

1. **Fix bugs at the pipeline layer** — both v7.0 (DRR export) and v8.0 (DRR category split) were calculation pipeline bugs that propagated to all surfaces; fixing upstream fixes all downstream automatically
2. **Parallel subagent execution works reliably** when tasks have zero shared state — confirmed in v7.0 and v8.0
