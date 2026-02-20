# ADR-050: Row click = inspect (zoom), bulk button = reclassify

**Date:** 2026-02-20  
**Status:** Accepted

## Context

The review page originally opened a `WorkloadDialog` on every row click, allowing the
user to reclassify the clicked VM. This created two UX problems:

1. **Double interaction on editable cells** — clicking a dropdown cell triggered both the
   inline AG Grid editor and the WorkloadDialog simultaneously.
2. **No way to inspect details without triggering reclassification** — users could not
   simply view OS, description, or in-use metrics without accidentally opening the dialog.

## Decision

Separate the two actions by interaction type:

| Interaction | Action |
|-------------|--------|
| **Row click** (anywhere) | Update detail bar only — shows OS, Description, In Use MiB, performance fields for the clicked VM |
| **Checkbox selection + "Bulk Update" button** | Opens `WorkloadDialog` for all selected VMs — reclassification |

`_handle_row_click` is reduced to a 4-line function that only calls `_update_detail_bar`.
The `WorkloadDialog` is exclusively invoked from `_handle_bulk_update`.

## Consequences

- Single-VM reclassification now requires two steps (check + button) instead of one
  click, but eliminates the accidental dialog trigger on editable cells
- The detail bar provides immediate value on every click without side effects
- Consistent with standard grid UX: checkboxes = selection for batch operations,
  row click = inspect/navigate
- `_handle_row_click` no longer needs `drr_table`, `workload_options`, `grid`, or
  `stats_container` parameters — simpler signature reduces coupling
