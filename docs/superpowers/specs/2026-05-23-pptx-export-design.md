# PPTX Export — Design Spec

**Date:** 2026-05-23
**Status:** Approved (design); pending implementation plan
**Author:** brainstormed with Claude

## Overview

Add a PowerPoint (`.pptx`) export to the `/report` page, alongside the existing
PDF and Excel exports. Pre-sales engineers present sizing results to customers
in PowerPoint; a generated deck is a natural "present and leave behind"
deliverable.

The deck is a **hybrid**: a concise customer-facing pitch deck up front, followed
by appendix slides for the technical audience. Charts are **native, editable
PowerPoint charts** where a native chart type exists (pie, bar), with the Sankey
flow rendered as an image (PowerPoint has no native Sankey). The deck is
**self-contained and branded** — built from scratch with python-pptx, styled to
match the PDF deliverable, reusing the existing company-logo upload. No template
file is required.

## Goals

- One-click `.pptx` download from `/report`, mirroring the PDF/Excel buttons.
- A deck that is presentable as-is and editable by the SE in PowerPoint.
- Visual and data consistency with the existing PDF report.
- Full localization (EN/FR/DE/IT) via the existing `t()` mechanism.

## Non-Goals (v1)

- No corporate-template injection (uploading a company `.pptx` to populate). The
  branding is self-contained. This can be a future enhancement.
- No PPTX export on the separate datastore **layout planner** page
  (`ui/pages/layout_page.py`) — that page keeps its own PDF/Excel exports. v1 is
  scoped to the main `/report` page only.
- No new chart *types* beyond what the PDF already shows.

## Architecture

Follows the established "generate a deliverable as bytes → offer a download
button" pattern used by `pdf_report.py` / `excel_report.py`. Two new modules,
mirroring the `pdf_report.py` + `pdf_charts.py` split:

### `src/store_predict/services/pptx_report.py`

Public entry point, signature-parallel to `generate_report_pdf` /
`generate_report_xlsx`:

```python
def generate_report_pptx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    company_logo_bytes: bytes | None = None,
    health_result: HealthCheckResult | None = None,
) -> bytes:
    ...
```

Responsibilities:
- `_i18n.set("locale", locale)` before any `t()` call (same synchronous pattern
  as `generate_report_pdf`; no coroutine interleaving).
- Create a 16:9 `Presentation()` (`slide_width = Inches(13.333)`,
  `slide_height = Inches(7.5)`).
- Compose slides by calling private `_slide_*` builders (one per slide type).
- Return `BytesIO` bytes via `prs.save(buf)`.

Private slide builders (one responsibility each), e.g.:
`_slide_title`, `_slide_exec_summary`, `_slide_drr_story`, `_slide_workload_mix`,
`_slide_recommendation`, `_slide_breakdown_table`, `_slide_layout_strategies`,
`_slide_findings`, `_slide_charts`.

Shared helpers: a brand header-band drawer, a KPI-tile drawer, and a table-filler
(reusing the `_layout_metric_rows` data shape already exported by
`pdf_report.py`).

### `src/store_predict/services/pptx_charts.py`

Native-chart + Sankey-image builders, analogous to `pdf_charts.py`:

- `add_workload_pie(slide, summary, x, y, cx, cy)` — `XL_CHART_TYPE.PIE` from
  `CategoryChartData` (categories = workload categories, one series = capacity).
- `add_drr_bar(slide, summary, ...)` — `XL_CHART_TYPE.COLUMN_CLUSTERED`, avg DRR
  per category.
- `add_before_after_bar(slide, summary, ...)` — `XL_CHART_TYPE.COLUMN_CLUSTERED`,
  provisioned vs. required capacity.
- `add_sankey_picture(slide, summary, ...)` — reuses the existing matplotlib
  Sankey renderer (the image-producing core behind
  `pdf_charts.make_sankey_image_flowable`) to produce PNG bytes, placed via
  `slide.shapes.add_picture(BytesIO(png), ...)`. Refactor the matplotlib Sankey
  in `pdf_charts.py` so the PNG-bytes core is callable from both modules (DRY),
  without changing the PDF flowable's behavior.

Native charts get brand styling: `chart.has_legend`, legend position, data
labels, and series fill colors set to the PDF's Dell-blue palette
(`pdf_charts.DELL_PALETTE_RL` HEX equivalents as `RGBColor`).

## Slide composition (hybrid: deck + appendix)

Conditional slides appear only when the data supports them — same guards the PDF
uses (`summary.has_performance_data`, `summary.total_vms > 0`,
`health_result is not None and health_result.has_data and health_result.findings`).

### Main (present)

1. **Title** — report title (`t("pptx.report_title")` / reuse `pdf.report_title`),
   project name, date, customer logo (decoded from the existing
   `company_logo_b64` tab storage), brand header band.
2. **Executive summary** — KPI tiles: total VMs, total provisioned, **required
   capacity** (headline), weighted DRR.
3. **DRR story** — native before/after bar (provisioned → required) with the
   weighted DRR called out as a large number.
4. **Workload mix** — native pie of capacity per category + 2–3 highlight
   callouts (largest category, count of categories).
5. **Recommendation** — required capacity restated; top health findings
   (critical/warning counts) when available.

### Appendix (back-up)

6. **Full workload breakdown** — native table: category × (VMs, provisioned GiB,
   avg DRR, required GiB) with a totals row. Same columns/order as the PDF table.
7. **Layout strategies** — native table of the consolidation / performance /
   uniform comparison, built from `_layout_metric_rows(generate_all_proposals(summary))`.
   Only when `summary.total_vms > 0`.
8. **Health findings** — native table of severity-grouped findings, only when
   findings exist.
9. **Charts** — Sankey image + native pie/DRR bars for the technical audience.

## Branding

Palette and fonts match the **PDF deliverable** so the deck and PDF read as one
family:
- Brand blue `#1e3a5f` for header bands / table headers (the PDF `_BRAND_BLUE`).
- Dell-blue chart palette from `pdf_charts.py` (`#007DB8`, `#40A8D8`, greys).
- Open Sans (the fonts already bundled in `services/_fonts.py`); set
  `run.font.name` on title/heading runs. PowerPoint substitutes if the viewer
  lacks the font — acceptable, matches typical decks.

## Data flow

```
/report page (review-filtered, non-ignored VMs)
   → calculate(vm_data) → CalculationSummary
   → run_health_checks(active_df) → HealthCheckResult
   → [PPTX button] → _on_download_pptx
       → run.io_bound(generate_report_pptx, summary, project_name, locale,
                      company_logo_bytes, health_result)
       → ui.download(bytes, filename, media_type=pptx)
```

The same `summary` / `health_result` already computed for the page render are
reused — no recomputation.

## UI wiring (`ui/pages/report.py`)

- Add a third action button beside PDF/Excel:
  `ui.button(t("report.download_pptx"), icon="slideshow").props("color=secondary").tooltip(t("tooltip.download_pptx"))`.
- Handler `_on_download_pptx`, mirroring `_on_download_excel`:
  - `assert isinstance(summary, CalculationSummary)`
  - decode `company_logo_b64` from tab storage to bytes (as the PDF handler does)
  - `pptx_bytes = await run.io_bound(generate_report_pptx, summary, project_name, get_locale(), company_logo_bytes, health_result)`
  - filename `f"StorePredict_{safe_name}{scope_suffix}_{date_str}.pptx"` via the
    existing `sanitize_filename` + `_scope_filename_suffix` helpers
  - `ui.download(pptx_bytes, filename=filename, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")`
- Wrap the button in disable/enable around the await, and guard generation in
  try/except → `ui.notify(t("error.unexpected"), type="negative")`, same as the
  PDF path.

## Internationalization

- New keys in **all four** locale files
  (`src/store_predict/i18n/locales/{en,fr,de,it}.yaml`):
  - `report.download_pptx` (button label)
  - `tooltip.download_pptx` (tooltip)
  - `pptx.*` for any slide-specific strings not already covered by existing
    `pdf.*` / `report.*` / `stats.*` / `metrics.*` keys (reuse those where they
    fit; add `pptx.*` only for genuinely new copy such as slide subtitles).
- French is primary; maintain key parity across all four files.

## Dependencies

- Add `python-pptx` to `pyproject.toml` `dependencies` (pin with a lower bound
  and a conservative upper bound consistent with the project's other pins, e.g.
  `python-pptx>=1.0,<2.0` — exact bound confirmed at plan time).
- `matplotlib` and `pillow` are already dependencies (used for the Sankey image),
  so no additional charting dependency is needed.

## Error handling

- Generation runs in `run.io_bound`; the UI handler catches exceptions and
  notifies with the generic localized error, never leaking internals (consistent
  with the PDF handler and the project's log-sanitization rules).
- Empty / degenerate data: builders that depend on optional data are guarded
  (see "Slide composition"); a deck with only the main slides is still valid.
- The button is disabled during generation to prevent double-submits.

## Security

- The only external input is the company logo, already validated by
  `pdf_report.validate_logo` (format, magic bytes, size, dimensions) before being
  stored. The PPTX path reuses that validated value.
- All dynamic text (VM names, category names) is written via python-pptx's
  `.text` setters / table cells, which XML-escape internally — no markup
  injection. We **write** PPTX (Open XML) only; we do not parse untrusted PPTX,
  so XML-parsing hardening (e.g. defusedxml) is not applicable here.
- No DataFrame contents or VM names are logged.

## Testing (real objects, no mocks)

Per project convention, tests use real objects, fixtures, and sample data — never
`unittest.mock`.

- Build a real `CalculationSummary` (and a `HealthCheckResult`) from sample data,
  call `generate_report_pptx`, then **re-open the returned bytes with
  `pptx.Presentation(BytesIO(bytes))`** and assert structure:
  - expected number of slides (and that appendix slides appear/disappear with the
    data guards);
  - key strings present in slide text frames / table cells (project name, headline
    KPIs, table headers);
  - chart shapes exist on the chart slides (`shape.has_chart`), and a picture
    shape exists for the Sankey;
  - **locale wiring:** FR output bytes ≠ EN output bytes, and a FR-specific label
    appears in the FR deck's text (analogous to the PDF/Excel locale tests).
- A handler-level test (or existing report-page test pattern) confirms the
  download is wired with the correct `.pptx` filename and media type.

## Open questions

None. Scope, deck shape, chart strategy, and branding are all settled (see the
Non-Goals for explicit v1 boundaries).
