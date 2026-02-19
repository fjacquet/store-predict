# Phase 7: UI Bug Fixes & Report Enhancements - Research

**Researched:** 2026-02-19
**Domain:** NiceGUI AG Grid, ReportLab PDF, LiveOptics performance parsing, classification engine
**Confidence:** HIGH

## Summary

Phase 7 covers four distinct domains: (1) AG Grid interaction bug fixes, (2) PDF report enhancements with VM statistics, (3) LiveOptics performance data parsing and display, and (4) classification improvements including company-prefix stripping and description/annotation field matching.

The codebase is well-structured with clear separation (parsers, classification, calculation, UI components, PDF service). NiceGUI 3.7.1 ships with AG Grid 32.2.2+, which fully supports the `multiRow` selection mode. Filter and pagination state can be preserved using `run_grid_method` to call AG Grid JS APIs. The LiveOptics sample file confirms a "VM Performance" sheet with 35 columns including all IOPS, throughput, and latency metrics needed. RVTools vInfo has an "Annotation" column at position 58 that can be used for classification matching. LiveOptics lacks a direct annotation/notes column on the VMs sheet but has a "Custom Attributes" sheet.

**Primary recommendation:** Fix AG Grid bugs using `run_grid_method` for state preservation, extend `CANONICAL_COLUMNS` with optional performance fields, add a `description` field from RVTools Annotation, and enhance `ClassificationRule.matches()` to accept a third `description` parameter.

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI | 3.7.1 | Web UI framework with AG Grid | Already in use, ships AG Grid 32.2.2+ |
| pandas | (installed) | DataFrame operations | Already powers ingestion/classification |
| ReportLab | (installed) | PDF generation with Platypus | Already generates sizing reports |
| openpyxl | (installed) | Excel file reading | Already parses xlsx files |

### Supporting (no new dependencies needed)
This phase requires NO new library installations. All features can be implemented with the existing stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AG Grid JS API calls | Full grid rebuild | JS API calls are faster and preserve UX state |
| Extending CalculationSummary | New PerformanceSummary dataclass | Extending existing dataclass keeps report API simple |

## Architecture Patterns

### Recommended Changes to Project Structure
```
src/store_predict/
  pipeline/
    parsers/
      columns.py           # ADD: performance column aliases, annotation aliases
      liveoptics.py         # ADD: parse_liveoptics_performance() function
      rvtools.py            # ADD: annotation column extraction
    classification.py       # MODIFY: add description param to matches(), add prefix stripping
    calculation.py          # MODIFY: extend CalculationSummary with VM stats + perf
  services/
    pdf_report.py           # MODIFY: add VM stats section, performance section
  ui/
    components/
      vm_table.py           # MODIFY: fix multi-select, add performance columns, description column
    pages/
      review.py             # MODIFY: preserve filter/page state on updates
  config.py                 # ADD: company prefix patterns config
```

### Pattern 1: AG Grid State Preservation (Filter + Page)
**What:** Save and restore AG Grid filter model and pagination before/after data updates
**When to use:** Every time `grid.update()` is called after modifying row data
**Example:**
```python
# Source: https://github.com/zauberzeug/nicegui/discussions/3311
async def _update_grid_preserving_state(grid: ui.aggrid, row_data: list[dict]) -> None:
    """Update grid row data while preserving filter and page state."""
    # Save current state
    filter_model = await grid.run_grid_method("getFilterModel")
    current_page = await grid.run_grid_method("paginationGetCurrentPage")

    # Update data
    grid.options["rowData"] = row_data
    grid.update()

    # Restore state (do NOT await setFilterModel - it causes timeout)
    grid.run_grid_method("setFilterModel", filter_model)
    if current_page is not None and current_page > 0:
        grid.run_grid_method("paginationGoToPage", current_page)
```

### Pattern 2: Multi-Row Selection Configuration
**What:** Enable checkbox-based multi-row selection in AG Grid
**When to use:** Replace current `singleRow` mode
**Example:**
```python
# Source: https://www.ag-grid.com/javascript-data-grid/row-selection-multi-row/
# NiceGUI 3.7.1 ships AG Grid 32.2.2+ which supports this
grid = ui.aggrid({
    "columnDefs": column_defs,
    "rowData": row_data,
    "rowSelection": {
        "mode": "multiRow",
        "headerCheckbox": True,
        "enableClickSelection": True,
    },
    "pagination": True,
    "paginationPageSize": 50,
})
```

### Pattern 3: Optional Performance Columns with Graceful Fallback
**What:** Extend canonical DataFrame with optional performance columns that default to NaN/0
**When to use:** When performance data may or may not be available (RVTools never has it, LiveOptics CSV never has it)
**Example:**
```python
PERFORMANCE_COLUMNS: list[str] = [
    "peak_iops",
    "avg_iops",
    "peak_throughput_mbs",
    "avg_throughput_mbs",
    "peak_latency_ms",
    "avg_read_latency_ms",
    "avg_write_latency_ms",
    "iops_8k_equivalent",
]

# In parser: if performance data unavailable, fill with NaN
for col in PERFORMANCE_COLUMNS:
    if col not in result.columns:
        result[col] = float("nan")
```

### Pattern 4: Subcategory Selection via Cascading Dropdown
**What:** When user changes workload category via inline edit, show subcategory picker
**When to use:** Cell edit of workload_category column
**Example:**
```python
# After category change, present subcategory options
subcategories = [e for e in drr_table.entries if e.category == new_category]
if len(subcategories) > 1:
    # Show dialog to pick subcategory
    ...
elif len(subcategories) == 1:
    # Auto-select the only subcategory
    subcategory = subcategories[0].subcategory
```

### Anti-Patterns to Avoid
- **Awaiting `setFilterModel`:** Causes JavaScript timeout. Always call without `await`.
- **Rebuilding entire grid on edit:** Loses all state. Use `grid.update()` with state preservation instead.
- **Hardcoding performance column names:** Use alias resolution (same pattern as existing parsers) for robustness.
- **Making performance columns required:** Must be optional -- RVTools and LiveOptics CSV never have them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AG Grid filter persistence | Custom filter tracking | `getFilterModel()`/`setFilterModel()` | AG Grid native API handles all filter types |
| AG Grid page persistence | Page tracking variable | `paginationGetCurrentPage()`/`paginationGoToPage()` | Native API handles edge cases |
| 8K IOPS normalization | Complex custom formula | Standard formula: `IOPS + (throughput_KBps / 8)` | Industry standard for storage sizing |
| Excel column matching | String matching | Existing `resolve_columns()` in columns.py | Already handles aliases and whitespace |

**Key insight:** AG Grid's JavaScript API is fully accessible via `run_grid_method` in NiceGUI. No need to build Python-side state tracking.

## Common Pitfalls

### Pitfall 1: Awaiting setFilterModel Causes Timeout
**What goes wrong:** `await grid.run_grid_method("setFilterModel", fm)` throws a JavaScript timeout error
**Why it happens:** `setFilterModel` returns void/undefined; NiceGUI's await mechanism expects a return value
**How to avoid:** Call without await: `grid.run_grid_method("setFilterModel", fm)`
**Warning signs:** "TimeoutError" or "JavaScript timeout" in console

### Pitfall 2: Multi-Select vs Single-Click Edit Conflict
**What goes wrong:** Multi-row selection and single-click cell editing interfere with each other
**Why it happens:** Both respond to click events on the same row/cell
**How to avoid:** Use row selection checkboxes for multi-select, single-click edit only on the workload_category column. The existing pattern (row click = dialog, cell edit = inline dropdown) already handles this correctly. With `enableClickSelection: true`, clicks on non-editable cells select rows while editable cells enter edit mode.
**Warning signs:** Clicking a row selects it AND opens an editor simultaneously

### Pitfall 3: Performance Data Join Key Mismatch
**What goes wrong:** VM Performance sheet VM names don't match VMs sheet VM names
**Why it happens:** Different sheets may have slight name variations, extra whitespace, or different casing
**How to avoid:** Join on "VM Name" with `.str.strip()` on both sides. Verified from sample: both sheets use "VM Name" as column header. Also consider joining on "MOB ID" which is unique.
**Warning signs:** Many VMs with NaN performance data despite having performance sheet

### Pitfall 4: NaN Performance Values in UI Display
**What goes wrong:** AG Grid shows "NaN" or "undefined" for VMs without performance data
**Why it happens:** Not all VMs have performance data, especially powered-off VMs
**How to avoid:** Use AG Grid `valueFormatter` to show "-" or empty string for NaN values:
```javascript
"valueFormatter": "value != null && !isNaN(value) ? value.toFixed(0) : '-'"
```
**Warning signs:** "NaN" strings visible in the grid

### Pitfall 5: Company Prefix Stripping Over-Matching
**What goes wrong:** Prefix pattern strips legitimate parts of VM names (e.g., "ACME" prefix removes from "ACME-SQL01" but also matches a VM called "ACMEDB")
**Why it happens:** Prefix patterns without delimiter anchoring
**How to avoid:** Require delimiter after prefix (dash, underscore): `r'^ACME[-_]'` not `r'^ACME'`
**Warning signs:** VMs losing important name parts, misclassification increases

### Pitfall 6: Session Data Schema Change
**What goes wrong:** Adding new columns (performance, description) breaks existing sessions
**Why it happens:** Session storage has old schema without new columns
**How to avoid:** When loading session data, fill missing columns with defaults:
```python
for col in PERFORMANCE_COLUMNS + ["description"]:
    if col not in df.columns:
        df[col] = "" if col == "description" else float("nan")
```
**Warning signs:** KeyError when accessing new columns on old session data

## Code Examples

### LiveOptics VM Performance Sheet Columns (Verified from Sample)
```python
# Source: Verified from samples/live-optics.xlsx "VM Performance" sheet
# 35 columns total. Key performance columns:
LIVEOPTICS_PERFORMANCE_ALIASES: dict[str, list[str]] = {
    "vm_name": ["VM Name"],
    "mob_id": ["MOB ID"],
    "peak_iops": ["Peak IOPS"],
    "avg_iops": ["Average IOPS"],
    "avg_rw_ratio": ["Avg Read/Write Ratio"],
    "max_throughput_kbs": ["Max KB/sec"],
    "avg_throughput_kbs": ["Average KB/sec"],
    "peak_read_latency": ["Peak Read Latency"],
    "peak_write_latency": ["Peak Write Latency"],
    "avg_read_latency": ["Avg Read Latency"],
    "avg_write_latency": ["Avg Write Latency"],
    "peak_latency": ["Peak Latency"],
    "peak_read_iops": ["Peak Read IOPS"],
    "peak_write_iops": ["Peak Write IOPS"],
    "avg_read_iops": ["Avg Read IOPS"],
    "avg_write_iops": ["Avg Write IOPS"],
    "peak_read_mbs": ["Peak Read MB/s"],
    "peak_write_mbs": ["Peak Write MB/s"],
    "avg_read_mbs": ["Avg Read MB/s"],
    "avg_write_mbs": ["Avg Write MB/s"],
}
```

### RVTools Annotation Column (Verified from Sample)
```python
# Source: Verified from samples/rvtools.xlsx vInfo sheet, column index 58
# Column name: "Annotation"
# This is the VM description/notes field in RVTools
RVTOOLS_ALIASES_EXTENDED = {
    **RVTOOLS_ALIASES,
    "annotation": ["Annotation"],  # VM description field
}
```

### 8K Equivalent IOPS Calculation
```python
# Standard storage normalization: convert mixed I/O to 8K-equivalent IOPS
# Formula: IOPS + (throughput_in_KBps / 8)
# This normalizes sequential throughput to equivalent random 8K IOPS
def compute_8k_equivalent_iops(
    iops: float,
    throughput_kbs: float,
) -> float:
    """Compute normalized 8K equivalent IOPS.

    Args:
        iops: Raw IOPS count.
        throughput_kbs: Throughput in KB/sec.

    Returns:
        Normalized 8K equivalent IOPS.
    """
    if pd.isna(iops) or pd.isna(throughput_kbs):
        return float("nan")
    return iops + (throughput_kbs / 8.0)
```

### VM Statistics for PDF Report
```python
# Extend CalculationSummary with VM statistics
# These are computed from the row_data list in calculate()
avg_vm_size_mib = total_provisioned / len(vm_calcs) if vm_calcs else 0.0
largest_vm = max(vm_calcs, key=lambda v: v.provisioned_mib) if vm_calcs else None

# Add to PDF report body_style paragraphs:
# f"<b>Average VM Size:</b> {format_storage(avg_vm_size_mib)}"
# f"<b>Largest VM:</b> {largest_vm.vm_name} ({format_storage(largest_vm.provisioned_mib)})"
```

### Company Prefix Configuration
```python
# In config.py -- configurable company name patterns
# Users set these to ignore company prefixes during classification
COMPANY_PREFIX_PATTERNS: list[str] = []
# Example: ["ACME-", "CORP-", "OIK_"]
# These are stripped from VM names BEFORE pattern matching
# Delimiter-anchored: "OIK_" matches "OIK_SQL01" -> "SQL01"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `rowSelection: "multiple"` | `rowSelection: { mode: "multiRow" }` | AG Grid 32.2.0 | Object-based config required for NiceGUI 3.x |
| Full grid rebuild on data change | `grid.update()` + state restoration | NiceGUI 2.x+ | Preserves user context (filters, page, selection) |
| Single field classification | Multi-field classification (name + OS + description) | Phase 7 | Better accuracy with annotation data |

**Deprecated/outdated:**
- `rowSelection: "multiple"` string syntax: Replaced by object syntax `{ mode: "multiRow" }` in AG Grid 32+. NiceGUI 3.7.1 uses the new API.

## LiveOptics Performance Data: Verified Column Schema

**Source:** `samples/live-optics.xlsx`, "VM Performance" sheet (35 columns)

| Column Name | Type | Description |
|-------------|------|-------------|
| VM Name | str | Join key to VMs sheet |
| MOB ID | str | Alternate join key (unique) |
| Host | str | ESXi host |
| Datacenter | str | vCenter datacenter |
| Cluster | str | Cluster name |
| VM IO Classification | str | LiveOptics IO classification |
| Peak IOPS | float | Peak total IOPS |
| Average IOPS | float | Average total IOPS |
| Max KB/sec | float | Peak throughput in KB/s |
| Average KB/sec | float | Average throughput in KB/s |
| Peak Read Latency | float | Peak read latency (ms) |
| Peak Write Latency | float | Peak write latency (ms) |
| Avg Read Latency | float | Average read latency (ms) |
| Avg Write Latency | float | Average write latency (ms) |
| Peak Latency | float | Peak combined latency (ms) |
| Peak Read IOPS | float | Peak read IOPS |
| Peak Write IOPS | float | Peak write IOPS |
| Avg Read IOPS | float | Average read IOPS |
| Avg Write IOPS | float | Average write IOPS |
| Peak Read MB/s | float | Peak read throughput MB/s |
| Peak Write MB/s | float | Peak write throughput MB/s |
| Avg Read MB/s | float | Average read throughput MB/s |
| Avg Write MB/s | float | Average write throughput MB/s |

**Join strategy:** Use "VM Name" as primary join key (present in both VMs and VM Performance sheets). Fall back to "MOB ID" if VM Name has duplicates.

## RVTools Annotation Field: Verified

**Source:** `samples/rvtools.xlsx`, vInfo sheet, column index 58

- Column name: `Annotation`
- Contains free-text VM descriptions/notes entered by admins
- Can include workload hints (e.g., "SQL Server production", "Exchange mailbox")
- LiveOptics has NO equivalent annotation column in VMs sheet
- LiveOptics "Custom Attributes" sheet has backup metadata (not useful for classification)

## Open Questions

1. **8K Equivalent IOPS Formula Precision**
   - What we know: Standard formula is `IOPS + (throughput_KBps / 8)` for 8K block normalization
   - What's unclear: Dell PowerSizer may use a slightly different formula for PowerStore-specific sizing
   - Recommendation: Use the standard formula; document it in the report as "estimated 8K equivalent IOPS" with a note that PowerSizer should be used for final sizing

2. **Company Prefix Pattern Storage**
   - What we know: Needs to be configurable per-project
   - What's unclear: Should it be stored in config.py (global), session storage (per-upload), or a separate config file?
   - Recommendation: Store in `config.py` as a module-level list, allow override via environment variable. Can be moved to per-project config in a future phase.

3. **Multi-Row Selection UX with Row Click Dialog**
   - What we know: Current design uses row click for workload dialog, which conflicts with multi-row selection
   - What's unclear: Should multi-select trigger a batch workload dialog, or should selection be separate from editing?
   - Recommendation: Use checkboxes for selection (separate from click). Add a "Batch Edit" button that opens dialog for selected rows. Single row click still opens individual dialog.

## Sources

### Primary (HIGH confidence)
- `samples/live-optics.xlsx` - Verified VM Performance sheet columns (35 columns)
- `samples/rvtools.xlsx` - Verified vInfo Annotation column (position 58, 70 total columns)
- NiceGUI 3.7.1 installed version - Confirmed AG Grid 32.2.2+ support
- [NiceGUI AG Grid Issue #3854](https://github.com/zauberzeug/nicegui/issues/3854) - multiRow selection fix confirmed
- [NiceGUI Discussion #3311](https://github.com/zauberzeug/nicegui/discussions/3311) - getFilterModel/setFilterModel usage

### Secondary (MEDIUM confidence)
- [AG Grid Multi-Row Selection Docs](https://www.ag-grid.com/javascript-data-grid/row-selection-multi-row/) - Official AG Grid docs
- [AG Grid Filter API Docs](https://www.ag-grid.com/javascript-data-grid/filter-api/) - getFilterModel/setFilterModel
- [AG Grid Pagination Docs](https://www.ag-grid.com/javascript-data-grid/row-pagination/) - paginationGetCurrentPage/paginationGoToPage
- [LiveOptics VM Performance Data](https://support.liveoptics.com/hc/en-us/articles/360060070213-Optical-Prime-VM-Performance-Data) - Column definitions
- [LiveOptics Excel Field Definitions](https://support.liveoptics.com/hc/en-us/articles/1260802114709-Optical-Prime-VMware-Excel-Field-Definitions) - Field documentation

### Tertiary (LOW confidence)
- 8K equivalent IOPS formula - Industry standard but not Dell-officially documented for PowerStore specifically

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, no new dependencies
- AG Grid bugs: HIGH - Verified NiceGUI version, AG Grid API, and exact code patterns
- LiveOptics performance parsing: HIGH - Verified exact columns from real sample file
- RVTools annotation: HIGH - Verified exact column name and position from real sample file
- Classification improvements: HIGH - Clear extension points in existing code
- 8K IOPS formula: MEDIUM - Standard formula but not PowerStore-specific validated
- PDF report enhancements: HIGH - Clear extension of existing ReportLab Platypus patterns

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain, no fast-moving dependencies)
