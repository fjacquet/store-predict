# ADR-014: DRR Guard with max(drr, 0.1)

**Status:** Accepted
**Date:** 2026-02-19

## Context

Division by DRR is the core calculation. A DRR of zero or negative is not meaningful for storage sizing but could arrive from a corrupt CSV or a future editing mistake.

## Decision

Before computing `required_mib = provisioned_mib / drr`, clamp the divisor with `max(drr, 0.1)`.

## Rationale

- Prevents `ZeroDivisionError` without silently hiding bad data
- A floor of 0.1 implies 10x capacity expansion — obviously wrong and visible to reviewers
- Does not swallow the error; the nonsensical result prompts investigation

## Alternatives Considered

- **Skip VMs with DRR <= 0:** Silent data loss; sizing report would be incomplete
- **Raise an exception:** Crashes the entire report for one bad row; poor UX

## Consequences

- Corrupted or zero DRR values produce extreme required capacity numbers in the report
- Users are expected to catch these as outliers during review
- The floor value (0.1) is a visible magic constant and is documented here
