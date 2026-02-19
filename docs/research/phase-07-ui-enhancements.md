# Phase 7: UI Bug Fixes & Report Enhancements - Research

**Researched:** 2026-02-19
**Domain:** NiceGUI AG Grid, ReportLab PDF, LiveOptics performance parsing, DRR editing
**Confidence:** HIGH

## Summary

Phase 7 addressed critical AG Grid rendering issues, enhanced the report with performance metrics and CPU/memory data, fixed the 8K IOPS normalization formula, and added bulk workload editing capabilities.

## Key Findings

### NiceGUI AG Grid `:` Prefix Convention

NiceGUI requires a `:` prefix on AG Grid properties that contain JavaScript functions. Without it, strings are passed literally instead of being evaluated as JS. This was the root cause of the "No Rows To Show" bug.

```python
# Wrong — string passed literally, AG Grid crashes
"getRowId": "params => params.data.vm_name"

# Correct — evaluated as JavaScript function
":getRowId": "params => params.data.vm_name"
```

This applies to all JS function properties: `getRowId`, `valueFormatter`, `valueGetter`, etc.

### NaN Serialization Chain

pandas NaN values break JSON serialization. The fix chain:
1. `df.where(notna, "")` produces empty strings that break `float("")` downstream
2. Correct approach: dict post-processing with `val != val` identity check → `None`

### 8K IOPS Normalization

The original formula `avg_iops + (throughput_KB/s / 8)` double-counts IO activity since throughput already captures all IOPS. Correct formula: `throughput_KB/s / 8.0`.

### Peak IOPS Aggregation

Summing peak IOPS across all VMs is meaningless — peaks don't coincide. For storage sizing, show:
- **Total Average IOPS** (sum of averages — valid steady-state)
- **Hottest VM Peak IOPS** (single VM max — burst reference)

### AG Grid Selection

AG Grid 34.2.0 (bundled with NiceGUI 3.7.1) uses object syntax for `rowSelection`. To make header checkbox select only filtered rows: `selectAll: "filtered"`.

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| DRR editing | Editable column with min 0.1 | Pre-sales needs custom overrides |
| Peak IOPS display | Hottest VM, not sum | Sum of peaks is statistically meaningless |
| Report layout | Totals then Averages sections | Clearer grouping for pre-sales readability |
| Bulk update | Checkbox + dialog | Multi-select without bulk action is useless |
| 8K formula | throughput/8 only | Previous formula double-counted IOPS |

## Dependencies

No new dependencies. All features implemented with existing stack (NiceGUI, pandas, ReportLab, openpyxl).
