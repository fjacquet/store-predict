---
phase: 20-grid-ux-vm-data-columns
verified: 2026-02-22T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 20: Grid UX & VM Data Columns Verification Report

**Phase Goal:** Users can search, filter, and inspect VM data more efficiently in the review grid — with per-VM CPU, RAM, and IOPS visible on demand
**Verified:** 2026-02-22
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                         | Status     | Evidence                                                                                       |
|----|-----------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | `row_index` column exists in CANONICAL_COLUMNS whitelist                                      | VERIFIED   | `columns.py` line 33: `"row_index"` appended at end of CANONICAL_COLUMNS list                |
| 2  | `ingestion.py` assigns `row_index` as contiguous integer after template filtering             | VERIFIED   | `ingestion.py` line 133: `df["row_index"] = df.index.astype(int)` after `reset_index`        |
| 3  | AG Grid `getRowId` uses `row_index` (not `vm_name`)                                           | VERIFIED   | `vm_table.py` line 159: `":getRowId": "params => String(params.data.row_index)"`             |
| 4  | `_handle_cell_change` matches rows by `row_index` (both branches)                             | VERIFIED   | `review.py` lines 341, 351, 368: `row_idx = int(...)`, `int(row.get("row_index", -2)) == row_idx` |
| 5  | `_handle_bulk_update` matches rows by `row_index`                                             | VERIFIED   | `review.py` lines 294, 298: `selected_ids = {int(r["row_index"]) ...}`, `int(row.get("row_index", -1)) in selected_ids` |
| 6  | Quick-filter input renders above VM grid calling `setGridOption('quickFilterText', ...)`      | VERIFIED   | `review.py` lines 144-149, 30: `ui.input` with `on_change` → `_on_quick_filter` → `setGridOption` |
| 7  | Column-toggle panel renders as collapsible expansion with four checkboxes                     | VERIFIED   | `review.py` lines 158-168: `ui.expansion(...)` with checkboxes for num_cpus, memory_mib, avg_iops, peak_iops |
| 8  | Each checkbox calls `setColumnsVisible`                                                       | VERIFIED   | `review.py` line 166: `grid.run_grid_method("setColumnsVisible", [f], e.value)`              |
| 9  | All four optional columns defined in `vm_table.py` columnDefs with `hide: True`              | VERIFIED   | `vm_table.py` lines 115-145: 4 entries with `"hide": True` for num_cpus, memory_mib, avg_iops, peak_iops |
| 10 | All new i18n keys present in `en.yaml`                                                        | VERIFIED   | `en.yaml`: `search_placeholder`, `column_panel_title`, `column_panel_tip`, `tooltip.quick_filter`, `columns.num_cpus`, `columns.memory_mib`, `columns.avg_iops` all present |
| 11 | All new i18n keys present in `fr.yaml` with correct French translations                       | VERIFIED   | `fr.yaml`: all 7 corresponding keys present with French translations                          |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact                                              | Expected                                               | Status     | Details                                                                                   |
|-------------------------------------------------------|--------------------------------------------------------|------------|-------------------------------------------------------------------------------------------|
| `src/store_predict/pipeline/parsers/columns.py`       | CANONICAL_COLUMNS with `row_index` appended            | VERIFIED   | Line 33: `"row_index"` present in list                                                   |
| `src/store_predict/pipeline/ingestion.py`             | `row_index` assignment after `reset_index`             | VERIFIED   | Line 133: `df["row_index"] = df.index.astype(int)` post-filter                           |
| `src/store_predict/pipeline/parsers/rvtools.py`       | Placeholder `result["row_index"] = 0` before return   | VERIFIED   | Line 111: placeholder assigned; line 112: `return result[CANONICAL_COLUMNS]`             |
| `src/store_predict/pipeline/parsers/liveoptics.py`    | Placeholder `result["row_index"] = 0` before both returns | VERIFIED | Lines 93, 232: both xlsx and csv paths have placeholder                                  |
| `src/store_predict/ui/components/vm_table.py`         | `getRowId` using `params.data.row_index`; 4 hidden cols| VERIFIED   | Line 159: `String(params.data.row_index)`; 4 entries with `"hide": True`                 |
| `src/store_predict/ui/pages/review.py`                | Quick-filter input + column-toggle expansion above grid| VERIFIED   | Lines 28-30, 142-168: `_on_quick_filter`, toolbar row, expansion with 4 checkboxes       |
| `src/store_predict/i18n/locales/en.yaml`              | New i18n keys for filter box and column panel          | VERIFIED   | Lines 25-27 (review section), 63-65 (columns section), 260 (tooltip)                    |
| `src/store_predict/i18n/locales/fr.yaml`              | French translations for all new keys                   | VERIFIED   | Lines 25-27 (review section), 63-65 (columns section), 260 (tooltip)                    |

### Key Link Verification

| From                              | To                          | Via                                                            | Status   | Details                                                                    |
|-----------------------------------|-----------------------------|----------------------------------------------------------------|----------|----------------------------------------------------------------------------|
| `ingestion.py`                    | `columns.py` CANONICAL_COLUMNS | `row_index` preserved through whitelist filter              | VERIFIED | `"row_index"` in CANONICAL_COLUMNS; parsers assign placeholder before filter |
| `vm_table.py`                     | row_data dicts              | `getRowId` JS expression reads `params.data.row_index`         | VERIFIED | `":getRowId": "params => String(params.data.row_index)"` confirmed         |
| `review.py` `_handle_cell_change` | row_data list               | matches by `int(row_index)` in both drr and workload branches  | VERIFIED | Lines 341, 351, 368: no vm_name comparison remains for row lookup          |
| `review.py` `_handle_bulk_update` | row_data list               | matches by `int(row_index)` in selected_ids set                | VERIFIED | Lines 294, 298: integer set comparison confirmed                           |
| `review.py` quick-filter input    | AG Grid quickFilterText     | `run_grid_method("setGridOption", "quickFilterText", ...)`     | VERIFIED | Lines 30, 146: lambda calls `_on_quick_filter` which calls `setGridOption` |
| `review.py` column-toggle checkboxes | AG Grid column visibility | `run_grid_method("setColumnsVisible", [f], e.value)`           | VERIFIED | Line 166: direct call in `_toggle_col` closure                             |
| `vm_table.py` columnDefs          | hidden column data          | `"hide": True` entries for all four optional columns           | VERIFIED | Lines 117, 125, 133, 141: four hidden entries confirmed                    |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                          | Status    | Evidence                                                              |
|-------------|-------------|--------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------|
| GUX-01      | 20-02-PLAN  | User can search VMs by text across all visible columns using a quick-filter box      | SATISFIED | `ui.input` in review.py wired to `setGridOption('quickFilterText')`  |
| GUX-02      | 20-02-PLAN  | User can toggle column visibility (CPU, RAM, IOPS) via AG Grid sidebar panel         | SATISFIED | `ui.expansion` with 4 checkboxes wired to `setColumnsVisible`        |
| VDAT-01     | 20-01-PLAN, 20-02-PLAN | User sees vCPU count and RAM (MiB) columns hidden by default, enabled via panel | SATISFIED | All 4 columns defined with `"hide": True`; num_cpus and memory_mib included |

All three requirement IDs from PLAN frontmatter are accounted for. No orphaned requirements found for Phase 20 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `review.py` | 127 | `detail_bar.placeholder` i18n key | Info | Not a code stub — legitimate UI label for empty state |
| `review.py` | 145 | `placeholder=t(...)` input prop | Info | Not a code stub — standard HTML input placeholder attribute |
| `rvtools.py` | 111 | `result["row_index"] = 0` | Info | Intentional design (placeholder overwritten by `ingest_file`) |
| `liveoptics.py` | 93, 232 | `result["row_index"] = 0` | Info | Intentional design (placeholder overwritten by `ingest_file`) |

No blocker or warning anti-patterns found. All flagged items are intentional or non-code uses of the word "placeholder".

### Human Verification Required

#### 1. Quick-filter narrows VM grid in real time

**Test:** Upload a file with 10+ VMs. On the Review page, type part of a VM name into the search box above the grid.
**Expected:** The grid updates instantly to show only matching rows across all visible columns.
**Why human:** NiceGUI callbacks and AG Grid `setGridOption` interactions cannot be verified without a running browser session.

#### 2. Column toggle shows/hides columns correctly

**Test:** On the Review page, open the "Show Columns" expansion panel. Check the "vCPUs" checkbox.
**Expected:** A num_cpus column appears in the grid. Unchecking hides it again.
**Why human:** `setColumnsVisible` DOM effect requires a live browser.

#### 3. French locale strings render correctly

**Test:** Switch locale to French. Verify the search placeholder reads "Rechercher des VMs..." and the panel title reads "Afficher les colonnes".
**Expected:** No raw YAML key strings (e.g., `review.search_placeholder`) visible in the UI.
**Why human:** Locale rendering requires a live application session.

### Gaps Summary

No gaps found. All automated checks passed across all three verification levels (exists, substantive, wired) for every must-have artifact and key link.

The phase delivered:

- A stable row identity system based on `row_index` (Plan 20-01) replacing the fragile `vm_name` approach that broke on duplicate VM names
- A quick-filter search input above the VM grid (Plan 20-02) correctly wired to AG Grid's `quickFilterText`
- A collapsible column visibility panel (Plan 20-02) with four checkboxes correctly wired to `setColumnsVisible`
- Four hidden column definitions in `vm_table.py` for num_cpus, memory_mib, avg_iops, peak_iops
- Complete i18n parity across en.yaml and fr.yaml for all 7 new keys

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
