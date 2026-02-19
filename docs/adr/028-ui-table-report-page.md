# ADR-028: ui.table for Report Page (not AG Grid)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The report page displays a read-only workload breakdown table. The choice is between AG Grid (used on the review page) and NiceGUI's simpler `ui.table` (Quasar QTable).

## Decision

Use `ui.table` (Quasar) for the report page workload breakdown.

## Rationale

- The report table is read-only; no cell editing, sorting, or filtering is needed
- `ui.table` is lighter and requires less configuration than AG Grid
- Establishes a clear convention: `ui.aggrid` for interactive editing, `ui.table` for display

## Alternatives Considered

- **AG Grid on report page:** Brings unnecessary complexity, JS bundle size, and configuration overhead for a purely read-only context

## Consequences

- The convention `ui.table` = read-only, `ui.aggrid` = interactive must be documented and followed for future pages
- `ui.table` styling is controlled via Tailwind/Quasar classes rather than AG Grid column definitions
