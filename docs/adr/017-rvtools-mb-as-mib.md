# ADR-017: RVTools "MB" Values Treated as MiB (No Conversion)

**Status:** Accepted
**Date:** 2026-02-19

## Context

RVTools column headers use the label "MB" (e.g., "Provisioned MB") but the actual values are base-2 mebibytes, not SI megabytes.

## Decision

Read RVTools storage values directly as MiB with no conversion factor applied.

## Rationale

- RVTools documentation confirms values are base-2 mebibytes despite the "MB" label
- Cross-checking against LiveOptics exports of the same workloads produces matching totals without conversion
- Applying a 1.048576 (MB-to-MiB) conversion factor would introduce a 4.9% error — a bug, not a fix

## Alternatives Considered

- **Apply MB-to-MiB conversion:** Produces systematically wrong results; a ~5% inflation in required capacity

## Consequences

- Column alias dictionaries (ADR-003) map "Provisioned MB" to `provisioned_mib` with no numeric transformation
- All arithmetic treats the loaded values as MiB throughout the pipeline
- This decision must be revisited if a future RVTools version changes its storage units
