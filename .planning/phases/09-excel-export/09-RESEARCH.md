# Phase 9: Excel Export - Research

**Researched:** 2026-02-20
**Domain:** XlsxWriter, NiceGUI download pattern, Python service layer, i18n
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| XLSX-01 | Download Excel button on report page exports .xlsx file | NiceGUI `ui.download(bytes, filename)` pattern mirrors existing PDF download — verified working |
| XLSX-02 | Excel workbook contains Summary sheet with capacity/performance metrics | `CalculationSummary` dataclass exposes all needed fields; `write()` method for label-value rows |
| XLSX-03 | Excel workbook contains Workload Breakdown sheet with per-category aggregations | `summary.workload_groups` list of `WorkloadGroupResult` — mirrors PDF workload table |
| XLSX-04 | Excel workbook contains VM Detail sheet with all VMs, workloads, and DRR values | `summary.vm_calculations` list of `VMCalculation` — all fields available |
| XLSX-05 | Excel sheets have styled headers, auto-sized columns, and frozen header rows | `add_format()`, `worksheet.autofit()`, `freeze_panes(1, 0)` all verified working |
</phase_requirements>

---

## Summary

Phase 9 adds an Excel export service parallel to the existing PDF service. XlsxWriter 3.2.9 is already installed (confirmed by `pyproject.toml` and runtime check). The library generates write-only `.xlsx` workbooks in memory via `BytesIO`, which maps directly to the existing `ui.download(bytes, filename)` pattern used for PDF.

The three-sheet workbook (Summary, Workload Breakdown, VM Detail) maps naturally to the existing `CalculationSummary` dataclass. All data is already computed by the calculation pipeline — no new pipeline logic is needed. The service module follows the same structure as `services/pdf_report.py`: pure function, `BytesIO` in/bytes out, i18n via `t()`, locale-aware.

XlsxWriter has no bundled type stubs (`py.typed` absent), so a `[[tool.mypy.overrides]]` entry with `ignore_missing_imports = true` is required — identical to the existing pattern for `reportlab` and `i18n`. The `in_memory: True` workbook option eliminates temp-file creation and is the correct pattern for a web context.

**Primary recommendation:** Implement `services/excel_report.py` as a single `generate_report_xlsx(summary, project_name, locale) -> bytes` function following the pdf_report.py shape; wire a second download button in `report.py` alongside the existing PDF button.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| xlsxwriter | 3.2.9 (installed) | Write-only .xlsx generation | Already in pyproject.toml dependencies; write-only design is simpler and more reliable than openpyxl for generation |
| io.BytesIO | stdlib | In-memory file buffer | Zero disk I/O; matches existing PDF pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| store_predict.i18n.t | local | All user-facing strings | Every header label, sheet name, metric label |
| store_predict.i18n.locale.get_locale | local | Current tab locale | Pass as `locale` param, set `i18n.set("locale", locale)` before t() calls |
| store_predict.pipeline.calculation.CalculationSummary | local | Data source | Sole input to the generator function |
| store_predict.services.pdf_report.sanitize_filename | local | Safe filename | Reuse existing helper, no new implementation needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| xlsxwriter | openpyxl | openpyxl can read/modify; xlsxwriter is write-only but produces smaller files with richer format API. Since the decision is locked to xlsxwriter, do not use openpyxl |
| xlsxwriter | pandas ExcelWriter | pandas adds no value here — all data is already structured in Python dataclasses |

**Installation:** Already installed. No action needed. `xlsxwriter>=3.2.9` is in `[project] dependencies`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/
├── services/
│   ├── pdf_report.py          # existing
│   └── excel_report.py        # NEW — mirrors pdf_report.py shape
└── ui/
    └── pages/
        └── report.py          # MODIFY — add Download Excel button + handler
```

### Pattern 1: Service Module Shape (mirrors pdf_report.py)

**What:** Pure function accepting `CalculationSummary`, returning `bytes`. No UI imports.
**When to use:** All report generation logic.

```python
# Source: mirrors src/store_predict/services/pdf_report.py pattern
from __future__ import annotations

import i18n as _i18n
from io import BytesIO
from typing import TYPE_CHECKING

import xlsxwriter

from store_predict.i18n import t

if TYPE_CHECKING:
    from store_predict.pipeline.calculation import CalculationSummary

__all__ = ["generate_report_xlsx"]

_BRAND_BLUE = "#1e3a5f"
_BRAND_WHITE = "#FFFFFF"


def generate_report_xlsx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
) -> bytes:
    _i18n.set("locale", locale)

    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})

    # formats
    header_fmt = wb.add_format({
        "bold": True,
        "bg_color": _BRAND_BLUE,
        "font_color": _BRAND_WHITE,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    bold_fmt = wb.add_format({"bold": True})
    number_fmt = wb.add_format({"num_format": "0.0", "align": "right"})
    gib_fmt = wb.add_format({"num_format": '0.00 "GiB"', "align": "right"})

    _write_summary_sheet(wb, summary, header_fmt, bold_fmt, gib_fmt, number_fmt)
    _write_breakdown_sheet(wb, summary, header_fmt, number_fmt, gib_fmt)
    _write_vm_detail_sheet(wb, summary, header_fmt, number_fmt, gib_fmt)

    wb.close()
    return buf.getvalue()
```

### Pattern 2: Worksheet Builder Helper

**What:** Private `_write_*_sheet()` helpers, one per sheet.
**When to use:** Keep the main function under 30 lines; each sheet is isolated.

```python
def _write_summary_sheet(wb, summary, header_fmt, bold_fmt, gib_fmt, number_fmt):
    # Source: XlsxWriter docs — xlsxwriter.readthedocs.io/worksheet.html
    ws = wb.add_worksheet(t("excel.sheet_summary"))
    ws.write(0, 0, t("excel.col_metric"), header_fmt)
    ws.write(0, 1, t("excel.col_value"), header_fmt)

    row = 1
    metrics = [
        (t("pdf.total_vms"), summary.total_vms),
        (t("pdf.total_cpus"), summary.total_cpus),
        # ... etc
    ]
    for label, value in metrics:
        ws.write(row, 0, label, bold_fmt)
        ws.write(row, 1, value)
        row += 1

    ws.freeze_panes(1, 0)
    ws.autofit()
```

### Pattern 3: BytesIO + ui.download (NiceGUI integration)

**What:** Generate bytes, pass directly to `ui.download()`.
**When to use:** Report page download handler.

```python
# Source: mirrors existing _on_download in src/store_predict/ui/pages/report.py
def _on_download_excel(summary: object, project_name: str) -> None:
    from store_predict.pipeline.calculation import CalculationSummary
    assert isinstance(summary, CalculationSummary)
    xlsx_bytes = generate_report_xlsx(summary, project_name, locale=get_locale())
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    filename = f"StorePredict_{safe_name}_{date_str}.xlsx"
    ui.download(xlsx_bytes, filename=filename,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
```

### Pattern 4: Locale handling in service

**What:** Set `i18n.set("locale", locale)` at function entry — identical to `generate_report_pdf`.
**Why:** `t()` reads global locale state. Service functions are synchronous; no coroutine interleaving risk.

```python
def generate_report_xlsx(summary, project_name, locale="fr"):
    _i18n.set("locale", locale)   # Must be first, before any t() calls
    ...
```

### Anti-Patterns to Avoid

- **Calling `buf.read()` after `wb.close()`:** `read()` returns empty bytes because the cursor is at end of file. Use `buf.getvalue()` which ignores the cursor position — confirmed in XlsxWriter HTTP server example (`output.seek(0)` then `output.read()` is equivalent but `getvalue()` is cleaner).
- **Not setting `in_memory: True`:** Without this option, XlsxWriter writes temporary files to disk in a web context. Always pass `{"in_memory": True}` to `Workbook(buf, ...)`.
- **Calling `wb.close()` and then writing more data:** XlsxWriter is write-only and finalized on close. Build all sheets before calling `wb.close()`.
- **Reusing format objects across workbooks:** Each format is bound to its workbook instance. Create formats after `Workbook()`.
- **Using `autofit()` before writing data:** Call `worksheet.autofit()` AFTER writing all data — it calculates widths based on cell contents at call time.
- **Importing `xlsxwriter` types without mypy override:** xlsxwriter has no `py.typed` — mypy strict mode will fail without `ignore_missing_imports = true` in `pyproject.toml`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column width calculation | Custom string-width measurement | `worksheet.autofit()` | XlsxWriter uses Excel-calibrated font metrics; custom calculation will be wrong for non-ASCII (French) text |
| Frozen header rows | Manual row tracking | `worksheet.freeze_panes(1, 0)` | Built-in, one line |
| Header styling | CSS-like dict building | `wb.add_format({...})` | Format reuse across cells is free; XlsxWriter deduplicates internally |
| Number formatting | String formatting in Python before write | XlsxWriter `num_format` | Native number format lets Excel recalculate; formatted strings lose numeric type |
| In-memory file | Temp file + cleanup | `BytesIO` + `in_memory: True` | No disk I/O, no cleanup, no race conditions |
| Filename sanitization | New implementation | `sanitize_filename()` from `pdf_report.py` | Already tested, reuse via import |

**Key insight:** XlsxWriter's format + autofit + freeze_panes API handles every Excel "polish" requirement in this phase. Nothing needs to be hand-rolled.

---

## Common Pitfalls

### Pitfall 1: `buf.read()` returns empty bytes

**What goes wrong:** `wb.close()` leaves the BytesIO cursor at end-of-file. Calling `buf.read()` returns `b""`.
**Why it happens:** `write()` advances the cursor position; `read()` reads from current position.
**How to avoid:** Use `buf.getvalue()` (reads all regardless of position). If using `buf.read()`, call `buf.seek(0)` first.
**Warning signs:** `ui.download` triggers but downloaded file is 0 bytes or corrupted.

### Pitfall 2: Missing mypy override for xlsxwriter

**What goes wrong:** `mypy src/` fails with `Skipping analyzing "xlsxwriter": module is installed, but missing library stubs or py.typed marker [import-untyped]`.
**Why it happens:** xlsxwriter 3.2.9 ships no `py.typed` file and no bundled `.pyi` stubs.
**How to avoid:** Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = "xlsxwriter.*"
ignore_missing_imports = true
```
**Warning signs:** `mypy` CI step fails after adding the import.

### Pitfall 3: `worksheet.autofit()` called before data written

**What goes wrong:** Columns get minimum default width because no cells have content yet.
**Why it happens:** `autofit()` calculates widths from current cell contents at call time.
**How to avoid:** Call `ws.autofit()` as the LAST operation on each worksheet, after all `ws.write()` calls.
**Warning signs:** Columns appear truncated despite long strings in cells.

### Pitfall 4: t() locale not set in service context

**What goes wrong:** All labels render in English even when UI locale is French.
**Why it happens:** `t()` reads the `i18n` global locale. Service functions called from event handlers inherit whatever locale was last set.
**How to avoid:** Mirror `pdf_report.py`: call `_i18n.set("locale", locale)` at the top of `generate_report_xlsx()` before any `t()` invocation.
**Warning signs:** French users see English column headers in the downloaded file.

### Pitfall 5: Performance data section written unconditionally

**What goes wrong:** Summary sheet shows empty IOPS/throughput rows (zeros) for RVTools uploads that have no performance data.
**Why it happens:** `summary.has_performance_data` is False for RVTools files; the fields exist but are 0.
**How to avoid:** Guard the performance metric rows with `if summary.has_performance_data:` — same conditional used in `report.py` and `pdf_report.py`.
**Warning signs:** Summary sheet always shows "Total Avg IOPS: 0" for non-LiveOptics files.

### Pitfall 6: Sheet name length limit

**What goes wrong:** `xlsxwriter.exceptions.InvalidWorksheetName` raised if sheet name exceeds 31 characters.
**Why it happens:** Excel spec limits sheet tab names to 31 characters.
**How to avoid:** Keep translated sheet names under 31 chars. French i18n keys must be validated: "Détail par VM" (14 chars) is safe; "Détail des machines virtuelles" (30 chars) is at the limit.
**Warning signs:** Exception on `wb.add_worksheet(t("excel.sheet_vm_detail"))` in French locale.

---

## Code Examples

Verified patterns from official sources and local runtime tests:

### Full BytesIO Workbook Pattern

```python
# Source: https://xlsxwriter.readthedocs.io/example_http_server.html (verified)
# Locally validated: generates 5,517-byte valid PK ZIP on test run
from io import BytesIO
import xlsxwriter

buf = BytesIO()
wb = xlsxwriter.Workbook(buf, {"in_memory": True})
ws = wb.add_worksheet("Sheet 1")
ws.write(0, 0, "Hello")
wb.close()
xlsx_bytes = buf.getvalue()   # NOT buf.read()
```

### Header Format (Brand Colors)

```python
# Source: https://xlsxwriter.readthedocs.io/format.html (verified)
# Brand color #1e3a5f matches existing PDF brand color in pdf_report.py
header_fmt = wb.add_format({
    "bold": True,
    "bg_color": "#1e3a5f",
    "font_color": "#FFFFFF",
    "border": 1,
    "align": "center",
    "valign": "vcenter",
})
```

### Freeze Header Row + Autofit

```python
# Source: https://xlsxwriter.readthedocs.io/worksheet.html (verified)
# freeze_panes(row, col): rows 0..row-1 and cols 0..col-1 are frozen
ws.freeze_panes(1, 0)  # freeze row 0 (header); no column freeze
ws.autofit()           # call AFTER all writes
```

### write_row for Header

```python
# Source: https://xlsxwriter.readthedocs.io/worksheet.html (verified)
headers = [t("excel.col_vm_name"), t("excel.col_workload"), t("excel.col_drr"),
           t("excel.col_provisioned_gib"), t("excel.col_required_gib")]
ws.write_row(0, 0, headers, header_fmt)
```

### NiceGUI Download Button (mirrors existing PDF button)

```python
# Source: src/store_predict/ui/pages/report.py (existing, verified)
ui.button(
    t("report.download_excel"),
    on_click=lambda: _on_download_excel(summary, project_name),
    icon="table_view",
).classes("bg-green-700 text-white")
```

### Number Formatting (native Excel format)

```python
# Source: https://xlsxwriter.readthedocs.io/format.html
gib_fmt = wb.add_format({"num_format": "0.00", "align": "right"})
# Write numeric value, not pre-formatted string, so Excel can recalculate
ws.write(row, col, summary.total_provisioned_mib / 1024, gib_fmt)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `set_column(col, col, width)` manual width | `worksheet.autofit()` | XlsxWriter 3.0.6 | Eliminates manual width estimation per column |
| `BytesIO` with explicit `seek(0)` + `read()` | `buf.getvalue()` (no seek needed) | Always valid | `getvalue()` is simpler and more explicit |
| `openpyxl` for styled xlsx generation | `xlsxwriter` for write-only generation | Project decision | xlsxwriter API is simpler for generation; openpyxl needed only if reading back |

**Deprecated/outdated:**
- `xlsxwriter.Workbook(filename)` with temp files: use `BytesIO` + `in_memory: True` in web context.

---

## Open Questions

1. **Sheet name i18n key character count**
   - What we know: Excel 31-char sheet name limit; French translations tend to be longer than English
   - What's unclear: The exact French translation for "VM Detail" and "Workload Breakdown" sheet tabs
   - Recommendation: Keep sheet tab names short (e.g., "Résumé", "Répartition", "Détail VMs") — verify all under 31 chars during i18n key creation

2. **GiB vs MiB column values**
   - What we know: UI displays GiB; `CalculationSummary` stores MiB; PDF divides by 1024 for display
   - What's unclear: Whether the Excel export should store raw MiB (better for downstream sorting/calculation) or pre-converted GiB
   - Recommendation: Store GiB (divide by 1024) for consistency with PDF and user mental model; use `num_format: "0.00"` so Excel treats as numeric

3. **Column unit annotation in headers**
   - What we know: PDF headers say "Provisioned (GiB)"; i18n key `pdf.table_provisioned` = "Provisioned (GiB)"
   - What's unclear: Whether to reuse `pdf.*` i18n keys or create new `excel.*` keys
   - Recommendation: Create new `excel.*` namespace keys for clarity; reuse value strings where identical

---

## Sources

### Primary (HIGH confidence)

- XlsxWriter official docs — https://xlsxwriter.readthedocs.io/workbook.html — Workbook BytesIO, in_memory option, close()
- XlsxWriter worksheet docs — https://xlsxwriter.readthedocs.io/worksheet.html — write, write_row, freeze_panes, autofit, set_column
- XlsxWriter format docs — https://xlsxwriter.readthedocs.io/format.html — add_format() dict syntax, bold, bg_color, font_color, border, align, num_format
- XlsxWriter HTTP server example — https://xlsxwriter.readthedocs.io/example_http_server.html — BytesIO + in_memory + seek(0) pattern
- XlsxWriter autofit example — https://xlsxwriter.readthedocs.io/example_autofit.html — autofit() after writes
- Local runtime validation — `python -c "import xlsxwriter; print(xlsxwriter.__version__)"` → `3.2.9`; full multi-sheet BytesIO workbook generated and verified (`b'PK\x03\x04'` magic)

### Secondary (MEDIUM confidence)

- NiceGUI `ui.download` WebSearch (confirmed against nicegui.io/documentation/download): accepts `bytes` directly; `media_type` param available; pattern mirrors existing PDF download in `report.py`
- mypy strict mode test: confirmed `[import-untyped]` error without override; `ignore_missing_imports = true` resolves it

### Tertiary (LOW confidence)

- WebSearch on BytesIO `seek(0)` vs `getvalue()`: confirmed by runtime test that `getvalue()` works without seek; `seek(0)` + `read()` is equivalent but unnecessary

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — xlsxwriter 3.2.9 is already installed; API verified via official docs and local runtime test
- Architecture: HIGH — mirrors existing `pdf_report.py` shape exactly; no new patterns required
- Pitfalls: HIGH — BytesIO cursor pitfall verified by runtime; mypy override verified by mypy execution; locale pattern copied from existing pdf_report.py
- i18n integration: HIGH — existing `t()` and `_i18n.set("locale", locale)` pattern from pdf_report.py applies directly

**Research date:** 2026-02-20
**Valid until:** 2026-05-20 (stable library, 90-day estimate)
