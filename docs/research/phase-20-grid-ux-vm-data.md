# Phase 20 Research: Grid UX & VM Data Columns

**Phase:** 20
**Date:** 2026-02-22
**Status:** Complete

## Problem

Pre-sales engineers reviewing large VM lists (100–400+ VMs) needed two things:

1. **Quick search** — type a VM name fragment and instantly narrow the visible rows.
2. **On-demand hardware data** — see vCPU count and RAM without cluttering the grid by default.

Additionally, duplicate VM names in customer exports caused AG Grid's `getRowId`
to produce collisions, silently applying workload edits to the wrong VMs.

## Key Findings

### AG Grid Community vs Enterprise

AG Grid's sidebar (column visibility panel, filter panel) is an **Enterprise**
feature and silently fails in Community edition. The column toggle panel must be
implemented as a custom NiceGUI `ui.expansion` with `ui.checkbox` widgets calling
`run_grid_method('setColumnsVisible', [field], bool)`.

Quick-filter (`quickFilterText`) is Community-safe:

```python
await grid.run_grid_method("setGridOption", "quickFilterText", text)
```

### CANONICAL_COLUMNS whitelist

All columns used in the grid or health checks must be registered in
`CANONICAL_COLUMNS` in `pipeline/parsers/columns.py`. The line
`return result[CANONICAL_COLUMNS]` at the end of each parser silently strips
unregistered columns. New columns must be added to `columns.py` **before**
modifying parsers.

### row_index as stable identity

`vm_name` is not a reliable row key — linked clones, template copies, and
migrations regularly produce duplicate names. Using a 0-based integer assigned
after template filtering guarantees uniqueness. See ADR-060.

## Implementation

- `row_index` added to `CANONICAL_COLUMNS`; assigned in `ingest_file()` via
  `df.index.astype(int)` after `reset_index(drop=True)`
- Parsers set placeholder `result["row_index"] = 0` before the CANONICAL_COLUMNS
  filter; `ingest_file()` overwrites with the real value
- `getRowId` switched to `String(params.data.row_index)`
- Four hidden column defs added (`num_cpus`, `memory_mib`, `avg_iops`,
  `peak_iops`) with `"hide": True`
- Quick-filter input and column-toggle expansion added above the grid in
  `review_page()`

## Patterns Established

- Side-effect imports for NiceGUI route registration use `# noqa: F401`
- `_on_quick_filter` async helper defined **before** the `@ui.page` function to
  avoid Pyright forward-reference warnings
- Loop variables in `for _field, _key in toggleable_columns` renamed to
  `_field`/`_key` to satisfy ruff N806
