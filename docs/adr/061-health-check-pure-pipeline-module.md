# ADR-061: Health checks as a pure pipeline module, not a blocking pipeline stage

**Date:** 2026-02-22
**Status:** Accepted

## Context

Phase 21 adds a `/concerns` page that surfaces data quality flags, sizing risks,
and VMware best practice violations. Two architectural approaches were considered:

1. **Blocking pipeline stage** — run health checks automatically during
   `ingest_file()` or `classify_dataframe()` and store findings in session.
2. **On-demand page-level computation** — call `run_health_checks(df)` on every
   `/concerns` page visit, starting from `load_session_data()`.

## Decision

Implement health checks as a pure pipeline module (`pipeline/health_checks.py`)
called on-demand from the `/concerns` page, never as an automatic pipeline step.

```python
# concerns.py — every page visit
df = load_session_data()
result = run_health_checks(df)
```

`HealthCheckResult` is a local variable. It is **never** written to
`app.storage.tab`.

## Rationale

The blocking stage approach would cache findings based on the initial
classification. When a user edits a VM's workload category in the Review grid
(e.g., changing "Unknown" to "Database"), the cached findings would remain stale
until the next upload. The pre-sales workflow depends on findings reflecting the
**current** workload assignments, not the initial classification.

Starting from `load_session_data()` ensures the correct `workload_category` values
(including user edits) are used for checks like "high Unknown VM ratio" and
"large Unknown VMs". If findings were recomputed on an old snapshot, the
"Unknown ratio" check could still fire even after the engineer has classified all
VMs correctly.

## Consequences

- **Positive:** Findings always reflect the user's current edited state — no
  stale cache.
- **Positive:** No new session storage key required — findings are cheap to
  recompute (pure pandas comparisons, <10ms for typical 400-VM datasets).
- **Positive:** The module is fully testable with real DataFrames — no NiceGUI
  context required.
- **Negative:** Health checks run on every page visit rather than once per
  upload. Acceptable given the sub-millisecond cost of pandas boolean masks at
  typical dataset sizes.
- **Constraint:** The `/concerns` page must never call `classify_dataframe()` —
  that would discard user edits. It must always start from `load_session_data()`.
