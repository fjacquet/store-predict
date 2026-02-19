# ADR-007: AG Grid for VM Review Table

**Status:** Accepted
**Date:** 2026-02-18

## Context

The review page needs a data table to display hundreds of VMs with sorting, filtering, pagination, and inline editing of workload categories.

## Decision

Use NiceGUI's `ui.aggrid` (AG Grid community edition) instead of `ui.table` (Quasar table).

## Rationale

- AG Grid handles thousands of rows with virtual scrolling
- Built-in `agSelectCellEditor` for inline workload dropdown
- Floating filters, column resize, and pagination out of the box
- Better performance with large datasets (5000+ VMs)

## Consequences

- Limited to AG Grid community features (no multi-select cell editor)
- Multi-workload assignment requires a separate dialog
- AG Grid options use JavaScript-style dict configuration
