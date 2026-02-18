# Phase 4: UI Upload & Review Pages - Research

**Researched:** 2026-02-18
**Domain:** NiceGUI web UI (file upload, AG Grid table, session state, dark mode)
**Confidence:** HIGH

## Summary

This phase implements the core user-facing UI: a file upload page and a review/edit page using NiceGUI 3.7.1 (already installed). The upload page accepts RVTools/LiveOptics files, runs them through the existing ingestion + classification pipeline, and stores results in session state. The review page displays classified VMs in an AG Grid table with inline workload dropdown editing and a multi-select dialog for assigning multiple workloads with conservative DRR.

NiceGUI wraps AG Grid (community edition) and Quasar Vue components. The AG Grid wrapper (`ui.aggrid`) accepts standard AG Grid option dictionaries and exposes events like `cellValueChanged`. For session persistence, NiceGUI provides `app.storage.user` (per-user, cross-tab) and `app.storage.tab` (per-tab). Dark mode is handled by `ui.dark_mode()` with binding to storage.

**Primary recommendation:** Use `app.storage.tab` for per-session DataFrame state (upload data + classifications), `app.storage.user` for dark mode preference, AG Grid with `agSelectCellEditor` for single-select workload editing, and an awaitable `ui.dialog` subclass with `ui.select(multiple=True)` for multi-workload assignment.

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI | 3.7.1 | Full UI framework (pages, components, routing) | Already chosen, installed |
| pandas | >=2.2 | DataFrame for VM data manipulation | Already used by pipeline |

### NiceGUI Components Used
| Component | Purpose | Key API |
|-----------|---------|---------|
| `ui.upload` | File dropzone for .xlsx/.csv | `on_upload`, `.props('accept=".xlsx,.csv"')` |
| `ui.aggrid` | AG Grid table for VM review | Options dict with columnDefs, rowData |
| `ui.dialog` | Multi-select workload dialog | Awaitable pattern with `self.submit()` |
| `ui.select` | Dropdown in dialog | `multiple=True`, options list |
| `ui.dark_mode` | Theme toggle | `.bind_value(app.storage.user, 'dark_mode')` |
| `ui.input` | Project name field | Standard text input |
| `ui.label` | Summary statistics display | Reactive binding |
| `ui.navigate` | Page-to-page navigation | `ui.navigate.to('/review')` |
| `app.storage.tab` | Per-tab session state | Dict-like, stores serializable data |
| `app.storage.user` | Per-user preferences | Dark mode persistence |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ui.aggrid` | `ui.table` (Quasar table) | AG Grid has better built-in sorting/filtering/pagination; table needs custom slots for dropdowns |
| `app.storage.tab` | `app.storage.user` for data | tab is better for upload data since each session should be independent |
| Awaitable dialog | Inline multi-select in grid | AG Grid community has no multi-select cell editor; dialog is cleaner UX |

## Architecture Patterns

### Recommended Project Structure
```
src/store_predict/
  ui/
    __init__.py
    layout.py              # Shared layout context manager (EXISTS)
    state.py               # NEW: Session state helpers (get/set DataFrame, project name)
    components/
      __init__.py
      upload_card.py        # NEW: Upload dropzone + format detection card
      vm_table.py           # NEW: AG Grid table wrapper with column defs
      workload_dialog.py    # NEW: Awaitable multi-select workload dialog
      summary_stats.py      # NEW: Real-time summary statistics component
      dark_mode_toggle.py   # NEW: Dark/light mode toggle button
    pages/
      __init__.py
      upload.py             # EXISTS (stub) - full upload page
      review.py             # NEW: review/edit page
      report.py             # Future (Phase 5)
```

### Pattern 1: Per-Tab Session State with DataFrame Serialization
**What:** Store uploaded DataFrame and classification results in `app.storage.tab` as JSON-serializable dicts (list of row dicts), not raw DataFrames.
**When to use:** Always for per-session upload data.
**Example:**
```python
# Source: NiceGUI storage docs + pandas API
from nicegui import app
import pandas as pd

def save_dataframe(df: pd.DataFrame) -> None:
    """Store classified DataFrame in tab-scoped session."""
    app.storage.tab["vm_data"] = df.to_dict(orient="records")
    app.storage.tab["project_name"] = app.storage.tab.get("project_name", "")

def load_dataframe() -> pd.DataFrame | None:
    """Retrieve DataFrame from session, or None if not uploaded yet."""
    records = app.storage.tab.get("vm_data")
    if records is None:
        return None
    return pd.DataFrame(records)
```

### Pattern 2: AG Grid with Workload Dropdown Editor
**What:** AG Grid column definition using `agSelectCellEditor` for inline workload category selection.
**When to use:** Single-select workload override per VM (FR-4.2).
**Example:**
```python
# Source: NiceGUI aggrid docs + AG Grid select editor
from nicegui import ui

categories = [
    "Database", "HealthCare", "File", "VDI",
    "Logging - Analytics", "Email", "Containers",
    "Virtual Machines", "VM Replication", "Boot from SAN",
    "Web Servers", "Unknown (Reducible)", "Custom DRR",
]

grid = ui.aggrid({
    "columnDefs": [
        {"field": "vm_name", "headerName": "VM Name", "sortable": True,
         "filter": "agTextColumnFilter", "floatingFilter": True},
        {"field": "os_name", "headerName": "OS", "sortable": True,
         "filter": "agTextColumnFilter", "floatingFilter": True},
        {"field": "workload_category", "headerName": "Workload",
         "editable": True, "singleClickEdit": True,
         "cellEditor": "agSelectCellEditor",
         "cellEditorParams": {"values": categories}},
        {"field": "drr", "headerName": "DRR", "sortable": True,
         "filter": "agNumberColumnFilter"},
        {"field": "provisioned_mib", "headerName": "Provisioned (MiB)",
         "sortable": True, "filter": "agNumberColumnFilter"},
    ],
    "rowData": row_data,
    "pagination": True,
    "paginationPageSize": 50,
    "rowSelection": {"mode": "singleRow"},
    "stopEditingWhenCellsLoseFocus": True,
}).on("cellValueChanged", handle_cell_change)
```

### Pattern 3: Awaitable Multi-Select Dialog
**What:** Custom dialog class that returns selected workload types when submitted.
**When to use:** FR-4.3 multi-workload assignment via row click.
**Example:**
```python
# Source: NiceGUI dialog docs + daelon.dev dialog pattern
from nicegui import ui

class WorkloadDialog(ui.dialog):
    def __init__(self, vm_name: str, current_workloads: list[str],
                 all_options: list[dict]) -> None:
        super().__init__()
        with self, ui.card().classes("w-96"):
            ui.label(f"Workloads for {vm_name}").classes("text-lg font-bold")
            self.select = ui.select(
                options=all_options,
                multiple=True,
                value=current_workloads,
                label="Select workload types",
            ).classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: self.submit(None))
                ui.button("Apply", on_click=lambda: self.submit(self.select.value))

# Usage in review page:
async def on_row_click(e):
    vm_name = e.args["data"]["vm_name"]
    result = await WorkloadDialog(vm_name, current, options)
    if result is not None:
        # Apply multi-workload with conservative DRR
        update_vm_workloads(vm_name, result)
```

### Pattern 4: Dark Mode Toggle with Storage Persistence
**What:** Bind dark mode to `app.storage.user` so preference persists across sessions.
**When to use:** FR-7.6.
**Example:**
```python
# Source: NiceGUI dark_mode docs + GitHub discussion #5394
from nicegui import app, ui

def add_dark_mode_toggle() -> None:
    """Add dark/light toggle to header, persisted in user storage."""
    dark = ui.dark_mode().bind_value(app.storage.user, "dark_mode")
    ui.switch("Dark Mode").bind_value(app.storage.user, "dark_mode").props(
        "color=white"
    )
```

### Pattern 5: Upload Handler with Pipeline Integration
**What:** Handle file upload event, save to temp file, run ingestion + classification.
**When to use:** Upload page (FR-7.1).
**Example:**
```python
# Source: NiceGUI upload docs + existing pipeline modules
import tempfile
from pathlib import Path
from nicegui import app, ui
from store_predict.pipeline.ingestion import ingest_file
from store_predict.pipeline.classification import classify_dataframe, RuleRegistry, build_default_rules
from store_predict.services.drr_table import DRRTable
from store_predict.config import DRR_CSV_PATH

async def handle_upload(e) -> None:
    """Process uploaded file through ingestion + classification pipeline."""
    with tempfile.NamedTemporaryFile(
        suffix=Path(e.name).suffix, delete=False
    ) as tmp:
        tmp.write(e.content.read())
        tmp_path = Path(tmp.name)
    try:
        df = ingest_file(tmp_path)
        registry = RuleRegistry(build_default_rules())
        df = classify_dataframe(df, registry)
        # Add DRR column
        drr_table = DRRTable.from_csv(DRR_CSV_PATH)
        df["drr"] = df.apply(
            lambda r: drr_table.get_ratio(r["workload_category"], r["workload_subcategory"]),
            axis=1,
        )
        app.storage.tab["vm_data"] = df.to_dict(orient="records")
        ui.notify(f"Loaded {len(df)} VMs", type="positive")
        ui.navigate.to("/review")
    except Exception as exc:
        ui.notify(str(exc), type="negative")
    finally:
        tmp_path.unlink(missing_ok=True)
```

### Anti-Patterns to Avoid
- **Storing pandas DataFrame directly in storage:** NiceGUI storage requires JSON-serializable data. Always use `df.to_dict(orient="records")` and reconstruct with `pd.DataFrame(records)`.
- **Using `app.storage.user` for upload data:** Multiple tabs would overwrite each other. Use `app.storage.tab` for per-session data.
- **Modifying `aggrid.options['rowData']` without calling `aggrid.update()`:** After programmatic changes to rowData, call `aggrid.update()` to refresh the grid.
- **Using AG Grid community multi-select editor:** Does not exist in community edition. Use a dialog instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data grid with sort/filter/pagination | Custom HTML table | `ui.aggrid` | AG Grid handles thousands of rows, virtual scrolling, column resize |
| File upload with drag-and-drop | Custom JS dropzone | `ui.upload` | NiceGUI wraps Quasar uploader with all UX niceties |
| Dark mode CSS | Manual CSS class toggling | `ui.dark_mode()` | Handles Quasar theme + Tailwind dark variant automatically |
| Session state | Custom dict on module-level | `app.storage.tab` | NiceGUI handles multi-user isolation, persistence, cleanup |
| Page routing | Flask-style routing | `@ui.page("/path")` | NiceGUI routing with layout context manager already established |

**Key insight:** NiceGUI wraps Quasar (Vue component library) and AG Grid. Nearly every UI need is covered by an existing component. The main engineering challenge is session state management (DataFrame serialization) and wiring the existing pipeline modules to the UI.

## Common Pitfalls

### Pitfall 1: DataFrame Not Serializable to Storage
**What goes wrong:** Storing a pandas DataFrame in `app.storage.tab` raises a serialization error.
**Why it happens:** NiceGUI storage uses JSON serialization. DataFrames, numpy types, and NaN values are not JSON-serializable.
**How to avoid:** Convert to records with `df.to_dict(orient="records")`. Replace NaN with None: `df.where(df.notna(), None)`.
**Warning signs:** `TypeError: Object of type DataFrame is not JSON serializable`

### Pitfall 2: AG Grid Update Not Reflecting
**What goes wrong:** Changing `aggrid.options['rowData']` in Python does not update the grid visually.
**Why it happens:** AG Grid needs explicit notification of data changes.
**How to avoid:** Call `aggrid.update()` after modifying options, or reassign `aggrid.options['rowData']` and call update.
**Warning signs:** Data appears stale after edits.

### Pitfall 3: Dark Mode Flash on Page Load
**What goes wrong:** Page briefly shows light mode before switching to dark.
**Why it happens:** `app.storage.user` is only available after client connection; initial render uses default.
**How to avoid:** Initialize with `app.storage.user.get('dark_mode', False)` early. Accept minor flash as a known NiceGUI limitation.
**Warning signs:** Brief white flash when navigating to new page in dark mode.

### Pitfall 4: Multi-Select Dialog Closing Unexpectedly
**What goes wrong:** `ui.select(multiple=True)` inside a dialog can cause the dialog to close when clicking options.
**Why it happens:** Known issue (#1108 in NiceGUI repo) where select dropdown click propagates to dialog backdrop.
**How to avoid:** Use `.props('use-chips')` on the select and ensure dialog has `.props('persistent')` to prevent backdrop-close during selection.
**Warning signs:** Dialog closes when user tries to select second workload.

### Pitfall 5: Upload File Content Already Consumed
**What goes wrong:** Calling `e.content.read()` twice returns empty bytes the second time.
**Why it happens:** File-like object cursor is at end after first read.
**How to avoid:** Read once, store bytes. Or use `e.content.seek(0)` before re-reading.
**Warning signs:** Empty DataFrame after seemingly successful upload.

### Pitfall 6: storage_secret Required for User Storage
**What goes wrong:** `app.storage.user` raises error without `storage_secret`.
**Why it happens:** NiceGUI uses the secret for cookie signing.
**How to avoid:** Already set in `main.py`: `ui.run(storage_secret="change-me-in-production")`. Good for dev, needs env var for production.
**Warning signs:** Error about missing storage_secret on first request.

## Code Examples

### Complete Upload Page Structure
```python
# Source: NiceGUI docs + existing layout pattern
from nicegui import app, ui
from store_predict.ui.layout import layout

@ui.page("/upload")
def upload_page() -> None:
    with layout("StorePredict - Upload"):
        with ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6"):
            ui.label("Upload Workload Data").classes("text-3xl font-bold")

            # Project name input
            ui.input(
                label="Project Name",
                placeholder="e.g., Customer-DC-Migration-2026",
                on_change=lambda e: app.storage.tab.update({"project_name": e.value}),
            ).classes("w-full").bind_value(app.storage.tab, "project_name")

            # File upload dropzone
            ui.upload(
                label="Drop RVTools or LiveOptics file here",
                on_upload=handle_upload,
                auto_upload=True,
                max_file_size=50_000_000,  # 50MB
            ).props('accept=".xlsx,.csv"').classes("w-full")
```

### AG Grid Column Definitions with All Features
```python
# Source: AG Grid docs + NiceGUI aggrid wrapper
column_defs = [
    {
        "field": "vm_name",
        "headerName": "VM Name",
        "sortable": True,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "minWidth": 200,
    },
    {
        "field": "os_name",
        "headerName": "OS",
        "sortable": True,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
    },
    {
        "field": "workload_category",
        "headerName": "Workload Category",
        "editable": True,
        "singleClickEdit": True,
        "cellEditor": "agSelectCellEditor",
        "cellEditorParams": {"values": workload_categories},
        "sortable": True,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
    },
    {
        "field": "workload_subcategory",
        "headerName": "Subcategory",
        "sortable": True,
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
    },
    {
        "field": "drr",
        "headerName": "DRR",
        "sortable": True,
        "filter": "agNumberColumnFilter",
        "floatingFilter": True,
        "valueFormatter": "value.toFixed(1)",
    },
    {
        "field": "provisioned_mib",
        "headerName": "Provisioned (MiB)",
        "sortable": True,
        "filter": "agNumberColumnFilter",
        "valueFormatter": "Math.round(value).toLocaleString()",
    },
    {
        "field": "in_use_mib",
        "headerName": "In Use (MiB)",
        "sortable": True,
        "filter": "agNumberColumnFilter",
        "valueFormatter": "Math.round(value).toLocaleString()",
    },
    {
        "field": "classification_confidence",
        "headerName": "Confidence",
        "sortable": True,
        "filter": "agTextColumnFilter",
    },
]
```

### Summary Statistics Binding
```python
# Source: NiceGUI reactive binding pattern
from nicegui import ui

def build_summary_stats(row_data: list[dict]) -> None:
    """Display real-time summary statistics cards."""
    total_vms = len(row_data)
    total_provisioned = sum(r.get("provisioned_mib", 0) for r in row_data)
    avg_drr = (
        sum(r.get("drr", 5.0) for r in row_data) / total_vms
        if total_vms > 0
        else 0
    )
    total_effective = (
        sum(r.get("provisioned_mib", 0) / r.get("drr", 5.0) for r in row_data)
    )

    with ui.row().classes("w-full gap-4"):
        with ui.card().classes("flex-1 p-4"):
            ui.label("Total VMs").classes("text-sm text-gray-500")
            ui.label(str(total_vms)).classes("text-2xl font-bold")
        with ui.card().classes("flex-1 p-4"):
            ui.label("Total Provisioned").classes("text-sm text-gray-500")
            ui.label(f"{total_provisioned / 1024:.1f} GiB").classes("text-2xl font-bold")
        with ui.card().classes("flex-1 p-4"):
            ui.label("Avg DRR").classes("text-sm text-gray-500")
            ui.label(f"{avg_drr:.1f}x").classes("text-2xl font-bold")
        with ui.card().classes("flex-1 p-4"):
            ui.label("Effective Capacity").classes("text-sm text-gray-500")
            ui.label(f"{total_effective / 1024:.1f} GiB").classes("text-2xl font-bold")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AG Grid `rowSelection: 'multiple'` string | `rowSelection: {mode: 'multiRow'}` object | AG Grid 31+ | NiceGUI 3.7 uses newer AG Grid; use object syntax |
| `ui.colors()` for theming | `ui.dark_mode()` with bind | NiceGUI 1.4+ | Clean dark mode API with storage binding |
| Module-level globals for state | `app.storage.tab` / `app.storage.user` | NiceGUI 1.3+ | Proper multi-user state isolation |

**Deprecated/outdated:**
- `rowSelection: 'single'` string syntax: use `rowSelection: {'mode': 'singleRow'}` dict instead
- Direct DataFrame in global variables: breaks with multiple concurrent users

## Open Questions

1. **AG Grid version shipped with NiceGUI 3.7.1**
   - What we know: NiceGUI bundles AG Grid community edition; earlier versions used 30.2.0
   - What's unclear: Exact AG Grid version in 3.7.1 (affects `paginationPageSizeSelector` availability)
   - Recommendation: Test pagination config at runtime; fall back to simple `paginationPageSize` if selector fails

2. **Large file upload handling (>10k VMs)**
   - What we know: AG Grid handles large datasets well with virtual scrolling
   - What's unclear: Whether NiceGUI's storage serialization is fast enough for 50k+ row DataFrames
   - Recommendation: Test with large sample; if slow, consider server-side pagination or chunking

3. **Subcategory dropdown dependency on category**
   - What we know: DRR lookup needs both category and subcategory
   - What's unclear: Best UX for cascading category -> subcategory selection in grid
   - Recommendation: Single-select changes category only, auto-map to first subcategory. Multi-select dialog shows category/subcategory pairs.

## Sources

### Primary (HIGH confidence)
- NiceGUI 3.7.1 installed locally - verified version
- NiceGUI AG Grid docs: https://nicegui.io/documentation/aggrid
- NiceGUI upload docs: https://nicegui.io/documentation/upload
- NiceGUI dark_mode docs: https://nicegui.io/documentation/dark_mode
- NiceGUI storage docs: https://nicegui.io/documentation/storage
- NiceGUI editable AG Grid example: https://github.com/zauberzeug/nicegui/blob/main/examples/editable_ag_grid/main.py
- Existing codebase: main.py, layout.py, upload.py, ingestion.py, classification.py, drr_table.py

### Secondary (MEDIUM confidence)
- AG Grid select cell editor: https://github.com/zauberzeug/nicegui/discussions/675 and #2237
- Dark mode persistence pattern: https://github.com/zauberzeug/nicegui/discussions/5394
- Awaitable dialog pattern: https://daelon.dev/posts/nicegui_dialogs/
- Multi-select dialog issue: https://github.com/zauberzeug/nicegui/issues/1108

### Tertiary (LOW confidence)
- AG Grid version in NiceGUI 3.7.1 (unverified, assumed 31+)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - NiceGUI 3.7.1 verified installed, all components documented
- Architecture: HIGH - Patterns verified against official examples and existing codebase
- Pitfalls: MEDIUM - some based on GitHub issues, may be fixed in 3.7.1
- Session state: HIGH - app.storage API well-documented, serialization pattern standard

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (NiceGUI has frequent releases but API is stable)
