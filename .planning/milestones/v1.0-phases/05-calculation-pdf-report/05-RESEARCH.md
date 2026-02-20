# Phase 5: Calculation & PDF Report - Research

**Researched:** 2026-02-19
**Domain:** Capacity calculation engine + PDF report generation (ReportLab)
**Confidence:** HIGH

## Summary

Phase 5 completes the StorePredict pipeline by adding a calculation service that computes per-VM required capacity and workload-grouped totals, a report page displaying summary cards and breakdown tables, and a one-page PDF export using ReportLab. The codebase already has all prerequisites in place: session state stores classified VM data with DRR values (`app.storage.tab["vm_data"]`), `DRRTable` provides ratio lookups, and the UI architecture uses a context-manager layout pattern with NiceGUI.

ReportLab 4.4.10 is already installed and declared in `pyproject.toml`. It ships with Bitstream Vera TTF fonts that fully support French characters (accents, special chars). The Platypus high-level framework (`SimpleDocTemplate`, `Table`, `Paragraph`) is the correct approach for the one-page report -- it handles content flow, table rendering, and font embedding automatically.

NiceGUI provides `ui.download.content(bytes_data, filename)` for triggering browser downloads of in-memory content, which is the ideal mechanism for serving generated PDFs without writing to disk.

**Primary recommendation:** Build a pure-pipeline `CalculationService` class (no UI dependency) that takes classified VM row dicts and returns structured results, then a separate `PDFReportGenerator` that takes calculation results and produces PDF bytes in memory using ReportLab Platypus with Vera fonts.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FR-5.1 | Per-VM required capacity: `required_mib = provisioned_mib / drr` | Simple arithmetic on row dicts; calculation service iterates rows |
| FR-5.2 | Totals: total_provisioned, total_in_use, total_required, weighted_average_drr | Aggregate sums over row dicts; weighted avg = total_provisioned / total_required |
| FR-5.3 | Group results by workload category with subtotals | `itertools.groupby` or dict accumulation on `workload_category` field |
| FR-5.4 | Display results in summary cards and breakdown table | Reuse existing `build_summary_stats` pattern + NiceGUI `ui.table` or AG Grid |
| FR-6.1 | One-page PDF with StorePredict branding | ReportLab `SimpleDocTemplate` with custom `onFirstPage` callback for branding |
| FR-6.2 | Include project name, date, total VMs, provisioned, weighted avg DRR, required | Header section drawn via canvas in `onFirstPage` callback |
| FR-6.3 | Workload breakdown table in PDF | ReportLab `Table` + `TableStyle` with header row styling |
| FR-6.4 | French character support | Vera TTF fonts (bundled with ReportLab) support full Latin-1+ Unicode |
| FR-6.5 | Download from report page | `ui.download.content(pdf_bytes, 'report.pdf', media_type='application/pdf')` |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| reportlab | 4.4.10 (installed) | PDF generation | Industry-standard Python PDF toolkit; already a project dependency |
| pandas | >=2.2 (installed) | Data aggregation for calculations | Already used throughout pipeline |
| nicegui | >=3.4 (installed) | Report page UI + download trigger | Already the project UI framework |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| reportlab.platypus | (part of reportlab) | High-level document builder | For structured PDF with tables and paragraphs |
| reportlab.pdfbase.ttfonts | (part of reportlab) | TTF font registration | For Vera font (French character support) |
| reportlab.lib.colors | (part of reportlab) | Color definitions for table styling | For branded table headers |
| io.BytesIO | stdlib | In-memory PDF buffer | Avoid temp files for PDF generation |
| datetime | stdlib | Report date stamp | For FR-6.2 date field |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ReportLab Platypus | ReportLab pdfgen Canvas (low-level) | Canvas gives pixel control but requires manual layout; Platypus handles content flow automatically |
| Vera (bundled) | DejaVu Sans (external TTF) | DejaVu has broader Unicode but requires downloading/bundling; Vera covers French chars and ships with ReportLab |
| WeasyPrint | HTML-to-PDF | Heavier dependency (requires system libs); ReportLab already installed and proven |
| ui.download.content | Serve static file via endpoint | Content approach is simpler, no disk I/O needed |

**Installation:** No new dependencies required. All libraries already declared in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/
  pipeline/
    calculation.py          # NEW: CalculationService (pure data, no UI)
  services/
    drr_table.py            # EXISTING: DRR lookup
    pdf_report.py           # NEW: PDFReportGenerator (ReportLab)
  ui/
    pages/
      report.py             # NEW: Report page (summary + download button)
    components/
      summary_stats.py      # EXISTING: Reusable summary cards
```

### Pattern 1: Calculation Service (Pure Pipeline)

**What:** A stateless class that takes row dicts (from session state) and returns structured calculation results as dataclasses.
**When to use:** Always -- keeps calculation logic testable without UI.
**Example:**

```python
# Source: Project convention (pipeline has zero imports from UI)
from dataclasses import dataclass

@dataclass(frozen=True)
class VMCalculation:
    """Per-VM calculation result."""
    vm_name: str
    workload_category: str
    provisioned_mib: float
    in_use_mib: float
    drr: float
    required_mib: float  # = provisioned_mib / drr

@dataclass(frozen=True)
class WorkloadGroupResult:
    """Aggregated results for one workload category."""
    category: str
    vm_count: int
    total_provisioned_mib: float
    total_in_use_mib: float
    avg_drr: float  # weighted average for this group
    total_required_mib: float

@dataclass(frozen=True)
class CalculationSummary:
    """Full calculation output."""
    vm_calculations: list[VMCalculation]
    workload_groups: list[WorkloadGroupResult]
    total_vms: int
    total_provisioned_mib: float
    total_in_use_mib: float
    total_required_mib: float
    weighted_avg_drr: float

def calculate(row_data: list[dict[str, Any]]) -> CalculationSummary:
    """Core calculation function. No UI dependencies."""
    ...
```

### Pattern 2: PDF Generation with In-Memory Buffer

**What:** Generate PDF to a `BytesIO` buffer using ReportLab Platypus, return bytes.
**When to use:** For serving downloads without temp files.
**Example:**

```python
# Source: ReportLab docs (https://docs.reportlab.com/reportlab/userguide/ch5_platypus)
import io
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_report_pdf(summary: CalculationSummary, project_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"StorePredict Report - {project_name}",
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )
    # Register Vera for French chars
    import reportlab
    import os
    font_dir = os.path.join(os.path.dirname(reportlab.__file__), 'fonts')
    pdfmetrics.registerFont(TTFont('Vera', os.path.join(font_dir, 'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('VeraBd', os.path.join(font_dir, 'VeraBd.ttf')))

    story = [...]  # Build flowables
    doc.build(story, onFirstPage=_draw_header)
    return buffer.getvalue()
```

### Pattern 3: NiceGUI Download Trigger

**What:** Use `ui.download.content()` to push PDF bytes to the browser.
**When to use:** For the download button on the report page.
**Example:**

```python
# Source: NiceGUI docs (https://nicegui.io/documentation/download)
from nicegui import ui

def _download_pdf():
    pdf_bytes = generate_report_pdf(summary, project_name)
    ui.download.content(
        pdf_bytes,
        filename=f"StorePredict_{project_name}_{date_str}.pdf",
        media_type='application/pdf',
    )

ui.button('Download PDF Report', on_click=_download_pdf, icon='download')
```

### Pattern 4: Branded PDF Header via onFirstPage Callback

**What:** Use canvas-level drawing in a callback to add a branded header.
**When to use:** For the report title, logo area, project name, and date.
**Example:**

```python
# Source: ReportLab docs (https://docs.reportlab.com/reportlab/userguide/ch5_platypus)
from reportlab.lib.pagesizes import A4

def _draw_header(canvas, doc):
    canvas.saveState()
    width, height = A4
    # Brand bar
    canvas.setFillColorRGB(0.0, 0.2, 0.5)  # Dark blue (matching UI)
    canvas.rect(0, height - 50, width, 50, fill=True, stroke=False)
    # Title
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont('VeraBd', 18)
    canvas.drawString(20*mm, height - 35, "StorePredict Sizing Report")
    canvas.restoreState()
```

### Anti-Patterns to Avoid

- **Coupling calculation to UI:** The calculation service MUST be in `pipeline/` with zero UI imports (NFR-2.4 requirement).
- **Writing PDF to disk then serving:** Use `BytesIO` buffer instead -- avoids temp file cleanup and concurrency issues.
- **Hardcoding DRR values in calculation:** Always read from the DRR column in session data (user may have edited workloads on review page).
- **Using standard fonts for French:** Standard PDF fonts (Helvetica, Times) only support WinAnsiEncoding; accented chars may fail. Must use Vera TTF.
- **Building PDF with raw Canvas only:** Platypus `SimpleDocTemplate` + `Table` handles pagination, column widths, and content flow. Don't manual-position everything.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF table rendering | Manual canvas.drawString() loops | `reportlab.platypus.Table` + `TableStyle` | Handles cell wrapping, column widths, styling, page breaks |
| Font embedding | Manual font file management | `pdfmetrics.registerFont(TTFont(...))` with bundled Vera | ReportLab handles subsetting and embedding automatically |
| File download | Custom HTTP endpoint | `ui.download.content()` | NiceGUI handles response headers, MIME type, browser download trigger |
| Weighted average DRR | Complex per-group averaging | `total_provisioned / total_required` | Mathematically equivalent and simpler: if required = prov/drr, then weighted_avg_drr = sum(prov) / sum(prov/drr) |
| MiB to GiB/TiB | Ad-hoc division everywhere | Helper function `format_storage(mib)` | Consistent formatting, single place to change units |

**Key insight:** ReportLab's Platypus framework exists precisely to avoid low-level canvas coordinate math. Use `Table` for the breakdown, `Paragraph` for text, `Spacer` for gaps, and let `SimpleDocTemplate.build()` handle layout.

## Common Pitfalls

### Pitfall 1: Division by Zero in DRR Calculation

**What goes wrong:** A VM with `drr=0` causes `ZeroDivisionError` in `required_mib = provisioned_mib / drr`.
**Why it happens:** Edge case if DRR data is corrupted or a custom DRR of 0 is entered.
**How to avoid:** Guard with `max(drr, 0.1)` or skip VMs with DRR <= 0. The existing `DRRTable.get_ratio()` defaults to 5.0, but user edits on the review page could theoretically set 0.
**Warning signs:** `ZeroDivisionError` in test with edge-case data.

### Pitfall 2: Empty Dataset

**What goes wrong:** No VMs uploaded, or all filtered out. Division by zero in averages, empty tables.
**Why it happens:** Edge case of zero rows after filtering.
**How to avoid:** Check `len(row_data) == 0` early, return a "no data" summary. Show appropriate message on report page.
**Warning signs:** `ZeroDivisionError` when computing averages over empty list.

### Pitfall 3: Vera Font Not Found in Docker

**What goes wrong:** `TTFont('Vera', path)` raises `FileNotFoundError` in container.
**Why it happens:** Font path is derived from `reportlab.__file__`, which differs between dev and Docker.
**How to avoid:** Use `reportlab.rl_config.TTFSearchPath` or compute path relative to the reportlab package directory at runtime. Always use `os.path.join(os.path.dirname(reportlab.__file__), 'fonts', 'Vera.ttf')`.
**Warning signs:** Works locally, fails in CI/Docker.

### Pitfall 4: Large Tables Overflowing One Page

**What goes wrong:** With 30 workload categories, the breakdown table may exceed one A4 page.
**Why it happens:** ReportLab `Table` can grow beyond page bounds if not constrained.
**How to avoid:** Use smaller font size (8-9pt) for tables, limit to workload group summary (not per-VM listing). With 28 DRR categories max, a well-sized table should fit on one page. Set `SimpleDocTemplate(... , topMargin=..., bottomMargin=...)` to maximize usable area.
**Warning signs:** PDF is 2+ pages when requirement says one page.

### Pitfall 5: Session Data Shape After User Edits

**What goes wrong:** Row dicts from session may have different keys after user edits on review page.
**Why it happens:** The review page modifies `workload_category`, `workload_subcategory`, `drr` in-place.
**How to avoid:** The calculation service should use `.get(key, default)` for all field accesses with sensible defaults. Existing `summary_stats.py` already uses this pattern.
**Warning signs:** `KeyError` when accessing row fields.

### Pitfall 6: PDF Filename with Special Characters

**What goes wrong:** Project name with spaces, slashes, or accents causes download issues.
**Why it happens:** Filenames need to be sanitized for HTTP Content-Disposition.
**How to avoid:** Sanitize project name in filename: replace non-alphanumeric chars with underscores.
**Warning signs:** Browser shows garbled filename or download fails.

## Code Examples

### Calculation: Per-VM Required Capacity (FR-5.1)

```python
# Source: Project requirement FR-5.1
def _calculate_vm(row: dict[str, Any]) -> VMCalculation:
    provisioned = float(row.get("provisioned_mib", 0))
    in_use = float(row.get("in_use_mib", 0))
    drr = float(row.get("drr", 5.0))
    drr = max(drr, 0.1)  # Guard against zero
    return VMCalculation(
        vm_name=str(row.get("vm_name", "")),
        workload_category=str(row.get("workload_category", "Unknown (Reducible)")),
        provisioned_mib=provisioned,
        in_use_mib=in_use,
        drr=drr,
        required_mib=provisioned / drr,
    )
```

### Calculation: Weighted Average DRR (FR-5.2)

```python
# Source: Mathematical definition
# weighted_avg_drr = total_provisioned / total_required
# This works because required_i = provisioned_i / drr_i
# So sum(provisioned) / sum(provisioned/drr) = weighted average DRR
total_provisioned = sum(vm.provisioned_mib for vm in vm_calcs)
total_required = sum(vm.required_mib for vm in vm_calcs)
weighted_avg_drr = total_provisioned / total_required if total_required > 0 else 0.0
```

### Calculation: Group by Workload (FR-5.3)

```python
# Source: Python stdlib itertools pattern
from collections import defaultdict

groups: dict[str, list[VMCalculation]] = defaultdict(list)
for vm in vm_calcs:
    groups[vm.workload_category].append(vm)

workload_results = []
for category, vms in sorted(groups.items()):
    prov = sum(v.provisioned_mib for v in vms)
    req = sum(v.required_mib for v in vms)
    workload_results.append(WorkloadGroupResult(
        category=category,
        vm_count=len(vms),
        total_provisioned_mib=prov,
        total_in_use_mib=sum(v.in_use_mib for v in vms),
        avg_drr=prov / req if req > 0 else 0.0,
        total_required_mib=req,
    ))
```

### PDF: Workload Breakdown Table (FR-6.3)

```python
# Source: ReportLab docs (ch7_tables) verified via Context7
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

header = ['Category', 'VMs', 'Provisioned (GiB)', 'Avg DRR', 'Required (GiB)']
data = [header]
for wg in summary.workload_groups:
    data.append([
        wg.category,
        str(wg.vm_count),
        f"{wg.total_provisioned_mib / 1024:.1f}",
        f"{wg.avg_drr:.1f}x",
        f"{wg.total_required_mib / 1024:.1f}",
    ])
# Totals row
data.append([
    'TOTAL',
    str(summary.total_vms),
    f"{summary.total_provisioned_mib / 1024:.1f}",
    f"{summary.weighted_avg_drr:.1f}x",
    f"{summary.total_required_mib / 1024:.1f}",
])

table = Table(data, colWidths=[150, 50, 100, 70, 100])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),  # Dark blue header
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'VeraBd'),
    ('FONTNAME', (0, 1), (-1, -1), 'Vera'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f0f4f8')]),
    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8ecf0')),  # Totals row
    ('FONTNAME', (0, -1), (-1, -1), 'VeraBd'),  # Bold totals
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
]))
```

### NiceGUI: Download Trigger (FR-6.5)

```python
# Source: NiceGUI docs (https://nicegui.io/documentation/download) verified via Context7
from nicegui import ui

def _on_download():
    pdf_bytes = generate_report_pdf(summary, project_name)
    safe_name = re.sub(r'[^\w\-]', '_', project_name) if project_name else 'report'
    ui.download.content(
        pdf_bytes,
        filename=f"StorePredict_{safe_name}_{date_str}.pdf",
        media_type='application/pdf',
    )

ui.button('Download PDF Report', on_click=_on_download, icon='download') \
    .classes('bg-blue-700 text-white')
```

### Navigation: Review -> Report

```python
# Source: Existing layout.py pattern
# Add to layout.py nav bar:
ui.link("Report", "/report").classes("text-white no-underline hover:underline")

# Add to review page (bottom navigation button):
ui.button("Generate Report", on_click=lambda: ui.navigate.to("/report")) \
    .classes("bg-blue-700 text-white")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WeasyPrint (HTML->PDF) | ReportLab (native PDF) | Project decision | No external system dependencies (WeasyPrint needs cairo/pango) |
| Disk-based temp PDF files | In-memory BytesIO buffer | ReportLab has always supported this | Cleaner, no cleanup needed |
| pdfmetrics standard fonts | TTF font registration (Vera) | Required for Unicode | Standard fonts limited to WinAnsiEncoding |
| `ui.download('path')` | `ui.download.content(bytes, name)` | NiceGUI 3.x | Direct byte content download without disk I/O |

**Deprecated/outdated:**

- ReportLab `Canvas.stringWidth()` for manual text layout -- use Platypus flowables instead
- `reportlab.lib.styles.ParagraphStyle` direct instantiation -- use `getSampleStyleSheet()` as base and customize

## Open Questions

1. **Logo/branding image in PDF header**
   - What we know: FR-6.1 says "StorePredict branding" -- could be text-only or include a logo
   - What's unclear: Whether a logo image file exists or needs to be created
   - Recommendation: Start with text-only branding (bold title + colored bar). Add logo later if provided. This is sufficient for MVP.

2. **TiB vs GiB display units**
   - What we know: Current UI shows GiB. For large environments (5000 VMs), totals could be in TiB range.
   - What's unclear: Whether PDF should auto-switch to TiB for large values.
   - Recommendation: Use GiB consistently with TiB in parentheses for totals > 1024 GiB. E.g., "1,536.0 GiB (1.5 TiB)".

3. **Per-VM detail in PDF vs. summary only**
   - What we know: FR-6.3 specifies workload breakdown table (category-level). No mention of per-VM listing.
   - What's unclear: Whether customers expect per-VM detail in the PDF.
   - Recommendation: PDF shows workload group summary only (fits one page). Per-VM detail stays in the UI review page. This matches the one-page requirement.

## Sources

### Primary (HIGH confidence)

- Context7 `/websites/reportlab` -- SimpleDocTemplate, Table, TableStyle, TTFont registration, onFirstPage callbacks
- Context7 `/websites/nicegui_io` -- ui.download.content(), file serving, button patterns
- ReportLab official docs: <https://docs.reportlab.com/reportlab/userguide/ch5_platypus> (Platypus framework)
- ReportLab official docs: <https://docs.reportlab.com/reportlab/userguide/ch7_tables> (Table styling)
- ReportLab official docs: <https://docs.reportlab.com/reportlab/userguide/ch3_fonts> (TTF font registration)
- NiceGUI official docs: <https://nicegui.io/documentation/download> (download API)

### Secondary (MEDIUM confidence)

- Existing codebase analysis: `summary_stats.py`, `state.py`, `review.py`, `drr_table.py` -- established patterns for data flow and UI components

### Tertiary (LOW confidence)

- None. All findings verified against official documentation.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH -- All libraries already installed and proven in the project; ReportLab 4.4.10 and NiceGUI 3.7.1 verified
- Architecture: HIGH -- Follows established project patterns (pipeline/UI separation, session state, context-manager layout)
- Pitfalls: HIGH -- Based on ReportLab official docs and direct verification (Vera font tested with French characters)

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable libraries, no breaking changes expected)
