# ADR-021: Dual Workload Edit Mechanism (Dropdown + Dialog)

**Status:** Accepted
**Date:** 2026-02-19

## Context

Users need to assign one or more workload types to each VM. AG Grid Community Edition does not include a native multi-select cell editor.

## Decision

Provide two edit paths: an inline `agSelectCellEditor` dropdown for single-workload assignment, and a `WorkloadDialog` (see ADR-009) for multi-workload selection.

## Rationale

- Single-workload edit via dropdown is fast (one click) for the common case
- Multi-workload selection requires a dialog since AG Grid Community lacks this natively
- Both paths update the same `row_data` list and trigger the same stats rebuild
- Maintains UI consistency: one data model, two entry points

## Alternatives Considered

- **Dialog only:** More clicks for single-workload assignment; degrades the common-case UX
- **Custom JavaScript AG Grid editor:** High maintenance burden; requires bundling JS alongside Python

## Consequences

- Two code paths must be kept in sync around the `row_data` update and stats refresh
- Tested separately but produce identical downstream state
