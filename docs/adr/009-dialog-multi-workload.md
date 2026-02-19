# ADR-009: Dialog for Multi-Workload Assignment

**Status:** Accepted
**Date:** 2026-02-18

## Context

VMs may need multiple workload types assigned (e.g., a server running both SQL and file services). AG Grid community edition does not support multi-select cell editors.

## Decision

Use a custom awaitable `WorkloadDialog(ui.dialog)` triggered by row click for multi-workload assignment. Single-workload changes use inline `agSelectCellEditor`.

## Rationale

- AG Grid community has no built-in multi-select editor
- Awaitable dialog pattern is idiomatic NiceGUI
- Row click for multi-select, cell edit for single-select provides clear UX distinction
- `.props('persistent')` and `use-chips` prevent accidental dialog close during selection

## Consequences

- Two interaction patterns: cell edit (single) and row click (multi)
- DRR recalculates using the most conservative (lowest) ratio among selected workloads
- Dialog requires `.props('persistent')` to avoid backdrop-close bug
