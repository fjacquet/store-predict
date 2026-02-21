# ADR-048: AG Grid Community constraint — detail bar instead of master-detail

**Date:** 2026-02-20
**Status:** Accepted

## Context

The review page needed to show supplementary VM data (OS, Description, In Use MiB,
performance metrics) without cluttering the main classification grid. The initial plan
called for AG Grid's built-in master-detail rows (`masterDetail: true`) with a `›`
expand icon on each row opening an inline sub-panel.

## Decision

After implementation, Playwright tests revealed:

```text
AG Grid: error #200 Unable to use masterDetail as MasterDetailModule is not registered
AG Grid: error #200 Unable to use agGroupCellRenderer
```

`masterDetail`, `MasterDetailModule`, and `agGroupCellRenderer` are **AG Grid Enterprise**
features. NiceGUI 3.x ships AG Grid Community. We do not have an Enterprise license.

We replaced the master-detail approach with a **detail bar** — a `ui.row` container
placed above the grid that updates on `rowClicked` events to display supplementary fields
for the selected VM.

## Consequences

- No Enterprise license required
- Detail bar is always visible (no expand/collapse), showing placeholder text until a row
  is clicked — simpler and arguably clearer UX for a review workflow
- If an Enterprise license is obtained in the future, master-detail rows can be reinstated
  by reverting `vm_table.py` and removing the detail bar from `review.py`
- Column definitions for supplementary fields (os_name, vm_description, in_use_mib,
  performance columns) are no longer needed in the grid; data is passed directly from
  `row_data` to the detail bar update function
