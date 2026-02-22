# Phase 20: Grid UX & VM Data Columns - Research

**Researched:** 2026-02-22
**Domain:** NiceGUI AG Grid Community — column visibility, quick filter, row identity
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUX-01 | User can search VMs by text across all visible columns using a quick-filter box | `quickFilterText` grid option + `setGridOption('quickFilterText', text)` API — confirmed Community edition, no extra modules needed |
| GUX-02 | User can toggle column visibility (CPU, RAM, IOPS) via a panel | AG Grid sidebar is **Enterprise-only**; implement via NiceGUI custom checkbox panel + `run_grid_method('setColumnsVisible', [...], bool)` — confirmed Community API |
| VDAT-01 | User sees vCPU count and RAM (MiB) columns in the VM grid (hidden by default) | `num_cpus` and `memory_mib` are already in CANONICAL_COLUMNS and parsed by both parsers; add `hide: True` column defs to `vm_table.py` |
</phase_requirements>

---

## Summary

Phase 20 makes three changes to the VM review grid: (1) a quick-filter search box that narrows rows in real time, (2) a custom column-visibility panel that toggles CPU, RAM, and IOPS columns on/off, and (3) the vCPU and RAM columns themselves appearing in the grid as hidden-by-default columns. A fourth change — switching `getRowId` from `vm_name` to `row_index` — is required to fix a duplicate-VM-name corruption bug that would break row identity and IOPS joins for customer files containing template clones.

All required data already exists in the session. `num_cpus`, `memory_mib`, `peak_iops`, and `avg_iops` are all registered in `CANONICAL_COLUMNS` and populated by both parsers. The only code changes are in `vm_table.py` (column definitions, grid options) and `review.py` (quick-filter input widget + column-toggle panel). No parser changes, no new dependencies.

The single most important research finding is that the AG Grid **sidebar and column header menu are both Enterprise-only features** — they are not available in the Community bundle that NiceGUI ships. Column visibility toggling must be implemented as a custom NiceGUI checkbox panel above the grid that calls `run_grid_method('setColumnsVisible', ['col_id'], visible)`. This is confirmed by the official AG Grid documentation and aligns with the project's established pattern of calling `run_grid_method` for programmatic grid control.

**Primary recommendation:** Implement GUX-02 with a NiceGUI `ui.row` of `ui.checkbox` widgets — one per optional column — where each checkbox's `on_change` calls `await grid.run_grid_method('setColumnsVisible', [field_name], new_value)`. Do not attempt to configure `sideBar` in the grid options; it will silently fail or require Enterprise modules.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI | >=3.4,<4.0 | AG Grid wrapper + checkbox widgets | Already installed; `ui.aggrid` wraps AG Grid Community |
| AG Grid Community | bundled with NiceGUI | Grid filtering, column visibility API | NiceGUI ships Community edition only |
| pandas | >=2.2,<4.0 | DataFrame slicing for row_data prep | Already installed; used for session data |
| python-i18n | >=0.3.9 | All new UI strings via `t()` | Project convention; both locales must be updated together |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ui.input` (NiceGUI) | same | Quick-filter text input widget | Bind to `on_change` that calls `setGridOption('quickFilterText', ...)` |
| `ui.checkbox` (NiceGUI) | same | Column visibility toggles | One per optional column in panel above the grid |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ui.checkbox` panel for column visibility | AG Grid `sideBar: 'columns'` | Sidebar requires Enterprise license — Community bundle will silently ignore it |
| `run_grid_method('setColumnsVisible', ...)` | Updating `columnDefs` and calling `grid.update()` | Full column-def update rebuilds the entire grid; API method is instant and preserves scroll/filter state |
| `hide: True` column initial state | `initialHide: True` | `hide` works for both initial state and `setColumnsVisible` toggling; `initialHide` is only applied at column creation, not on updates |

**Installation:** No new dependencies — all tools are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All changes are in two existing files:

```
src/store_predict/
├── pipeline/
│   └── parsers/
│       └── columns.py     # Add row_index to CANONICAL_COLUMNS
├── ui/
│   ├── components/
│   │   └── vm_table.py    # Add hidden column defs + accept quick_filter_text param
│   └── pages/
│       └── review.py      # Add quick-filter input + column-toggle panel
```

Also:
```
src/store_predict/i18n/locales/
├── en.yaml    # Add new i18n keys for filter box + column panel
└── fr.yaml    # Same keys in French (parity enforced by test)
```

### Pattern 1: Quick Filter via `setGridOption`

**What:** A `ui.input` widget bound to `on_change` calls the AG Grid API method `setGridOption('quickFilterText', text)`. This triggers AG Grid's built-in cross-column text search on every keystroke.

**When to use:** Any time you need real-time search across all visible columns.

**Example:**
```python
# Source: AG Grid docs https://www.ag-grid.com/javascript-data-grid/filter-quick/
# + NiceGUI run_grid_method pattern from review.py

async def _on_quick_filter(e: Any, grid: ui.aggrid) -> None:
    await grid.run_grid_method("setGridOption", "quickFilterText", e.value)

ui.input(
    placeholder=t("review.search_placeholder"),
    on_change=lambda e: _on_quick_filter(e, grid),
).classes("w-full max-w-sm").props("clearable dense outlined")
```

**Notes:**
- `quickFilterText` splits on spaces — each word must match at least one column
- Case-insensitive by default
- Searches only visible columns (hidden columns are not searched)
- No extra configuration needed; works with the existing Community bundle

### Pattern 2: Column Visibility via `setColumnsVisible`

**What:** A custom NiceGUI panel with one `ui.checkbox` per optional column. Each checkbox's `on_change` calls `run_grid_method('setColumnsVisible', [field_id], visible)`.

**When to use:** When users need to show/hide columns (AG Grid sidebar is Enterprise-only).

**Example:**
```python
# Source: AG Grid Grid API docs https://www.ag-grid.com/javascript-data-grid/grid-api/
# setColumnsVisible is Community edition, part of ColumnApiModule (auto-included)

OPTIONAL_COLUMNS = [
    ("num_cpus",    "columns.num_cpus"),
    ("memory_mib",  "columns.memory_mib"),
    ("avg_iops",    "columns.avg_iops"),
    ("peak_iops",   "columns.peak_iops"),
]

with ui.row().classes("items-center gap-4 flex-wrap"):
    ui.label(t("review.show_columns")).classes("text-sm font-medium text-gray-600")
    for field, i18n_key in OPTIONAL_COLUMNS:
        async def _toggle(e: Any, f: str = field) -> None:
            await grid.run_grid_method("setColumnsVisible", [f], e.value)
        ui.checkbox(t(i18n_key), value=False, on_change=_toggle).classes("text-sm")
```

**Notes:**
- `setColumnsVisible` takes a list of column field names (strings) and a boolean
- The AG Grid Column API was deprecated in v31 and merged into the Grid API; `setColumnsVisible` (plural) is the current method name
- Initial column state is set via `"hide": True` in the column definition
- Checkboxes start `value=False` (column hidden) to match `"hide": True` in columnDefs

### Pattern 3: `row_index` as Stable Row Identity

**What:** During ingestion, after template filtering and `reset_index(drop=True)`, assign a `row_index` column equal to the DataFrame's integer index. Update `getRowId` in `vm_table.py` to use this field. Update cell-change handlers in `review.py` to look up rows by `row_index` instead of `vm_name`.

**When to use:** Always — this must precede any further grid work in this phase.

**Example:**
```python
# In ingestion.py — after reset_index:
df = df[~df["is_template"]].reset_index(drop=True)
df["row_index"] = df.index  # stable integer, survives JSON round-trip

# In vm_table.py — grid_options:
":getRowId": "params => String(params.data.row_index)",

# In review.py — cell change handler:
row_index = changed_data.get("row_index")
for row in row_data:
    if row.get("row_index") == row_index:
        # update this row
        break
```

**Notes:**
- `row_index` must be added to `CANONICAL_COLUMNS` in `columns.py` so it survives the `result[CANONICAL_COLUMNS]` filter in parsers
- `row_index` must also be added to `columns.py` parsers' output (both `rvtools.py` and `liveoptics.py`) via `result["row_index"] = result.index` **before** `return result[CANONICAL_COLUMNS]`
- The `getRowId` JS string must call `String(...)` to ensure the return is a string (AG Grid requirement)
- All places in `review.py` that look up rows by `vm_name` must switch to `row_index`; there are two: `_handle_cell_change` and `_handle_bulk_update`
- The bulk update uses `selected_names = {r["vm_name"] for r in selected}` — switch to `selected_ids = {r["row_index"] for r in selected}`

### Pattern 4: Hidden Column Definitions

**What:** Add column defs for `num_cpus`, `memory_mib`, `avg_iops`, `peak_iops` with `"hide": True`. These columns exist in every row's data but are not rendered unless the user enables them via the visibility panel.

**Example:**
```python
# Source: AG Grid column properties docs (Community edition)
# https://www.ag-grid.com/javascript-data-grid/column-properties/#reference-display-hide

{
    "field": "num_cpus",
    "headerName": t("columns.num_cpus"),
    "hide": True,
    "sortable": True,
    "filter": "agNumberColumnFilter",
    ":valueFormatter": "params => params.value != null ? params.value.toLocaleString() : '—'",
},
{
    "field": "memory_mib",
    "headerName": t("columns.memory_mib"),
    "hide": True,
    "sortable": True,
    "filter": "agNumberColumnFilter",
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
{
    "field": "avg_iops",
    "headerName": t("columns.avg_iops"),
    "hide": True,
    "sortable": True,
    "filter": "agNumberColumnFilter",
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
{
    "field": "peak_iops",
    "headerName": t("columns.peak_iops"),
    "hide": True,
    "sortable": True,
    "filter": "agNumberColumnFilter",
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
```

### Anti-Patterns to Avoid

- **Setting `sideBar: 'columns'` or `sideBar: True`:** The AG Grid sidebar is Enterprise-only. Setting it in grid options when using the Community bundle will silently fail (the sidebar panel simply does not render). Source: official AG Grid Community vs Enterprise comparison docs.
- **Using `grid.update()` to toggle column visibility:** Updating the full `options` dict and calling `grid.update()` rebuilds the entire grid, loses scroll position, resets sort/filter state, and is significantly slower than the API call. Use `run_grid_method('setColumnsVisible', ...)` instead.
- **Looking up rows by `vm_name` in cell-change handlers after switching to `row_index`:** If `getRowId` switches to `row_index` but handlers still match by `vm_name`, duplicate VM names will cause the wrong row to be updated. Switch all handlers together.
- **Adding `row_index` only to ingestion but not to `CANONICAL_COLUMNS`:** Both parsers end with `return result[CANONICAL_COLUMNS]`. If `row_index` is not in that list, it is silently stripped. Add it to `CANONICAL_COLUMNS` first.
- **Using `initialHide` instead of `hide`:** `initialHide` only applies at column creation. If the grid is re-instantiated, `initialHide` columns start hidden; but if the grid is rebuilt from updated options, `hide` is the reliable property.
- **`quickFilterText` searching hidden columns:** By design, AG Grid's quick filter only searches visible columns. Optional columns (CPU, RAM, IOPS) that are hidden will not be searched until the user shows them. This is correct behavior — document it in tooltips.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-column text search | Custom Python-side filter + `grid.update()` on every keystroke | AG Grid `quickFilterText` via `setGridOption` | Built-in, debounced, case-insensitive, no round-trip to server |
| Column visibility toggle | Custom columnDefs rebuild + `grid.update()` | `run_grid_method('setColumnsVisible', [...], bool)` | Single API call, preserves scroll/filter/sort state |
| Stable row identity | Hash of VM name or composite key | Integer `row_index` assigned at `reset_index()` time | Integers survive JSON round-trips without corruption; guaranteed unique |
| IOPS display formatting | Python-side number formatting in row_data | AG Grid `valueFormatter` JS expression in columnDef | Formatting stays on client, no Python processing |

**Key insight:** The AG Grid JavaScript API (`run_grid_method`) can drive column visibility directly from NiceGUI Python callbacks. No grid rebuild is needed; the API call is the correct tool for all post-initialization column state changes.

---

## Common Pitfalls

### Pitfall 1: AG Grid Sidebar is Enterprise-Only
**What goes wrong:** Developer adds `"sideBar": "columns"` or `"sideBar": True` to grid options, expecting a column visibility panel to appear. Nothing happens — no error, no sidebar.
**Why it happens:** AG Grid Community does not include the Sidebar or Tool Panels modules. Setting the option is silently ignored.
**How to avoid:** Use a custom NiceGUI checkbox panel above the grid. Call `run_grid_method('setColumnsVisible', [field], visible)` from each checkbox's `on_change`.
**Warning signs:** `"sideBar"` key appearing in `vm_table.py` grid_options — remove it.

### Pitfall 2: Duplicate VM Names Breaking Row Identity
**What goes wrong:** Customer RVTools exports often have duplicate VM names (clone templates, linked clones). AG Grid uses `getRowId` to uniquely identify rows. With `vm_name` as the ID, two rows sharing a name collapse into one row in AG Grid's internal store. Inline edits apply to the wrong row.
**Why it happens:** The current `getRowId` is `"params => params.data.vm_name"`. Duplicate names produce duplicate IDs.
**How to avoid:** Add `row_index` column during ingestion (stable integer), switch `getRowId` to `"params => String(params.data.row_index)"`, update all cell-change handlers to match by `row_index`.
**Warning signs:** Cells that appear to not update after editing when the grid has duplicate VM names.

### Pitfall 3: `row_index` Stripped by CANONICAL_COLUMNS Filter
**What goes wrong:** `row_index` is assigned in ingestion but stripped before being stored, because both parsers end with `return result[CANONICAL_COLUMNS]` and `row_index` is not in that list.
**Why it happens:** The canonical schema whitelist is the source of truth; anything not listed is dropped silently.
**How to avoid:** Add `"row_index"` to `CANONICAL_COLUMNS` in `columns.py` before adding it to the parsers. Also add `result["row_index"] = result.index` in both `parse_rvtools` and `_build_liveoptics_df` before the return.
**Warning signs:** `KeyError: 'row_index'` in `vm_table.py` when the grid tries to render the getRowId function.

### Pitfall 4: Integer `row_index` Becoming Float After JSON Round-Trip
**What goes wrong:** Session state is stored as JSON (`app.storage.tab`). Integer values in Python dicts can survive as integers in JSON, but when a DataFrame is reconstructed with `pd.DataFrame(records)`, pandas may infer `row_index` as float64 if any NaN is present in that column position.
**Why it happens:** JSON serialization of `None` mixed with integers causes pandas dtype inference to choose float64.
**How to avoid:** `row_index` is always a pure integer (set at `reset_index()` time, never NaN). But add a safety cast: `result["row_index"] = result.index.astype(int)`. In `_handle_cell_change`, read it as `int(changed_data.get("row_index", -1))`.
**Warning signs:** Row lookup logic fails to find the matching row because `0 != 0.0` in a dict lookup is `False` but `0 == 0.0` is `True` in Python — the subtlety is that `{r["row_index"] for r in row_data}` will contain floats if loaded from JSON, and `int(changed_data["row_index"])` will be an int. Use the same type on both sides.

### Pitfall 5: Quick Filter Searching Hidden Columns
**What goes wrong:** User types a CPU count in the quick filter box, expecting to find VMs with that CPU count. If the `num_cpus` column is hidden, AG Grid does not include it in the quick filter scan.
**Why it happens:** This is correct AG Grid behavior — hidden columns are excluded from `quickFilterText` scanning.
**How to avoid:** Document this in the filter box tooltip: "Searches all visible columns." Add a hint to the column toggle panel: "Tip: Show a column to include it in search."
**Warning signs:** User feedback that the search "missed" some VMs they know match.

### Pitfall 6: i18n Key Parity Gap
**What goes wrong:** New i18n keys added for the filter box, column panel labels, and new column headers are added in `en.yaml` but not `fr.yaml`. NiceGUI renders the key string itself as the label in French.
**Why it happens:** `python-i18n` silently returns the key when a translation is missing — no error, no warning.
**How to avoid:** Add all new keys to both `en.yaml` and `fr.yaml` simultaneously. The test `test_ux_polish.py` (parameterized over `["en", "fr"]`) catches missing keys for known keys — add the new phase-20 keys to that test's `REQUIRED_KEYS` list or write a new parameterized test block.
**Warning signs:** French UI shows raw dotted key strings like `columns.num_cpus` instead of translated text.

---

## Code Examples

Verified patterns from official sources and live codebase:

### Quick Filter Text Input Widget
```python
# Source: AG Grid filter-quick docs + NiceGUI run_grid_method (review.py:268)
# Place above the grid in review_page()

filter_input = (
    ui.input(
        placeholder=t("review.search_placeholder"),
        on_change=lambda e: _on_quick_filter(e, grid),
    )
    .classes("w-full max-w-sm")
    .props("clearable dense outlined prepend-icon=search")
    .tooltip(t("tooltip.quick_filter"))
)

async def _on_quick_filter(e: Any, grid: ui.aggrid) -> None:
    """Apply AG Grid quickFilterText on each keystroke."""
    await grid.run_grid_method("setGridOption", "quickFilterText", e.value or "")
```

### Column Visibility Panel (Custom, Community-Compatible)
```python
# Source: AG Grid setColumnsVisible Grid API docs (Community edition)
# NiceGUI ui.checkbox + run_grid_method pattern

TOGGLEABLE_COLUMNS: list[tuple[str, str]] = [
    ("num_cpus",   "columns.num_cpus"),
    ("memory_mib", "columns.memory_mib"),
    ("avg_iops",   "columns.avg_iops"),
    ("peak_iops",  "columns.peak_iops"),
]

with ui.expansion(t("review.column_panel_title"), icon="view_column").classes("w-full"):
    with ui.row().classes("items-center gap-6 flex-wrap p-2"):
        for field, key in TOGGLEABLE_COLUMNS:
            async def _toggle_col(e: Any, f: str = field) -> None:
                await grid.run_grid_method("setColumnsVisible", [f], e.value)
            ui.checkbox(t(key), value=False, on_change=_toggle_col)
```

### row_index Assignment in ingestion.py
```python
# Source: live codebase ingestion.py:128
# Add row_index AFTER template filter + reset_index

def ingest_file(path: Path) -> pd.DataFrame:
    ...
    # Filter out template VMs
    df = df[~df["is_template"]].reset_index(drop=True)
    # Stable integer row identity for AG Grid getRowId (Phase 20)
    df["row_index"] = df.index.astype(int)
    return df
```

### row_index in CANONICAL_COLUMNS and Parsers
```python
# Source: live codebase columns.py:12
# Add "row_index" to the list — parsers will then include it

CANONICAL_COLUMNS: list[str] = [
    "vm_name",
    "os_name",
    "num_cpus",
    "memory_mib",
    "provisioned_mib",
    "in_use_mib",
    "datacenter",
    "cluster",
    "is_template",
    "is_powered_on",
    "source_format",
    "vm_description",
    "peak_iops",
    "avg_iops",
    "peak_throughput_mbs",
    "avg_throughput_mbs",
    "peak_latency_ms",
    "avg_read_latency_ms",
    "avg_write_latency_ms",
    "iops_8k_equivalent",
    "row_index",  # <- ADD THIS (Phase 20)
]

# In rvtools.py and _build_liveoptics_df, before return result[CANONICAL_COLUMNS]:
result["row_index"] = result.index.astype(int)
return result[CANONICAL_COLUMNS]
```

### Updated getRowId in vm_table.py
```python
# Source: AG Grid getRowId docs + live vm_table.py:127
# Change from vm_name to row_index

# Before (Phase 19):
":getRowId": "params => params.data.vm_name",

# After (Phase 20):
":getRowId": "params => String(params.data.row_index)",
```

### Updated Cell Change Handler (row_index lookup)
```python
# Source: live review.py:305 — switch vm_name lookup to row_index

async def _handle_cell_change(e, row_data, drr_table, grid, stats_container):
    args = e.args
    col_id = args.get("colId", "")
    changed_data = args.get("data", {})
    row_index = int(changed_data.get("row_index", -1))  # stable integer
    new_value = args.get("newValue", "")

    ...
    for row in row_data:
        if int(row.get("row_index", -2)) == row_index:  # match by index
            row["workload_category"] = new_category
            ...
            break
```

### New i18n Keys Required (both en.yaml and fr.yaml)
```yaml
# Add to columns: section
columns:
  num_cpus: "vCPUs"          # en  |  "vCPUs"        # fr (same abbreviation)
  memory_mib: "RAM (MiB)"    # en  |  "RAM (Mio)"     # fr
  avg_iops: "Avg IOPS"       # en  |  "IOPS moy."     # fr
  # peak_iops already present in existing en.yaml

# Add to review: section
review:
  search_placeholder: "Search VMs..."    # en  |  "Rechercher des VMs..."  # fr
  column_panel_title: "Show Columns"     # en  |  "Afficher les colonnes"  # fr

# Add to tooltip: section
tooltip:
  quick_filter: "Search across all visible columns. Show hidden columns to include them."
  # fr: "Recherche dans toutes les colonnes visibles."
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AG Grid Column API (`columnApi.setColumnVisible`) | Grid API (`api.setColumnsVisible`) | AG Grid v31 | `run_grid_method('setColumnsVisible', ...)` is the correct current method name |
| `getRowId` using `vm_name` | `getRowId` using `row_index` (integer) | Phase 20 | Eliminates duplicate VM name corruption; required before any further grid work |
| No quick filter | `quickFilterText` via `setGridOption` | Phase 20 | User can search 100+ VM list without configuring individual column filters |

**Deprecated/outdated:**
- `columnApi.setColumnVisible` (singular): Moved to Grid API in v31 as `setColumnsVisible` (plural). Do not use `columnApi` in NiceGUI `run_grid_method` calls.
- AG Grid `sideBar: 'columns'`: Enterprise-only. Setting this in Community edition is a no-op.

---

## Open Questions

1. **Where exactly to assign `row_index` — parsers or `ingest_file`?**
   - What we know: Parsers return `result[CANONICAL_COLUMNS]`, so `row_index` must be in that list. `ingest_file` calls `reset_index(drop=True)` after template filtering, making it the natural assignment point. Parsers could also assign it.
   - What's unclear: If `row_index` is assigned in parsers (before template filtering), the indices will have gaps after filtering. If assigned in `ingest_file` (after filtering), indices are contiguous 0..N-1.
   - Recommendation: Assign in `ingest_file` after `reset_index(drop=True)` for contiguous indices. Parsers assign `result["row_index"] = result.index` only as a placeholder so the column exists before `result[CANONICAL_COLUMNS]` — then `ingest_file` overwrites it. Alternatively, add `row_index` to CANONICAL_COLUMNS and handle its assignment only in `ingest_file`, requiring parsers to add the column as a placeholder (e.g. `result["row_index"] = 0`). Choose consistency over cleverness: assign in `ingest_file` exclusively.

2. **Should `avg_iops` or `peak_iops` be shown in the toggle panel?**
   - What we know: Both are in CANONICAL_COLUMNS. `avg_iops` is more useful for sizing (average workload); `peak_iops` is more useful for performance validation.
   - What's unclear: The requirement says "IOPS columns" without specifying which.
   - Recommendation: Show both in the toggle panel. Default both to hidden. This matches the existing behavior where IOPS data is shown in the detail bar only for LiveOptics uploads.

3. **Should `row_index` be a visible column in the grid?**
   - What we know: It is used internally for `getRowId` and row matching but has no business value to users.
   - Recommendation: Add it to `columnDefs` with `"hide": True` and `"suppressColumnsToolPanel": True` (but this option is also Enterprise-only). Simplest: just don't add it to `columnDefs` at all — AG Grid can use a field for `getRowId` even if there is no column definition for it, as long as the field exists in `rowData`.

---

## Sources

### Primary (HIGH confidence)
- Live codebase: `src/store_predict/ui/components/vm_table.py` — current `getRowId`, column defs, grid options
- Live codebase: `src/store_predict/pipeline/parsers/columns.py` — confirmed `num_cpus`, `memory_mib`, `peak_iops`, `avg_iops` in CANONICAL_COLUMNS
- Live codebase: `src/store_predict/pipeline/parsers/rvtools.py` — confirmed `num_cpus` and `memory_mib` parsed
- Live codebase: `src/store_predict/pipeline/parsers/liveoptics.py` — confirmed `num_cpus` and `memory_mib` parsed
- Live codebase: `src/store_predict/ui/pages/review.py:268` — `run_grid_method` used for `getFilterModel` / `setFilterModel` — pattern confirmed working
- AG Grid official docs (2026): https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise/ — sidebar and column header menu are Enterprise-only
- AG Grid official docs (2026): https://www.ag-grid.com/javascript-data-grid/filter-quick/ — `quickFilterText` and `setGridOption('quickFilterText', text)` are Community
- AG Grid official docs (2026): https://www.ag-grid.com/javascript-data-grid/grid-api/ — `setColumnsVisible` is Community, signature: `setColumnsVisible(keys: string[], visible: boolean): void`
- AG Grid official docs (2026): https://www.ag-grid.com/javascript-data-grid/column-properties/#reference-display-hide — `hide: boolean` property is Community
- NiceGUI source (installed): `ui.aggrid.run_grid_method` calls `run_method('run_grid_method', name, *args)` — confirmed entry point for all AG Grid API calls

### Secondary (MEDIUM confidence)
- AG Grid column API migration note: Column API deprecated v31, all methods moved to Grid API; `setColumnsVisible` (plural) is the current method name
- `.planning/research/SUMMARY.md` — milestone research confirms row grouping is Enterprise-only, IOPS columns exist in schema

### Tertiary (LOW confidence)
- NiceGUI GitHub discussions — `agColumnsToolPanel` referenced in earlier discussions; validity of sidebar config in Community not independently re-verified beyond official docs above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against live `pyproject.toml` and NiceGUI source
- Architecture: HIGH — all integration points verified against live source code
- AG Grid Community/Enterprise boundary: HIGH — verified against official 2026 docs
- Pitfalls: HIGH — `row_index` pitfall and sidebar Enterprise trap verified directly
- i18n key additions: HIGH — pattern is established; keys not yet written but pattern is clear

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days; AG Grid Community API is stable)
