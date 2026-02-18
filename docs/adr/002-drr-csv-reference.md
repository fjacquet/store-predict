# ADR-002: DRR Ratios from CSV, Not Hardcoded

**Status:** Accepted
**Date:** 2026-02-18

## Context

DRR (Data Reduction Ratio) values vary by workload category. Pre-sales engineers may need to update ratios as Dell publishes new benchmarks.

## Decision

Load DRR reference data from `samples/DRR.csv` at runtime, not hardcoded in source.

## Rationale

- Users can update ratios without code changes
- CSV is human-readable and editable
- Same format as vendor reference documentation
- Easy to version and diff

## Consequences

- Must handle CSV parsing edge cases (embedded newlines, trailing rows)
- File must be present at runtime
- 28 valid entries verified, not 30 as initially estimated
