# ADR-064: Datacenter/cluster scope filtering as a dedicated pipeline stage

**Date:** 2026-02-23
**Status:** Accepted

## Context

Pre-sales engineers frequently receive RVTools or LiveOptics exports that span
multiple datacenters or clusters. They need to size a subset of the estate
(e.g., one datacenter being migrated to PowerStore) without discarding the rest
of the file. The previous pipeline applied every uploaded VM to all calculations
with no way to narrow scope after upload.

## Decision

Insert a `/scope` page between upload and review. The scope page reads the
`datacenter` and `cluster` columns that are already present in the canonical
DataFrame (v6.0 ingestion) and offers multi-select pickers for each dimension.
The selection is persisted in `app.storage.tab["scope_selection"]` via two new
state helpers:

- `save_scope_selection(datacenters, clusters)` — writes selected sets
- `get_scope_selection()` — returns `(set[str], set[str])`
- `load_filtered_session_data()` — returns the DataFrame filtered to the
  selected scope (or the full DataFrame when nothing is selected)
- `save_filtered_rows(row_data)` — merges AG Grid row edits back into the
  **full** unfiltered dataset, preserving unselected VMs

All downstream pages (review, report, compute, layout, concerns) call
`load_filtered_session_data()` instead of `load_session_data()`.

## Rationale

- Filtering at the session state layer is the least invasive change: no parser
  or calculation code needs modification.
- Storing the full dataset and applying scope at read time means engineers can
  change scope without re-uploading.
- `save_filtered_rows` merging back into the full dataset preserves edits on
  in-scope VMs while leaving out-of-scope rows untouched.
- A live VM count preview on the scope page gives immediate feedback on
  selection size before proceeding.

## Consequences

- **Positive:** Engineers can size any datacenter/cluster subset from a single
  file upload.
- **Positive:** Scope badge visible on review and report headers provides
  context for the output.
- **Positive:** Exported filenames include a scope suffix so engineers can
  distinguish multiple runs from the same file.
- **Negative:** An extra navigation step (scope page) is added to the workflow;
  mitigated by a "Select All" default and a clearly labelled "Skip" path.
- **Pattern:** Any future filtering dimension (e.g., tag, power state) should
  follow the same `load_filtered_session_data` contract.
