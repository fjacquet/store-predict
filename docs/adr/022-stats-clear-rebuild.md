# ADR-022: Stats Container Clear-and-Rebuild Pattern

**Status:** Accepted
**Date:** 2026-02-19

## Context

When a user changes a VM's workload classification, the summary statistics panel must update to reflect the new DRR totals. NiceGUI supports several update strategies.

## Decision

On workload change: call `stats_container.clear()` followed by `build_summary_stats()` to regenerate the entire stats panel.

## Rationale

- Simpler than tracking references to individual labels and updating each in place
- The stats panel is small (< 10 widgets); clear-and-rebuild is not a performance concern
- Eliminates the risk of stale UI state if the number of stat rows changes

## Alternatives Considered

- **Reactive bindings:** Requires binding each stat value to a reactive variable; adds boilerplate and NiceGUI-specific complexity
- **Partial updates:** Requires maintaining widget references and carefully matching old to new values

## Consequences

- Any animation or focus state on the stats panel is lost on rebuild (acceptable)
- The `build_summary_stats` function must be pure enough to be called multiple times without side effects
