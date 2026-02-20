# Phase 9: Excel Export - Research

**Researched:** 2026-02-20
**Domain:** XlsxWriter, NiceGUI download pattern, Python service layer, i18n
**Confidence:** HIGH

## Summary

Phase 9 adds an Excel export service parallel to the existing PDF service. XlsxWriter 3.2.9 is already installed and declared in `pyproject.toml`. The library generates write-only `.xlsx` workbooks in memory via `BytesIO`, which maps directly to the existing `ui.download(bytes, filename)` pattern used for PDF. All data needed for the three-sheet workbook is already present in the `CalculationSummary` dataclass — no new pipeline logic is required.

## Key Findings

### BytesIO + in_memory: True

Always pass `{"in_memory": True}` to `xlsxwriter.Workbook()` when targeting a web context. Without it, XlsxWriter writes temporary files to disk. Retrieve bytes with `buf.getvalue()` (not `buf.read()`) after `wb.close()` — `read()` returns empty bytes because the cursor is at end-of-file.

```python
buf = io.BytesIO()
wb = xlsxwriter.Workbook(buf, {"in_memory": True})
# ... build sheets ...
wb.close()
return buf.getvalue()   # correct; buf.read() would return b""
```

### Service Module Shape Mirrors pdf_report.py

`generate_report_xlsx(summary, project_name, locale)` is a pure function — no UI imports. Set `i18n.set("locale", locale)` at function entry, identical to `generate_report_pdf`. This is safe because the function is synchronous and there is no coroutine interleaving risk.

### Private Sheet Builder Helpers

Split sheet construction into private `_write_*_sheet()` helpers to keep the main function under 30 lines and isolate each sheet's logic.

```python
def _write_summary_sheet(wb, summary, header_fmt, bold_fmt, gib_fmt, number_fmt):
    ws = wb.add_worksheet(t("excel.sheet_summary"))
    ws.freeze_panes(1, 0)      # freeze header row
    ws.autofit()               # call AFTER writing all data
```

Call `ws.autofit()` after writing all data — it calculates column widths from cell contents at call time.

### NiceGUI Download Integration

Pass bytes directly to `ui.download()` with the correct MIME type. Mirrors `_on_download` for PDF on the same report page.

```python
def _on_download_excel(summary, project_name):
    xlsx_bytes = generate_report_xlsx(summary, project_name, locale=get_locale())
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    ui.download(
        xlsx_bytes,
        filename=f"StorePredict_{safe_name}_{date_str}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

### Workbook Structure

Three sheets map directly to existing dataclass fields:

| Sheet | Data source |
|-------|-------------|
| Summary | `summary.total_vms`, `summary.total_provisioned_gib`, etc. |
| Workload Breakdown | `summary.workload_groups` — list of `WorkloadGroupResult` |
| VM Detail | `summary.vm_calculations` — list of `VMCalculation` |

### mypy Override Required

XlsxWriter has no `py.typed` marker. Add an override in `pyproject.toml` identical to the existing entries for `reportlab` and `i18n`:

```toml
[[tool.mypy.overrides]]
module = "xlsxwriter.*"
ignore_missing_imports = true
```

## Anti-Patterns

- **Calling `buf.read()` instead of `buf.getvalue()`:** After `wb.close()` the BytesIO cursor is at EOF. `buf.read()` returns `b""`. Always use `buf.getvalue()`.
- **Omitting `in_memory: True`:** Without this option, XlsxWriter creates temp files on disk — wrong for a web context.
- **Calling `autofit()` before writing data:** Column widths are calculated from contents at call time. Call it as the last step per sheet.

## Dependencies

No new dependencies. `xlsxwriter>=3.2.9` is already in `[project] dependencies`. No `uv pip install` needed.
