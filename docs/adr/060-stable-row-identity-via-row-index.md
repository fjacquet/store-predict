# ADR-060: Stable AG Grid row identity via row_index integer

**Date:** 2026-02-22
**Status:** Accepted

## Context

AG Grid requires a `getRowId` callback to uniquely identify rows for stable
updates (cell edits, bulk updates). The original implementation used `vm_name`
as the row identity:

```js
":getRowId": "params => params.data.vm_name"
```

Customer RVTools exports regularly contain duplicate VM names — linked clones,
template copies, and migrations all produce files where the same name appears
multiple times. When `getRowId` returns the same string for two rows, AG Grid
collapses them into a single logical row. Inline workload edits then silently
apply to the wrong VM.

## Decision

Assign a stable integer `row_index` (0-based, contiguous) in `ingest_file()`
after template filtering and `reset_index()`:

```python
df["row_index"] = df.index.astype(int)
```

Switch `getRowId` to:

```js
":getRowId": "params => String(params.data.row_index)"
```

`String()` is required — AG Grid expects a string from `getRowId`.

`row_index` is registered in `CANONICAL_COLUMNS` so it passes through the
parser whitelist. Parsers set a placeholder `result["row_index"] = 0` before
`return result[CANONICAL_COLUMNS]`; the real value is overwritten in
`ingest_file()`.

Both `_handle_cell_change` and `_handle_bulk_update` in `review.py` use
`int(row.get("row_index", -1)) == row_idx` for row matching instead of
string VM name comparison.

## Consequences

- **Positive:** Duplicate VM names no longer corrupt row identity or cause
  edits to silently apply to the wrong VM.
- **Positive:** `row_index` doubles as a stable join key for IOPS performance
  data merges.
- **Negative:** `row_index` is internal — it is defined in `CANONICAL_COLUMNS`
  but has no visible column definition in the grid (no `columnDef` entry), so
  it never appears as a user-visible column.
- **Neutral:** Existing unit tests continued passing without modification
  because tests that exercise `_handle_cell_change` construct records with
  `row_index` populated.
