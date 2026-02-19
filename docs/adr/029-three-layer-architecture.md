# ADR-029: Three-Layer Architecture (pipeline → services → ui)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The codebase must remain testable and maintainable as it grows. Without clear boundaries, UI framework code tends to leak into business logic.

## Decision

Enforce a hard three-layer separation: `pipeline/` (pure data, no UI imports), `services/` (DRRTable, PDF generation), `ui/` (NiceGUI components only).

## Rationale

- All business logic in `pipeline/` and `services/` is testable without starting a NiceGUI server
- UI code importing from `pipeline/` is fine; the reverse is a violation (NFR-2.4)
- The services layer provides the bridge: it consumes pipeline DataFrames and produces artefacts the UI can display or download

## Alternatives Considered

- **Monolithic page handlers:** Business logic co-located with UI; impossible to test without a running server; common in naive NiceGUI projects

## Consequences

- `pipeline/` modules must never contain `from nicegui import ...`
- New features must be placed in the correct layer; code review should enforce this
- The architecture supports future headless CLI usage of the pipeline without UI changes
