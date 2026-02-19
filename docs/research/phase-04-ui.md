# Phase 4: UI Upload & Review Pages - Research

**Researched:** 2026-02-18
**Domain:** NiceGUI web UI (file upload, AG Grid table, session state, dark mode)
**Confidence:** HIGH

## Summary

Phase 4 implements the core user-facing UI: a file upload page and a review/edit page using NiceGUI 3.7.1. The upload page accepts RVTools/LiveOptics files, runs them through the existing ingestion + classification pipeline, and stores results in session state. The review page displays classified VMs in an AG Grid table with inline workload dropdown editing and a multi-select dialog for assigning multiple workloads with conservative DRR.

## Stack

| Component | Purpose | Key API |
|-----------|---------|---------|
| `ui.upload` | File dropzone for .xlsx/.csv | `on_upload`, `.props('accept=".xlsx,.csv"')` |
| `ui.aggrid` | AG Grid table for VM review | Options dict with columnDefs, rowData |
| `ui.dialog` | Multi-select workload dialog | Awaitable pattern with `self.submit()` |
| `ui.select` | Dropdown in dialog | `multiple=True`, options list |
| `ui.dark_mode` | Theme toggle | `.bind_value(app.storage.user, 'dark_mode')` |
| `app.storage.tab` | Per-tab session state | Dict-like, stores serializable data |
| `app.storage.user` | Per-user preferences | Dark mode persistence |

## Architecture Patterns

### Session State: Tab vs User Storage

- **`app.storage.tab`** for per-session upload data (DataFrame, project name) — multiple tabs stay independent
- **`app.storage.user`** for cross-page preferences (dark mode) — persists across sessions

DataFrames are serialized via `df.to_dict(orient="records")` and reconstructed with `pd.DataFrame(records)`.

### AG Grid Workload Editing

Single-click editing uses `agSelectCellEditor` from AG Grid community edition. Column definition includes `editable: True`, `singleClickEdit: True`, and a values list for the dropdown.

### Multi-Select Workload Dialog

AG Grid community edition lacks a multi-select cell editor. A custom `WorkloadDialog(ui.dialog)` subclass provides multi-workload assignment via row click. Uses `.props('persistent')` and `use-chips` to prevent accidental close during selection.

### Dark Mode Persistence

`ui.dark_mode()` is bound to `app.storage.user['dark_mode']` for cross-page persistence. Minor flash on initial page load is a known NiceGUI limitation.

### DRR Recalculation

When workloads change (either via cell edit or multi-select dialog), DRR is recalculated using the most conservative (lowest) ratio among selected workloads. Summary statistics rebuild in real-time.

## Key Decisions

- AG Grid over Quasar `ui.table` — better sorting, filtering, pagination for large datasets
- Tab storage for data, user storage for preferences — proper isolation
- Dialog for multi-select (AG Grid community limitation)
- `use-chips` prop on multi-select to prevent dialog backdrop-close issue
- Stats container clear+rebuild pattern for real-time updates

## Common Pitfalls

1. **DataFrame serialization** — NiceGUI storage requires JSON-serializable data; convert with `.to_dict(orient="records")`
2. **AG Grid update** — must call `aggrid.update()` after programmatic rowData changes
3. **Dialog closing on select click** — use `.props('persistent')` on dialog
4. **Upload content consumed** — `e.content.read()` can only be called once; store bytes
5. **storage_secret required** — `app.storage.user` needs `storage_secret` in `ui.run()`

## Sources

- NiceGUI 3.7.1 documentation (AG Grid, upload, dark_mode, storage)
- AG Grid community edition select cell editor
- NiceGUI GitHub discussions #675, #2237, #5394
- NiceGUI GitHub issues #1108 (multi-select dialog)
