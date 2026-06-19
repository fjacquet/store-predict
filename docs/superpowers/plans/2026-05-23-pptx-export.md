# PPTX Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a branded, editable PowerPoint (`.pptx`) export to the `/report` page, alongside the existing PDF and Excel exports.

**Architecture:** Two new service modules mirror the existing `pdf_report.py`/`pdf_charts.py` split: `pptx_report.py` composes a hybrid deck (concise pitch slides + technical appendix) and `pptx_charts.py` builds native, editable PowerPoint charts plus a Sankey image. A new `report.py` button calls `generate_report_pptx(...) -> bytes` via `run.io_bound` and hands it to `ui.download`. Branding matches the PDF deliverable; charts that have a native PowerPoint equivalent (pie, bar) are native and editable, and the Sankey reuses the existing matplotlib renderer as an embedded picture.

**Tech Stack:** python-pptx (new), python-i18n, matplotlib + pillow (already present, for the Sankey image), pytest. Commands use the `rtk` prefix per project convention. The `.venv` is pre-activated in the interactive shell; in the non-interactive Bash tool use `.venv/bin/python -m pytest ...`.

---

## Conventions for every task

- **RTK prefix:** all shell commands are prefixed with `rtk` (e.g. `rtk pytest`, `rtk ruff check .`).
- **Tests use real objects** — fixtures and real dataclasses only. **Never** `unittest.mock`.
- **i18n:** all user-facing strings go through `t()`. New keys go in **all four** locales (`en`, `fr`, `de`, `it`). French is the primary locale.
- **Never log** DataFrame contents or VM names.
- **Commit trailer** on every commit:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  ```
- After each task, before committing, run the quality gate on touched files:
  ```bash
  rtk ruff format .
  rtk ruff check .
  rtk mypy src/
  ```

## File structure (created/modified across the plan)

- **Modify** `pyproject.toml` — add `python-pptx` dependency (Task 1).
- **Modify** `src/store_predict/i18n/locales/{en,fr,de,it}.yaml` — new keys (Task 2).
- **Modify** `src/store_predict/services/pdf_charts.py` — extract `render_sankey_png()` (Task 3).
- **Create** `src/store_predict/services/pptx_charts.py` — native chart + Sankey-picture builders (Tasks 4–5).
- **Create** `src/store_predict/services/pptx_report.py` — deck orchestrator + slide builders (Tasks 6–9).
- **Modify** `src/store_predict/ui/pages/report.py` — PPTX button + handler (Task 10).
- **Create** `tests/test_pptx_charts.py` (Tasks 4–5) and `tests/test_pptx_report.py` (Tasks 6–9).
- **Create** `docs/adr/086-pptx-export.md`; **modify** `docs/adr/index.md`, `CHANGELOG.md`, `pyproject.toml` version (Task 11).

---

## Task 1: Add the python-pptx dependency

**Files:**
- Modify: `pyproject.toml` (the `[project].dependencies` array)

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, inside the `dependencies = [ ... ]` array (alongside `reportlab>=4.0`, `matplotlib>=3.8`, etc.), add:

```toml
    "python-pptx>=1.0,<2.0",
```

- [ ] **Step 2: Install into the venv**

Run:
```bash
rtk uv pip install -e ".[dev]"
```
Expected: resolves and installs `python-pptx` (and its `XlsxWriter`/`lxml` deps) with no errors.

- [ ] **Step 3: Verify the import works**

Run:
```bash
.venv/bin/python -c "import pptx; from pptx import Presentation; from pptx.util import Inches, Pt; from pptx.dml.color import RGBColor; from pptx.chart.data import CategoryChartData; from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION; print(pptx.__version__)"
```
Expected: prints a version string (e.g. `1.0.2`), no traceback.

- [ ] **Step 4: Commit**

```bash
rtk git add pyproject.toml uv.lock
rtk git commit -m "build(pptx): add python-pptx dependency

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Add i18n keys (all four locales)

**Files:**
- Modify: `src/store_predict/i18n/locales/en.yaml`
- Modify: `src/store_predict/i18n/locales/fr.yaml`
- Modify: `src/store_predict/i18n/locales/de.yaml`
- Modify: `src/store_predict/i18n/locales/it.yaml`
- Test: `tests/test_i18n.py` (existing parity test — run, don't rewrite)

Reuse existing keys for content already covered (`stats.*` for KPI tiles, `pdf.report_title`, `pdf.table_*`, `pdf.findings_*`, `strategy.*`, `metrics.*`, `layout_page.metric`). Only genuinely new copy gets new keys.

- [ ] **Step 1: Add the `report.download_pptx` key**

Under the existing `report:` namespace in each file, next to `download_excel`, add:

- `en.yaml`: `  download_pptx: Download PowerPoint`
- `fr.yaml`: `  download_pptx: Télécharger PowerPoint`
- `de.yaml`: `  download_pptx: PowerPoint herunterladen`
- `it.yaml`: `  download_pptx: Scarica PowerPoint`

- [ ] **Step 2: Add the `tooltip.download_pptx` key**

Under the existing `tooltip:` namespace, next to `download_excel`, add:

- `en.yaml`: `  download_pptx: "Download the sizing report as an editable PowerPoint deck"`
- `fr.yaml`: `  download_pptx: "Télécharger le rapport de dimensionnement en présentation PowerPoint modifiable"`
- `de.yaml`: `  download_pptx: "Sizing-Bericht als bearbeitbare PowerPoint-Präsentation herunterladen"`
- `it.yaml`: `  download_pptx: "Scarica il report di dimensionamento come presentazione PowerPoint modificabile"`

- [ ] **Step 3: Add the new top-level `pptx:` namespace**

Add a `pptx:` block (top-level, same indentation level as `report:` / `pdf:`) to each file:

`en.yaml`:
```yaml
pptx:
  exec_summary_heading: Executive Summary
  drr_story_heading: Data Reduction
  workload_mix_heading: Workload Mix
  recommendation_heading: Recommendation
  appendix_heading: Appendix
  provisioned: Provisioned
  required: Required
```

`fr.yaml`:
```yaml
pptx:
  exec_summary_heading: Synthèse
  drr_story_heading: Réduction des données
  workload_mix_heading: Répartition des charges
  recommendation_heading: Recommandation
  appendix_heading: Annexe
  provisioned: Provisionné
  required: Requis
```

`de.yaml`:
```yaml
pptx:
  exec_summary_heading: Zusammenfassung
  drr_story_heading: Datenreduktion
  workload_mix_heading: Workload-Verteilung
  recommendation_heading: Empfehlung
  appendix_heading: Anhang
  provisioned: Bereitgestellt
  required: Erforderlich
```

`it.yaml`:
```yaml
pptx:
  exec_summary_heading: Sintesi
  drr_story_heading: Riduzione dei dati
  workload_mix_heading: Distribuzione dei carichi
  recommendation_heading: Raccomandazione
  appendix_heading: Appendice
  provisioned: Provisionato
  required: Richiesto
```

- [ ] **Step 4: Run the i18n parity test**

Run:
```bash
rtk pytest tests/test_i18n.py -v
```
Expected: PASS — all four locales have identical key sets (the parity test catches any missing key).

- [ ] **Step 5: Commit**

```bash
rtk git add src/store_predict/i18n/locales/
rtk git commit -m "i18n(pptx): add PowerPoint export keys (en/fr/de/it)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Extract a reusable Sankey PNG renderer

The existing `make_sankey_image_flowable()` builds a matplotlib figure and returns a ReportLab `Image`. Extract the figure-to-PNG core so both the PDF flowable and the PPTX picture can share it (DRY). Behavior of the PDF path must not change.

**Files:**
- Modify: `src/store_predict/services/pdf_charts.py`
- Test: `tests/test_pdf_charts.py` (add a new test)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pdf_charts.py`:

```python
def test_render_sankey_png_returns_png_bytes() -> None:
    from store_predict.services.pdf_charts import render_sankey_png

    summary = _make_summary([("Database/Microsoft SQL", 3, 30720.0, 5.0)])  # local helper in this file
    png = render_sankey_png(summary, width_pt=480, height_pt=180)
    assert isinstance(png, (bytes, bytearray))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_sankey_png_returns_none_for_empty() -> None:
    from store_predict.services.pdf_charts import render_sankey_png

    summary = _make_summary()  # 0 VMs, total_provisioned_mib == 0
    assert render_sankey_png(summary, width_pt=480, height_pt=180) is None
```

If `tests/test_pdf_charts.py` has no local `_make_summary`, copy the `_make_summary` helper from `tests/test_excel_report.py` (lines 16–67) into this test module.

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
.venv/bin/python -m pytest tests/test_pdf_charts.py::test_render_sankey_png_returns_png_bytes -v
```
Expected: FAIL with `ImportError: cannot import name 'render_sankey_png'`.

- [ ] **Step 3: Refactor `pdf_charts.py`**

In `src/store_predict/services/pdf_charts.py`, add `render_sankey_png` to `__all__`, then introduce the function by moving the figure-building body out of `make_sankey_image_flowable`. The new function returns `bytes | None` (None when there is no data). `make_sankey_image_flowable` becomes a thin wrapper.

Replace the existing `make_sankey_image_flowable` (currently lines 119–250) with:

```python
def render_sankey_png(summary: CalculationSummary, width_pt: int = 500, height_pt: int = 200) -> bytes | None:
    """Render the provisioned→required Sankey to PNG bytes via matplotlib Agg (headless).

    Returns ``None`` when there is no data to plot (no workload groups or zero
    provisioned capacity). Flow bands are cubic Bezier sigmoid curves.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path as MplPath

    if not summary.workload_groups or summary.total_provisioned_mib == 0:
        return None

    _fp = FontProperties(fname=str(FONT_PATH_LIGHT)) if FONT_PATH_LIGHT.exists() else FontProperties()

    groups = summary.workload_groups
    total_prov = summary.total_provisioned_mib
    total_req = summary.total_required_mib

    palette = ["#007DB8", "#40A8D8", "#6C757D", "#ADB5BD", "#CED4DA", "#DEE2E6"]

    dpi = 300
    fig = Figure(figsize=(width_pt / 72, height_pt / 72), dpi=dpi, facecolor="white")
    FigureCanvasAgg(fig)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    node_w = 0.03
    left_x = 0.05
    right_x = 0.92
    mid_x = (left_x + right_x + node_w) / 2.0 - node_w / 2.0
    usable_h = 0.78
    offset_y = 0.11
    scale = usable_h / total_prov

    prov_h = total_prov * scale
    req_h = total_req * scale
    left_y0 = offset_y + (usable_h - prov_h) / 2.0
    right_y0 = offset_y + (usable_h - req_h) / 2.0

    def _node(x: float, y0: float, h: float, color: str) -> None:
        ax.add_patch(Rectangle((x, y0), node_w, h, facecolor=color, edgecolor="none", zorder=3))

    def _label(x: float, y: float, text: str, size: float = 7, va: str = "bottom") -> None:
        ax.text(x, y, text, ha="center", va=va, fontsize=size, color="#333333", zorder=5, fontproperties=_fp)

    def _hex_rgba(hx: str, alpha: float) -> tuple[float, float, float, float]:
        return (int(hx[1:3], 16) / 255, int(hx[3:5], 16) / 255, int(hx[5:7], 16) / 255, alpha)

    def _flow_band(x0: float, yb0: float, h0: float, x1: float, yb1: float, h1: float, color: str) -> None:
        cx = (x0 + x1) / 2.0
        verts = [
            (x0, yb0),
            (cx, yb0),
            (cx, yb1),
            (x1, yb1),
            (x1, yb1 + h1),
            (cx, yb1 + h1),
            (cx, yb0 + h0),
            (x0, yb0 + h0),
            (x0, yb0),
        ]
        codes = [
            MplPath.MOVETO,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.LINETO,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CLOSEPOLY,
        ]
        ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=_hex_rgba(color, 0.35), edgecolor="none", zorder=2))

    _node(left_x, left_y0, prov_h, "#007DB8")
    _label(left_x + node_w / 2, left_y0 + prov_h + 0.03, "Provisioned")
    _label(left_x + node_w / 2, left_y0 - 0.04, f"{total_prov / 1024:.0f} GiB", size=6.0, va="top")

    _node(right_x, right_y0, req_h, "#40A8D8")
    _label(right_x + node_w / 2, right_y0 + req_h + 0.03, "Required")
    _label(right_x + node_w / 2, right_y0 - 0.04, f"{total_req / 1024:.0f} GiB", size=6.0, va="top")

    cur_left_top = left_y0 + prov_h
    cur_right_top = right_y0 + req_h

    for i, grp in enumerate(groups):
        color = palette[i % len(palette)]
        seg_prov_h = max(grp.total_provisioned_mib * scale, 0.005)
        seg_req_h = max(grp.total_required_mib * scale, 0.005)

        seg_left_y0 = cur_left_top - seg_prov_h
        seg_right_y0 = cur_right_top - seg_req_h
        seg_mid_y0 = seg_left_y0
        seg_mid_h = seg_prov_h

        _node(mid_x, seg_mid_y0, seg_mid_h, color)
        if seg_mid_h >= 0.04:
            txt_color = "white" if i < 2 else "#333333"
            ax.text(
                mid_x + node_w / 2,
                seg_mid_y0 + seg_mid_h / 2,
                grp.category[:12],
                ha="center",
                va="center",
                fontsize=6,
                color=txt_color,
                zorder=4,
                fontproperties=_fp,
            )

        _flow_band(left_x + node_w, seg_left_y0, seg_prov_h, mid_x, seg_mid_y0, seg_mid_h, color)
        _flow_band(mid_x + node_w, seg_mid_y0, seg_mid_h, right_x, seg_right_y0, seg_req_h, color)

        cur_left_top -= seg_prov_h
        cur_right_top -= seg_req_h

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    return buf.getvalue()


def make_sankey_image_flowable(summary: CalculationSummary, width_pt: int = 500, height_pt: int = 200) -> Flowable:
    """Return a ReportLab Image with the provisioned→required Sankey, or an empty Spacer when no data."""
    png = render_sankey_png(summary, width_pt=width_pt, height_pt=height_pt)
    if png is None:
        return Spacer(width_pt, 0)
    return Image(BytesIO(png), width=width_pt, height=height_pt)
```

Update the module `__all__` to include `"render_sankey_png"`.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
.venv/bin/python -m pytest tests/test_pdf_charts.py -v
```
Expected: PASS — both new tests and all pre-existing `test_pdf_charts.py` tests pass (the PDF flowable behavior is unchanged).

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/services/pdf_charts.py tests/test_pdf_charts.py
rtk git commit -m "refactor(charts): extract render_sankey_png for reuse

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Native chart builders in `pptx_charts.py`

**Files:**
- Create: `src/store_predict/services/pptx_charts.py`
- Test: `tests/test_pptx_charts.py`

These functions add a chart to an already-created slide. They take a `slide` and an `EMU` position/size. Categories use `grp.category`; values use capacity in GiB. Colors come from the PDF Dell-blue palette.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pptx_charts.py`:

```python
"""Tests for the PPTX chart builders."""

from __future__ import annotations

from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services import pptx_charts


def _make_summary() -> CalculationSummary:
    groups = [
        WorkloadGroupResult("Database/Microsoft SQL", 3, 30720.0, 18432.0, 5.0, 6144.0),
        WorkloadGroupResult("Virtual Machines", 2, 10240.0, 6144.0, 5.0, 2048.0),
    ]
    vm_calcs = [
        VMCalculation(f"VM-{i}", "Virtual Machines", 5120.0, 3072.0, 5.0, 1024.0) for i in range(5)
    ]
    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=5,
        total_provisioned_mib=40960.0,
        total_in_use_mib=24576.0,
        total_required_mib=8192.0,
        weighted_avg_drr=5.0,
    )


def _blank_slide():
    prs = Presentation()
    return prs.slides.add_slide(prs.slide_layouts[6])


def test_add_workload_pie_adds_pie_chart() -> None:
    slide = _blank_slide()
    pptx_charts.add_workload_pie(slide, _make_summary(), Inches(1), Inches(1), Inches(5), Inches(4))
    charts = [s.chart for s in slide.shapes if s.has_chart]
    assert len(charts) == 1
    assert charts[0].chart_type == XL_CHART_TYPE.PIE


def test_add_drr_bar_adds_column_chart() -> None:
    slide = _blank_slide()
    pptx_charts.add_drr_bar(slide, _make_summary(), Inches(1), Inches(1), Inches(5), Inches(4))
    charts = [s.chart for s in slide.shapes if s.has_chart]
    assert len(charts) == 1
    assert charts[0].chart_type == XL_CHART_TYPE.COLUMN_CLUSTERED


def test_add_before_after_bar_has_two_series() -> None:
    slide = _blank_slide()
    pptx_charts.add_before_after_bar(slide, _make_summary(), Inches(1), Inches(1), Inches(5), Inches(4))
    charts = [s.chart for s in slide.shapes if s.has_chart]
    assert len(charts) == 1
    assert len(charts[0].series) == 2


def test_chart_builders_noop_on_empty_summary() -> None:
    empty = CalculationSummary([], [], 0, 0.0, 0.0, 0.0, 0.0)
    slide = _blank_slide()
    pptx_charts.add_workload_pie(slide, empty, Inches(1), Inches(1), Inches(5), Inches(4))
    pptx_charts.add_drr_bar(slide, empty, Inches(1), Inches(1), Inches(5), Inches(4))
    pptx_charts.add_before_after_bar(slide, empty, Inches(1), Inches(1), Inches(5), Inches(4))
    assert not any(s.has_chart for s in slide.shapes)
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_pptx_charts.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'store_predict.services.pptx_charts'`.

- [ ] **Step 3: Implement the native chart builders**

Create `src/store_predict/services/pptx_charts.py`:

```python
"""Native PowerPoint chart builders + Sankey picture for the PPTX report.

Charts that have a native PowerPoint equivalent (pie, column) are added as
editable charts so the engineer can restyle them in PowerPoint. The Sankey flow
diagram has no native chart type, so it is embedded as an image rendered by the
shared matplotlib renderer in ``pdf_charts``.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Length

from store_predict.i18n import t
from store_predict.services.pdf_charts import render_sankey_png

if TYPE_CHECKING:
    from pptx.slide import Slide

    from store_predict.pipeline.calculation import CalculationSummary

__all__ = [
    "DELL_PALETTE_HEX",
    "add_before_after_bar",
    "add_drr_bar",
    "add_sankey_picture",
    "add_workload_pie",
]

# Dell-blue palette (matches pdf_charts.DELL_PALETTE_RL) as RGBColor.
DELL_PALETTE_HEX = ("007DB8", "40A8D8", "6C757D", "ADB5BD", "CED4DA", "DEE2E6")
_PALETTE = tuple(RGBColor.from_string(h) for h in DELL_PALETTE_HEX)
_NAVY = RGBColor.from_string("1E3A5F")
_LIGHT_BLUE = RGBColor.from_string("40A8D8")


def add_workload_pie(
    slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length
) -> None:
    """Add an editable pie chart of provisioned capacity per workload category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series("GiB", tuple(grp.total_provisioned_mib / 1024 for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.PIE, x, y, cx, cy, data).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.RIGHT
    chart.legend.include_in_layout = False
    points = chart.series[0].points
    for idx, point in enumerate(points):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = _PALETTE[idx % len(_PALETTE)]


def add_drr_bar(
    slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length
) -> None:
    """Add an editable column chart of average DRR per workload category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series("DRR", tuple(round(grp.avg_drr, 2) for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, data).chart
    chart.has_legend = False
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = _NAVY


def add_before_after_bar(
    slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length
) -> None:
    """Add an editable two-series column chart: provisioned vs required GiB per category."""
    if not summary.workload_groups:
        return
    data = CategoryChartData()
    data.categories = [grp.category for grp in summary.workload_groups]
    data.add_series(t("pptx.provisioned"), tuple(grp.total_provisioned_mib / 1024 for grp in summary.workload_groups))
    data.add_series(t("pptx.required"), tuple(grp.total_required_mib / 1024 for grp in summary.workload_groups))
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, data).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = _NAVY
    chart.series[1].format.fill.solid()
    chart.series[1].format.fill.fore_color.rgb = _LIGHT_BLUE


def add_sankey_picture(
    slide: Slide, summary: CalculationSummary, x: Length, y: Length, cx: Length, cy: Length
) -> None:
    """Embed the provisioned→required Sankey as a picture. No-op when there is no data."""
    # width_pt/height_pt only set the render aspect ratio; the picture is sized to (cx, cy).
    png = render_sankey_png(summary, width_pt=640, height_pt=240)
    if png is None:
        return
    slide.shapes.add_picture(BytesIO(png), x, y, width=cx, height=cy)
```

- [ ] **Step 4: Run tests to verify the native-chart tests pass**

```bash
.venv/bin/python -m pytest tests/test_pptx_charts.py -v -k "pie or drr or before_after or noop"
```
Expected: PASS for the four native-chart tests (`add_sankey_picture` is covered in Task 5).

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/services/pptx_charts.py tests/test_pptx_charts.py
rtk git commit -m "feat(pptx): native pie/bar chart builders

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Sankey picture builder

**Files:**
- Modify: `tests/test_pptx_charts.py` (add tests; `add_sankey_picture` already implemented in Task 4)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pptx_charts.py`:

```python
def test_add_sankey_picture_adds_picture() -> None:
    slide = _blank_slide()
    pptx_charts.add_sankey_picture(slide, _make_summary(), Inches(1), Inches(1), Inches(8), Inches(3))
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1


def test_add_sankey_picture_noop_on_empty() -> None:
    empty = CalculationSummary([], [], 0, 0.0, 0.0, 0.0, 0.0)
    slide = _blank_slide()
    pptx_charts.add_sankey_picture(slide, empty, Inches(1), Inches(1), Inches(8), Inches(3))
    assert not any(s.shape_type == MSO_SHAPE_TYPE.PICTURE for s in slide.shapes)
```

- [ ] **Step 2: Run to verify pass (implementation done in Task 4)**

```bash
.venv/bin/python -m pytest tests/test_pptx_charts.py -v
```
Expected: PASS — all chart + Sankey tests pass.

- [ ] **Step 3: Commit**

```bash
rtk git add tests/test_pptx_charts.py
rtk git commit -m "test(pptx): cover Sankey picture builder

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: `pptx_report.py` scaffold — title + executive summary

**Files:**
- Create: `src/store_predict/services/pptx_report.py`
- Test: `tests/test_pptx_report.py`

The local `_make_summary` / `_make_perf_summary` / `_make_health_result` helpers used across Tasks 6–9 are copied from `tests/test_excel_report.py` (lines 16–129) and `tests/test_excel_report.py` `TestFindingsSheet._make_health_result` (lines 266–285).

- [ ] **Step 1: Write the failing test**

Create `tests/test_pptx_report.py`:

```python
"""Tests for the PPTX report generator service."""

from __future__ import annotations

from io import BytesIO

from pptx import Presentation

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.pipeline.health_checks import HealthCheckResult, HealthFinding, Severity
from store_predict.services.pptx_report import generate_report_pptx


def _make_summary(
    categories: list[tuple[str, int, float, float]] | None = None,
) -> CalculationSummary:
    if categories is None:
        categories = []
    vm_calcs: list[VMCalculation] = []
    groups: list[WorkloadGroupResult] = []
    for cat_name, count, prov_mib, drr in categories:
        in_use = prov_mib * 0.6
        req = prov_mib / max(drr, 0.1)
        for i in range(count):
            vm_calcs.append(
                VMCalculation(
                    vm_name=f"{cat_name}-VM{i + 1}",
                    workload_category=cat_name,
                    provisioned_mib=prov_mib / count,
                    in_use_mib=in_use / count,
                    drr=drr,
                    required_mib=req / count,
                )
            )
        groups.append(
            WorkloadGroupResult(
                category=cat_name,
                vm_count=count,
                total_provisioned_mib=prov_mib,
                total_in_use_mib=in_use,
                avg_drr=drr,
                total_required_mib=req,
            )
        )
    total_prov = sum(g.total_provisioned_mib for g in groups)
    total_in_use = sum(g.total_in_use_mib for g in groups)
    total_req = sum(g.total_required_mib for g in groups)
    weighted = total_prov / total_req if total_req > 0 else 0.0
    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=len(vm_calcs),
        total_provisioned_mib=total_prov,
        total_in_use_mib=total_in_use,
        total_required_mib=total_req,
        weighted_avg_drr=weighted,
        largest_vm_name=vm_calcs[0].vm_name if vm_calcs else "",
        largest_vm_provisioned_mib=vm_calcs[0].provisioned_mib if vm_calcs else 0.0,
    )


def _make_health_result() -> HealthCheckResult:
    findings = (
        HealthFinding(
            check_id="data_quality.missing_os",
            severity=Severity.WARNING,
            title="health.missing_os.title",
            detail="health.missing_os.detail",
            affected_count=3,
            affected_vms=("vm1", "vm2", "vm3"),
        ),
        HealthFinding(
            check_id="best_practice.tools_not_installed",
            severity=Severity.CRITICAL,
            title="health.tools_not_installed.title",
            detail="health.tools_not_installed.detail",
            affected_count=1,
            affected_vms=("vm1",),
        ),
    )
    return HealthCheckResult(findings=findings, total_vms_checked=10, has_data=True)


def _slide_text(prs: Presentation) -> str:
    """Concatenate all text from all slides for substring assertions."""
    chunks: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                chunks.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        chunks.append(cell.text)
    return "\n".join(chunks)


class TestPptxGeneratesBytes:
    def test_returns_pptx_magic_bytes(self) -> None:
        summary = _make_summary([("Database/Microsoft SQL", 3, 30720.0, 5.0)])
        result = generate_report_pptx(summary, "Test Project")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"  # .pptx is a zip container

    def test_opens_as_presentation_with_title(self) -> None:
        summary = _make_summary([("Database/Microsoft SQL", 3, 30720.0, 5.0)])
        prs = Presentation(BytesIO(generate_report_pptx(summary, "Acme Corp", locale="en")))
        assert len(prs.slides) >= 2
        assert "Acme Corp" in _slide_text(prs)
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'store_predict.services.pptx_report'`.

- [ ] **Step 3: Implement the scaffold + title + exec-summary slides**

Create `src/store_predict/services/pptx_report.py`:

```python
"""PowerPoint report generator for StorePredict sizing decks.

Produces a branded, editable .pptx from a CalculationSummary: a concise
customer-facing pitch deck followed by a technical appendix. Branding matches the
PDF deliverable. Charts that have a native PowerPoint equivalent (pie, column) are
editable; the Sankey is an embedded image.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING

import i18n as _i18n
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from store_predict.i18n import t
from store_predict.services import pptx_charts
from store_predict.services.pdf_report import _layout_metric_rows, format_storage

if TYPE_CHECKING:
    from pptx.slide import Slide

    from store_predict.pipeline.calculation import CalculationSummary
    from store_predict.pipeline.health_checks import HealthCheckResult

__all__ = ["generate_report_pptx"]

# Slide geometry (16:9) and brand colours (match the PDF deliverable).
_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)
_BRAND_NAVY = RGBColor.from_string("1E3A5F")
_WHITE = RGBColor.from_string("FFFFFF")
_DARK = RGBColor.from_string("333333")
_BLANK_LAYOUT = 6  # "Blank" layout in the default template


def _new_blank_slide(prs: Presentation) -> Slide:
    return prs.slides.add_slide(prs.slide_layouts[_BLANK_LAYOUT])


def _add_header_band(slide: Slide, heading: str) -> None:
    """Draw the brand navy band across the top with a white heading."""
    from pptx.enum.shapes import MSO_SHAPE

    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, _SLIDE_W, Inches(1.0))
    band.fill.solid()
    band.fill.fore_color.rgb = _BRAND_NAVY
    band.line.fill.background()
    band.shadow.inherit = False
    tf = band.text_frame
    tf.margin_left = Inches(0.4)
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = heading
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = _WHITE


def _add_text(
    slide: Slide,
    text: str,
    left: Inches,
    top: Inches,
    width: Inches,
    height: Inches,
    *,
    size: int = 18,
    bold: bool = False,
    color: RGBColor = _DARK,
    align: PP_ALIGN = PP_ALIGN.LEFT,
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_kpi_tile(slide: Slide, label: str, value: str, left: Inches, top: Inches, width: Inches) -> None:
    """A navy tile with a small label and a large value."""
    from pptx.enum.shapes import MSO_SHAPE

    tile = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(1.8))
    tile.fill.solid()
    tile.fill.fore_color.rgb = _BRAND_NAVY
    tile.line.fill.background()
    tile.shadow.inherit = False
    tf = tile.text_frame
    tf.word_wrap = True
    p_label = tf.paragraphs[0]
    p_label.alignment = PP_ALIGN.CENTER
    r_label = p_label.add_run()
    r_label.text = label
    r_label.font.size = Pt(12)
    r_label.font.color.rgb = RGBColor.from_string("9DBBD6")
    p_value = tf.add_paragraph()
    p_value.alignment = PP_ALIGN.CENTER
    r_value = p_value.add_run()
    r_value.text = value
    r_value.font.size = Pt(28)
    r_value.font.bold = True
    r_value.font.color.rgb = _WHITE


def _slide_title(prs: Presentation, project_name: str, company_logo_bytes: bytes | None) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.report_title"))
    _add_text(slide, project_name, Inches(0.6), Inches(2.6), Inches(12), Inches(1), size=40, bold=True, color=_BRAND_NAVY)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    _add_text(slide, date_str, Inches(0.6), Inches(3.6), Inches(12), Inches(0.6), size=18)
    if company_logo_bytes:
        slide.shapes.add_picture(BytesIO(company_logo_bytes), Inches(10.8), Inches(0.15), height=Inches(0.7))


def _slide_exec_summary(prs: Presentation, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.exec_summary_heading"))
    tiles = [
        (t("stats.total_vms"), f"{summary.total_vms:,}"),
        (t("stats.total_provisioned"), format_storage(summary.total_provisioned_mib)),
        (t("stats.required_capacity"), format_storage(summary.total_required_mib)),
        (t("stats.avg_drr"), f"{summary.weighted_avg_drr:.1f}x"),
    ]
    top = Inches(2.6)
    width = Inches(2.95)
    for i, (label, value) in enumerate(tiles):
        _add_kpi_tile(slide, label, value, Inches(0.6 + i * 3.15), top, width)


def generate_report_pptx(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    company_logo_bytes: bytes | None = None,
    health_result: HealthCheckResult | None = None,
) -> bytes:
    """Generate a branded PPTX sizing deck and return raw bytes.

    Args:
        summary: Calculation results to render.
        project_name: Customer / project label for the title slide.
        locale: Language for deck labels (e.g. "fr" or "en"). Defaults to "fr".
        company_logo_bytes: Optional customer logo (already validated upstream).
        health_result: Optional health findings; drives the findings slide.

    Returns:
        The .pptx document as bytes.
    """
    # Set the process-global locale before any t() call. Safe: this function is
    # fully synchronous (called via run.io_bound), so there is no coroutine interleaving.
    _i18n.set("locale", locale)

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    _slide_title(prs, project_name, company_logo_bytes)
    _slide_exec_summary(prs, summary)

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py -v
```
Expected: PASS — both scaffold tests pass.

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/services/pptx_report.py tests/test_pptx_report.py
rtk git commit -m "feat(pptx): deck scaffold with title + executive summary

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Main-deck slides — DRR story, workload mix, recommendation

**Files:**
- Modify: `src/store_predict/services/pptx_report.py`
- Modify: `tests/test_pptx_report.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pptx_report.py`:

```python
class TestMainDeck:
    def test_main_deck_has_charts_and_recommendation(self) -> None:
        summary = _make_summary(
            [("Database/Microsoft SQL", 3, 30720.0, 5.0), ("Virtual Machines", 2, 10240.0, 5.0)]
        )
        prs = Presentation(BytesIO(generate_report_pptx(summary, "X", locale="en")))
        # title + exec + drr-story + workload-mix + recommendation = 5 main slides
        assert len(prs.slides) >= 5
        # at least two native charts across the deck (before/after bar + workload pie)
        chart_count = sum(1 for slide in prs.slides for shape in slide.shapes if shape.has_chart)
        assert chart_count >= 2
        text = _slide_text(prs)
        assert "Recommendation" in text  # pptx.recommendation_heading (en)
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py::TestMainDeck -v
```
Expected: FAIL — fewer than 5 slides / heading missing.

- [ ] **Step 3: Implement the three slide builders + wire them in**

In `src/store_predict/services/pptx_report.py`, add these builders (after `_slide_exec_summary`):

```python
def _slide_drr_story(prs: Presentation, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.drr_story_heading"))
    _add_text(
        slide,
        f"{summary.weighted_avg_drr:.1f}x",
        Inches(0.6),
        Inches(1.3),
        Inches(4),
        Inches(1.2),
        size=54,
        bold=True,
        color=_BRAND_NAVY,
    )
    _add_text(slide, t("pdf.weighted_drr"), Inches(0.6), Inches(2.5), Inches(4), Inches(0.6), size=16)
    pptx_charts.add_before_after_bar(slide, summary, Inches(4.8), Inches(1.4), Inches(8.0), Inches(5.4))


def _slide_workload_mix(prs: Presentation, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.workload_mix_heading"))
    pptx_charts.add_workload_pie(slide, summary, Inches(0.6), Inches(1.3), Inches(12), Inches(5.6))


def _slide_recommendation(prs: Presentation, summary: CalculationSummary, health_result: HealthCheckResult | None) -> None:
    from store_predict.pipeline.health_checks import Severity

    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pptx.recommendation_heading"))
    _add_kpi_tile(
        slide, t("stats.required_capacity"), format_storage(summary.total_required_mib), Inches(0.6), Inches(2.0), Inches(5)
    )
    if health_result is not None and health_result.has_data and health_result.findings:
        n_crit = sum(1 for f in health_result.findings if f.severity == Severity.CRITICAL)
        n_warn = sum(1 for f in health_result.findings if f.severity == Severity.WARNING)
        lines = (
            f"{t('pdf.findings_severity_critical')}: {n_crit}    "
            f"{t('pdf.findings_severity_warning')}: {n_warn}"
        )
        _add_text(slide, lines, Inches(0.6), Inches(4.2), Inches(11), Inches(0.8), size=18)
```

Then update `generate_report_pptx` to call them after `_slide_exec_summary`:

```python
    _slide_title(prs, project_name, company_logo_bytes)
    _slide_exec_summary(prs, summary)
    _slide_drr_story(prs, summary)
    _slide_workload_mix(prs, summary)
    _slide_recommendation(prs, summary, health_result)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py -v
```
Expected: PASS — `TestMainDeck` and the scaffold tests pass.

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/services/pptx_report.py tests/test_pptx_report.py
rtk git commit -m "feat(pptx): DRR story, workload mix, recommendation slides

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Appendix slides — breakdown table, layout strategies, findings, charts

**Files:**
- Modify: `src/store_predict/services/pptx_report.py`
- Modify: `tests/test_pptx_report.py`

Conditional guards must match the PDF: layout only when `summary.total_vms > 0`; findings only when `health_result is not None and health_result.has_data and health_result.findings`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pptx_report.py`:

```python
class TestAppendix:
    def test_breakdown_table_present(self) -> None:
        summary = _make_summary([("Database/Microsoft SQL", 3, 30720.0, 5.0)])
        prs = Presentation(BytesIO(generate_report_pptx(summary, "X", locale="en")))
        assert any(shape.has_table for slide in prs.slides for shape in slide.shapes)
        assert "Category" in _slide_text(prs)  # pdf.table_category (en)

    def test_layout_slide_present_with_vms_absent_when_empty(self) -> None:
        with_vms = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        n_with = len(Presentation(BytesIO(generate_report_pptx(with_vms, "X", locale="en"))).slides)
        empty = _make_summary()  # total_vms == 0
        n_empty = len(Presentation(BytesIO(generate_report_pptx(empty, "X", locale="en"))).slides)
        assert n_with > n_empty

    def test_findings_slide_added_only_with_findings(self) -> None:
        summary = _make_summary([("Virtual Machines", 2, 10240.0, 5.0)])
        n_no = len(Presentation(BytesIO(generate_report_pptx(summary, "X", locale="en"))).slides)
        n_yes = len(
            Presentation(
                BytesIO(generate_report_pptx(summary, "X", locale="en", health_result=_make_health_result()))
            ).slides
        )
        assert n_yes == n_no + 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py::TestAppendix -v
```
Expected: FAIL — no table shape / slide counts unchanged.

- [ ] **Step 3: Implement appendix builders + a table helper, then wire them in**

In `src/store_predict/services/pptx_report.py`, add a generic table helper and the appendix builders:

```python
def _add_table(slide: Slide, rows: list[list[str]], left: Inches, top: Inches, width: Inches, height: Inches) -> None:
    """Add a styled table; row 0 is the navy header row."""
    n_rows = len(rows)
    n_cols = len(rows[0])
    table = slide.shapes.add_table(n_rows, n_cols, left, top, width, height).table
    for c in range(n_cols):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = _BRAND_NAVY
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = rows[0][c]
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = _WHITE
    for r in range(1, n_rows):
        for c in range(n_cols):
            cell = table.cell(r, c)
            run = cell.text_frame.paragraphs[0].add_run()
            run.text = rows[r][c]
            run.font.size = Pt(11)
            run.font.color.rgb = _DARK


def _slide_breakdown_table(prs: Presentation, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("report.breakdown_heading"))
    rows: list[list[str]] = [
        [
            t("pdf.table_category"),
            t("pdf.table_vms"),
            t("pdf.table_provisioned"),
            t("pdf.table_avg_drr"),
            t("pdf.table_required"),
        ]
    ]
    for grp in summary.workload_groups:
        rows.append(
            [
                grp.category,
                str(grp.vm_count),
                f"{grp.total_provisioned_mib / 1024:.1f}",
                f"{grp.avg_drr:.2f}",
                f"{grp.total_required_mib / 1024:.1f}",
            ]
        )
    rows.append(
        [
            t("pdf.table_total"),
            str(summary.total_vms),
            f"{summary.total_provisioned_mib / 1024:.1f}",
            f"{summary.weighted_avg_drr:.2f}",
            f"{summary.total_required_mib / 1024:.1f}",
        ]
    )
    _add_table(slide, rows, Inches(0.6), Inches(1.3), Inches(12), Inches(5.5))


def _slide_layout_strategies(prs: Presentation, summary: CalculationSummary) -> None:
    from store_predict.pipeline.layout_engine import generate_all_proposals

    proposals = generate_all_proposals(summary)
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.layout_heading"))
    rows: list[list[str]] = [
        [t("layout_page.metric"), t("strategy.consolidation"), t("strategy.performance"), t("strategy.uniform")]
    ]
    for metric_key, c_val, p_val, u_val in _layout_metric_rows(proposals):
        rows.append([t(f"metrics.{metric_key}"), c_val, p_val, u_val])
    _add_table(slide, rows, Inches(0.6), Inches(1.2), Inches(12), Inches(6.0))


def _slide_findings(prs: Presentation, health_result: HealthCheckResult) -> None:
    from store_predict.pipeline.health_checks import Severity

    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.findings_summary_heading"))
    sev_labels = {
        Severity.CRITICAL: t("pdf.findings_severity_critical"),
        Severity.WARNING: t("pdf.findings_severity_warning"),
        Severity.INFO: t("pdf.findings_severity_info"),
    }
    rows: list[list[str]] = [[t("pdf.findings_col_severity"), t("pdf.findings_col_count")]]
    for sev, label in sev_labels.items():
        count = sum(1 for f in health_result.findings if f.severity == sev)
        if count > 0:
            rows.append([label, str(count)])
    _add_table(slide, rows, Inches(0.6), Inches(1.3), Inches(6), Inches(3))


def _slide_charts(prs: Presentation, summary: CalculationSummary) -> None:
    slide = _new_blank_slide(prs)
    _add_header_band(slide, t("pdf.charts_heading"))
    pptx_charts.add_sankey_picture(slide, summary, Inches(0.6), Inches(1.2), Inches(12), Inches(2.6))
    pptx_charts.add_workload_pie(slide, summary, Inches(0.6), Inches(4.0), Inches(6), Inches(3.2))
    pptx_charts.add_drr_bar(slide, summary, Inches(6.8), Inches(4.0), Inches(6), Inches(3.2))
```

Update `generate_report_pptx` to append the appendix after the main deck:

```python
    # --- Appendix ---
    _slide_breakdown_table(prs, summary)
    if summary.total_vms > 0:
        _slide_layout_strategies(prs, summary)
    if health_result is not None and health_result.has_data and health_result.findings:
        _slide_findings(prs, health_result)
    _slide_charts(prs, summary)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py -v
```
Expected: PASS — `TestAppendix` plus all earlier tests pass.

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/services/pptx_report.py tests/test_pptx_report.py
rtk git commit -m "feat(pptx): appendix slides (breakdown, layout, findings, charts)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: Locale wiring + performance-data tests

**Files:**
- Modify: `tests/test_pptx_report.py`

- [ ] **Step 1: Write the failing/forcing tests**

Append to `tests/test_pptx_report.py`:

```python
class TestPptxLocale:
    def test_en_and_fr_differ(self) -> None:
        summary = _make_summary([("Database/Microsoft SQL", 2, 20480.0, 5.0)])
        en = generate_report_pptx(summary, "X", locale="en")
        fr = generate_report_pptx(summary, "X", locale="fr")
        assert en != fr

    def test_fr_label_present(self) -> None:
        summary = _make_summary([("Virtual Machines", 1, 10240.0, 5.0)])
        prs = Presentation(BytesIO(generate_report_pptx(summary, "X", locale="fr")))
        assert "Synthèse" in _slide_text(prs)  # pptx.exec_summary_heading (fr)

    def test_default_locale_is_fr(self) -> None:
        summary = _make_summary([("Virtual Machines", 1, 10240.0, 5.0)])
        prs = Presentation(BytesIO(generate_report_pptx(summary, "X")))
        assert "Synthèse" in _slide_text(prs)


class TestPptxRobustness:
    def test_empty_summary_still_generates(self) -> None:
        prs = Presentation(BytesIO(generate_report_pptx(_make_summary(), "Empty")))
        assert len(prs.slides) >= 2  # title + exec + breakdown + charts, no layout slide

    def test_logo_bytes_accepted(self) -> None:
        from PIL import Image as PILImage

        buf = BytesIO()
        PILImage.new("RGBA", (4, 4), (0, 0, 0, 0)).save(buf, format="PNG")
        png = buf.getvalue()
        summary = _make_summary([("Virtual Machines", 1, 10240.0, 5.0)])
        result = generate_report_pptx(summary, "X", company_logo_bytes=png)
        assert result[:4] == b"PK\x03\x04"
```

- [ ] **Step 2: Run the tests**

```bash
.venv/bin/python -m pytest tests/test_pptx_report.py -v
```
Expected: PASS. If `test_fr_label_present` fails because a heading wasn't routed through `t()`, fix the offending `_slide_*` builder to use the `t("pptx.*")` key (do not hardcode strings). Re-run until green.

- [ ] **Step 3: Commit**

```bash
rtk git add tests/test_pptx_report.py
rtk git commit -m "test(pptx): locale wiring + robustness coverage

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 10: Wire the PPTX button into the report page

**Files:**
- Modify: `src/store_predict/ui/pages/report.py`
- Test: `tests/test_report_print.py` (add a wiring test) — mirrors how existing report-page tests assert handler/filename wiring without launching a browser.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_report_print.py` (create the file with this content if it does not import what you need; otherwise append the test):

```python
def test_pptx_handler_produces_pptx_bytes() -> None:
    """The report page's PPTX path produces a valid .pptx for a real summary."""
    from store_predict.pipeline.calculation import calculate
    from store_predict.services.pptx_report import generate_report_pptx

    rows = [
        {"vm_name": "SQL01", "workload_category": "Database/Microsoft SQL", "provisioned_mib": 20480.0, "in_use_mib": 12288.0, "drr": 5.0},
        {"vm_name": "WEB01", "workload_category": "Virtual Machines", "provisioned_mib": 10240.0, "in_use_mib": 6144.0, "drr": 5.0},
    ]
    summary = calculate(rows)
    out = generate_report_pptx(summary, "Wiring Test", locale="fr")
    assert out[:4] == b"PK\x03\x04"


def test_report_page_imports_pptx_generator() -> None:
    """report.py must import generate_report_pptx (button wiring)."""
    import store_predict.ui.pages.report as report_mod

    assert hasattr(report_mod, "generate_report_pptx") or "generate_report_pptx" in report_mod.__dict__ or hasattr(
        report_mod, "_on_download_pptx"
    )
```

- [ ] **Step 2: Run to verify the second test fails**

```bash
.venv/bin/python -m pytest tests/test_report_print.py::test_report_page_imports_pptx_generator -v
```
Expected: FAIL — `report.py` does not yet reference `generate_report_pptx` / `_on_download_pptx`.

- [ ] **Step 3: Add the import, button, and handler in `report.py`**

In `src/store_predict/ui/pages/report.py`:

1. Extend the import from `store_predict.services.pptx_report`:
   ```python
   from store_predict.services.pptx_report import generate_report_pptx
   ```

2. After the `excel_btn` definition (around line 199–206), add a third button:
   ```python
            pptx_btn = (
                ui.button(
                    t("report.download_pptx"),
                    icon="slideshow",
                )
                .props("color=secondary")
                .tooltip(t("tooltip.download_pptx"))
            )
   ```

3. Add the handler next to `on_download_excel` (around line 229–234):
   ```python
        async def on_download_pptx() -> None:
            pptx_btn.disable()
            try:
                await _on_download_pptx(summary, project_name, health_result)
            finally:
                pptx_btn.enable()
   ```

4. Register the click next to `excel_btn.on("click", ...)` (around line 249):
   ```python
        pptx_btn.on("click", on_download_pptx)
   ```

5. Add the module-level handler next to `_on_download_excel` (end of file):
   ```python
   async def _on_download_pptx(
       summary: object,
       project_name: str,
       health_result: HealthCheckResult | None = None,
   ) -> None:
       """Generate the PowerPoint deck and trigger a browser download."""
       from store_predict.pipeline.calculation import CalculationSummary

       assert isinstance(summary, CalculationSummary)

       company_logo_b64: str = app.storage.tab.get("company_logo_b64", "")
       company_logo_bytes: bytes | None = base64.b64decode(company_logo_b64) if company_logo_b64 else None

       try:
           pptx_bytes = await run.io_bound(
               generate_report_pptx,
               summary,
               project_name,
               get_locale(),
               company_logo_bytes,
               health_result,
           )
       except Exception:
           ui.notify(t("error.unexpected"), type="negative")
           return

       safe_name = sanitize_filename(project_name)
       date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
       scope_suffix = _scope_filename_suffix()
       filename = f"StorePredict_{safe_name}{scope_suffix}_{date_str}.pptx"
       ui.download(
           pptx_bytes,
           filename=filename,
           media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
       )
   ```

- [ ] **Step 4: Run the wiring tests + the broader page test module**

```bash
.venv/bin/python -m pytest tests/test_report_print.py tests/test_logo_ui_wiring.py -v
```
Expected: PASS.

- [ ] **Step 5: Quality gate + commit**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
rtk git add src/store_predict/ui/pages/report.py tests/test_report_print.py
rtk git commit -m "feat(pptx): add Download PowerPoint button to report page

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 11: Docs, changelog, version bump

**Files:**
- Create: `docs/adr/086-pptx-export.md`
- Modify: `docs/adr/index.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml` (version)

> **Version note:** This feature is a new minor release. The release branch/PR `release/v10.1.0` (PR #26) is the next tagged release. If `v10.1.0` has been merged when this task runs, bump to `10.2.0`. If not yet merged, still use `10.2.0` and resolve the trivial `pyproject.toml`/`CHANGELOG.md` conflict at merge time (this branch will rebase onto the released `main`). Confirm the current released version with `rtk git tag --sort=-creatordate | head -3` before choosing the number.

- [ ] **Step 1: Write the ADR**

Create `docs/adr/086-pptx-export.md`:

```markdown
# ADR-086: PowerPoint (PPTX) export

## Status
Accepted — 2026-05-23

## Context
Pre-sales engineers present StorePredict sizing results to customers in
PowerPoint. The existing PDF and Excel exports cover the technical report and
the data workbook, but not a presentation-ready deliverable.

## Decision
Add a `.pptx` export to the `/report` page using `python-pptx`. The deck is a
hybrid: a concise customer-facing pitch (title, executive summary, DRR story,
workload mix, recommendation) followed by a technical appendix (full breakdown
table, layout strategies, health findings, charts). Charts with a native
PowerPoint equivalent (pie, column) are added as editable charts; the Sankey
flow has no native type and is embedded as an image rendered by the shared
matplotlib renderer (`pdf_charts.render_sankey_png`). Branding matches the PDF
deliverable and the deck is self-contained (no template upload in v1).

The code mirrors the existing export pattern: `services/pptx_report.py`
(composition) + `services/pptx_charts.py` (charts), called from `report.py` via
`run.io_bound` and `ui.download`.

## Consequences
- New runtime dependency: `python-pptx`.
- The Sankey renderer was refactored to a reusable `render_sankey_png()` shared
  by the PDF flowable and the PPTX picture.
- The layout-planner page keeps its own PDF/Excel exports; PPTX is scoped to the
  main report page for now. A corporate-template-injection mode is a possible
  future enhancement.
```

- [ ] **Step 2: Add the ADR to the index**

In `docs/adr/index.md`, add a list entry alongside the other ADRs:

```markdown
- [ADR-086: PowerPoint (PPTX) export](086-pptx-export.md)
```

- [ ] **Step 3: Add a CHANGELOG entry**

In `CHANGELOG.md`, add a new section at the top (above the most recent version section). Use `10.2.0` per the version note:

```markdown
## [10.2.0] - 2026-05-23

### Added

- **PowerPoint (`.pptx`) export** on the report page, alongside PDF and Excel. A
  hybrid deck: a concise customer-facing pitch (title, executive summary, DRR
  story, workload mix, recommendation) plus a technical appendix (full breakdown
  table, layout strategies, health findings, charts). Pie and bar charts are
  native, editable PowerPoint charts; the Sankey is an embedded image. Branding
  matches the PDF deliverable and reuses the company-logo upload. Localized in
  EN/FR/DE/IT. New dependency: `python-pptx`. See
  [ADR-086](adr/086-pptx-export.md).
```

- [ ] **Step 4: Bump the version**

In `pyproject.toml`, set:

```toml
version = "10.2.0"
```

- [ ] **Step 5: Full quality gate + entire test suite**

```bash
rtk ruff format . && rtk ruff check . && rtk mypy src/
.venv/bin/python -m pytest
```
Expected: all tests pass (the existing suite plus the new `test_pptx_*` tests). Build the docs to confirm the ADR renders:
```bash
rtk mkdocs build
```
Expected: build succeeds with no warnings about the new ADR link.

- [ ] **Step 6: Commit**

```bash
rtk git add docs/adr/086-pptx-export.md docs/adr/index.md CHANGELOG.md pyproject.toml
rtk git commit -m "docs(pptx): ADR-086, changelog, version 10.2.0

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] Run the full quality gate and suite once more:
  ```bash
  rtk ruff format . && rtk ruff check . && rtk mypy src/
  .venv/bin/python -m pytest
  ```
- [ ] Manual smoke check: run the app (`.venv/bin/python -m store_predict.main`), upload a sample, go to `/report`, click **Download PowerPoint**, and open the file in PowerPoint/LibreOffice to confirm the deck renders, charts are editable, and the appendix tables are present.
- [ ] Optional security scan on the new modules:
  ```bash
  rtk semgrep --config auto src/store_predict/services/pptx_report.py src/store_predict/services/pptx_charts.py
  ```
- [ ] Hand off to `superpowers:finishing-a-development-branch` to integrate `feat/pptx-export`.

---

## Notes on conventions honored

- **DRY:** the Sankey renderer is shared between PDF and PPTX (Task 3); the layout-strategy rows reuse `_layout_metric_rows`; KPI/table labels reuse existing `stats.*` / `pdf.*` keys.
- **YAGNI:** no corporate-template injection, no PPTX on the layout-planner page, no new chart types.
- **TDD:** every code task writes a failing test first, then the minimal implementation.
- **Security:** the only external input (company logo) is already validated upstream by `pdf_report.validate_logo`; python-pptx XML-escapes all text we set; we only write Open XML, never parse untrusted PPTX; no VM names or DataFrame contents are logged.
```

