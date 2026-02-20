# Phase 13: Graphics - Research

**Researched:** 2026-02-20
**Domain:** Data Visualization — NiceGUI/ECharts (web), ReportLab charts + matplotlib Sankey (PDF)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**What to visualize:**
- Sankey diagram — data reduction flow: Provisioned → Required (core "savings story")
  - Aggregate flow AND per-workload-category breakdown
- Workload category breakdown — pie/donut chart: % of capacity per workload type
- DRR by category — bar chart: which workloads compress best
- Before/after capacity — side-by-side bar: raw provisioned vs required after DRR
Total: 4+ chart types

**Chart placement in PDF:**
- Add a second page dedicated to visuals
- Page 1 unchanged (summary stats + workload breakdown table)
- Page 2 = all charts

**Chart placement in web UI:**
- Charts appear on the report page alongside existing summary cards and table
- Interactive (ECharts) in browser, static equivalents in PDF page 2

**Web UI chart library (LOCKED):**
- NiceGUI `ui.echart` (Apache ECharts) — already in NiceGUI, no extra dep

**PDF chart library (LOCKED):**
- ReportLab built-in charts for bar and pie charts (no extra dep)
- matplotlib for Sankey only — render to PNG buffer via BytesIO, embed via ImageReader (Phase 10 logo pattern)
- `matplotlib>=3.8` added to runtime dependencies
- Import isolated to PDF chart module

**Color scheme (LOCKED):**
- Dell blue (#007DB8) as primary, greys as secondary
- Sankey: Dell blue for "provisioned" node, lighter blue/green for "required" node
- Workload charts: Dell blue + grey tones (not per-category distinct colors)

### Claude's Discretion
- Exact chart dimensions and spacing on PDF page 2
- ECharts theme/option details for web UI
- How to handle very small datasets (1-2 workload categories)

### Deferred Ideas (OUT OF SCOPE)
- New analysis capabilities
- Additional chart types beyond the 4 specified
- Animation or interactivity beyond basic ECharts defaults
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GFX-01 | Web UI report page shows interactive ECharts visualizations (Sankey, pie, bar charts) | NiceGUI 3.7.1 `ui.echart` confirmed present; ECharts Sankey series type verified; `options` property for post-init updates confirmed |
| GFX-02 | PDF report gains a second page with static chart equivalents | ReportLab `PageBreak` flowable confirmed; `onLaterPages` callback for page 2 header; Drawing as Flowable confirmed |
| GFX-03 | Sankey diagram shows Provisioned→Required flow, both aggregate and per-workload | matplotlib.sankey.Sankey API confirmed; flows/labels/orientations pattern verified; PNG-to-BytesIO-to-ImageReader pattern matches Phase 10 logo pattern |
| GFX-04 | Pie/donut chart shows workload category distribution by capacity | ReportLab `Pie` in `reportlab.graphics.charts.piecharts` confirmed; ECharts `type: 'pie'` with `radius` array for donut confirmed |
| GFX-05 | Bar chart shows DRR value by category (which workloads reduce best) | ReportLab `VerticalBarChart` confirmed; ECharts `type: 'bar'` confirmed |
| GFX-06 | Side-by-side bar shows before/after capacity (provisioned vs required) | ReportLab `VerticalBarChart` with grouped data confirmed; ECharts grouped bar with multiple series confirmed |
</phase_requirements>

---

## Summary

Phase 13 adds four chart types to both the web UI report page and a new PDF page 2. The technology stack is fully locked: `ui.echart` (Apache ECharts) for the browser and ReportLab built-in charts plus matplotlib Sankey for the PDF. No new library wiring is needed for the web side — `ui.echart` ships with NiceGUI 3.7.1 (currently installed). Matplotlib is not yet in the runtime dependencies (pyproject.toml currently has `mathplot>=0.1`, which appears to be a placeholder or typo) and must be added as `matplotlib>=3.8`.

The core integration patterns are well understood. For the web UI, charts are created by passing a Python dict matching ECharts option schema to `ui.echart(options)`, and the `chart.options` property allows post-creation mutation followed by `chart.update()`. For the PDF, ReportLab `Drawing` objects containing `VerticalBarChart` or `Pie` instances are directly Flowable and can be appended to the Platypus story; page breaks use `PageBreak()` from `reportlab.platypus`. The matplotlib Sankey → PNG → BytesIO → `ImageReader` pipeline is identical to the existing logo embedding pattern in `_draw_header()`.

Data is sourced entirely from `CalculationSummary.workload_groups` (list of `WorkloadGroupResult`) and the summary totals. No pipeline changes are needed — all required fields (`total_provisioned_mib`, `total_required_mib`, `avg_drr`, `category`, `vm_count`) are already present.

**Primary recommendation:** Create a dedicated `src/store_predict/services/charts.py` module for chart-building helpers shared by both web UI and PDF, exporting separate functions for ECharts options dicts and ReportLab Drawing objects, with matplotlib Sankey isolated to `src/store_predict/services/pdf_charts.py`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NiceGUI `ui.echart` | 3.7.1 (installed) | Interactive ECharts in browser | Ships with NiceGUI, zero extra dep, full Apache ECharts support |
| Apache ECharts | bundled with NiceGUI | Chart rendering engine in browser | Industry standard, supports Sankey, pie, bar, grouped bar natively |
| ReportLab `reportlab.graphics` | 4.0+ (installed) | Static charts in PDF | Already dependency, Drawing is a Platypus Flowable |
| matplotlib | >=3.8 (to be added) | Sankey PNG for PDF only | Only library with mature Sankey support; must be added to pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `reportlab.platypus.PageBreak` | 4.0+ | Force new page in Platypus story | Transition from page 1 to chart page 2 |
| `reportlab.lib.utils.ImageReader` | 4.0+ | Embed PNG BytesIO into PDF canvas | Already used in `_draw_header()` for logos — same pattern for Sankey |
| `reportlab.platypus.Image` | 4.0+ | Embed PNG as Platypus Flowable | Alternative to ImageReader when working with Flowable story |
| `io.BytesIO` | stdlib | In-memory PNG buffer | matplotlib fig.savefig(buffer, format='png') |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| matplotlib Sankey | plotly/pySankey/SankeyFlow | Locked by CONTEXT.md — matplotlib is the decision |
| ReportLab built-in charts | matplotlib for all charts | Would add matplotlib dep for non-Sankey charts; locked decision is to use ReportLab for bar/pie |

**Installation (matplotlib addition only):**
```bash
uv pip install "matplotlib>=3.8"
```

Add to `pyproject.toml` dependencies:
```toml
"matplotlib>=3.8",
```

Note: The existing `mathplot>=0.1` entry appears to be a typo/placeholder for matplotlib. It should be replaced with `matplotlib>=3.8`.

---

## Architecture Patterns

### Recommended Project Structure
```
src/store_predict/
├── services/
│   ├── pdf_report.py          # Existing — add call to render_chart_page()
│   ├── charts.py              # NEW — ECharts options dicts (web UI, no PDF import)
│   └── pdf_charts.py          # NEW — ReportLab Drawing builders + matplotlib Sankey
├── ui/pages/
│   └── report.py              # Existing — add _build_charts_section()
```

### Pattern 1: ECharts Options Builder (Web UI)
**What:** Pure Python functions that return ECharts-compatible option dicts from `CalculationSummary` data.
**When to use:** Called once per chart during `report_page()` render; can be re-called if data refreshes.
**Example:**
```python
# Source: NiceGUI EChart source + Apache ECharts docs
# src/store_predict/services/charts.py

from store_predict.pipeline.calculation import CalculationSummary

DELL_BLUE = "#007DB8"
LIGHT_BLUE = "#40A8D8"
GREY = "#6C757D"
LIGHT_GREY = "#CED4DA"

def echart_sankey_options(summary: CalculationSummary) -> dict:
    """Return ECharts options dict for Provisioned→Required Sankey."""
    nodes = [{"name": "Provisioned", "itemStyle": {"color": DELL_BLUE}}]
    links = []

    for grp in summary.workload_groups:
        nodes.append({"name": grp.category, "itemStyle": {"color": LIGHT_GREY}})
        links.append({
            "source": "Provisioned",
            "target": grp.category,
            "value": round(grp.total_provisioned_mib / 1024, 1),
        })

    required_node = {"name": "Required", "itemStyle": {"color": LIGHT_BLUE}}
    nodes.append(required_node)
    for grp in summary.workload_groups:
        links.append({
            "source": grp.category,
            "target": "Required",
            "value": round(grp.total_required_mib / 1024, 1),
        })

    return {
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [{
            "type": "sankey",
            "layout": "none",
            "data": nodes,
            "links": links,
            "lineStyle": {"color": "gradient", "curveness": 0.5},
            "emphasis": {"focus": "adjacency"},
        }],
    }


def echart_pie_options(summary: CalculationSummary) -> dict:
    """Return ECharts options dict for workload category capacity pie."""
    data = [
        {"value": round(grp.total_provisioned_mib / 1024, 1), "name": grp.category}
        for grp in summary.workload_groups
    ]
    return {
        "tooltip": {"trigger": "item"},
        "legend": {"orient": "vertical", "left": "left"},
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],  # donut
            "data": data,
            "itemStyle": {"color": DELL_BLUE},
            "emphasis": {"itemStyle": {"shadowBlur": 10}},
        }],
    }


def echart_drr_bar_options(summary: CalculationSummary) -> dict:
    """Return ECharts options dict for DRR by workload category."""
    categories = [grp.category for grp in summary.workload_groups]
    values = [round(grp.avg_drr, 2) for grp in summary.workload_groups]
    return {
        "xAxis": {"type": "category", "data": categories,
                  "axisLabel": {"rotate": 30, "overflow": "truncate", "width": 80}},
        "yAxis": {"type": "value", "name": "DRR"},
        "series": [{"type": "bar", "data": values,
                    "itemStyle": {"color": DELL_BLUE}}],
        "tooltip": {"trigger": "axis"},
    }


def echart_before_after_options(summary: CalculationSummary) -> dict:
    """Return ECharts options dict for before/after capacity side-by-side bar."""
    categories = [grp.category for grp in summary.workload_groups]
    provisioned = [round(grp.total_provisioned_mib / 1024, 1) for grp in summary.workload_groups]
    required = [round(grp.total_required_mib / 1024, 1) for grp in summary.workload_groups]
    return {
        "legend": {},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": categories,
                  "axisLabel": {"rotate": 30, "overflow": "truncate", "width": 80}},
        "yAxis": {"type": "value", "name": "GiB"},
        "series": [
            {"name": "Provisioned", "type": "bar", "data": provisioned,
             "itemStyle": {"color": DELL_BLUE}},
            {"name": "Required", "type": "bar", "data": required,
             "itemStyle": {"color": LIGHT_BLUE}},
        ],
    }
```

### Pattern 2: NiceGUI ui.echart Wiring (Web UI)
**What:** Call `ui.echart(options_dict)` inside the report page layout; no extra update needed since data is static at render time.
**When to use:** Inside `report_page()`, after workload breakdown table.
**Example:**
```python
# Source: NiceGUI EChart source (nicegui/elements/echart.py, v3.7.1)
from nicegui import ui
from store_predict.services.charts import echart_sankey_options, echart_pie_options

# Inside report_page() with layout context:
with ui.row().classes("w-full gap-4"):
    ui.echart(echart_sankey_options(summary)).classes("w-full h-64")

with ui.grid().classes("grid grid-cols-2 gap-4 w-full"):
    ui.echart(echart_pie_options(summary)).classes("h-64")
    ui.echart(echart_drr_bar_options(summary)).classes("h-64")
    ui.echart(echart_before_after_options(summary)).classes("h-64 col-span-2")
```

### Pattern 3: ReportLab Chart as Flowable (PDF)
**What:** Create ReportLab `Drawing` with embedded `VerticalBarChart` or `Pie`, then append directly to the Platypus story.
**When to use:** PDF page 2 chart section.
**Example:**
```python
# Source: ReportLab docs ch11_graphics + confirmed via programcreek examples
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib import colors

DELL_BLUE_RL = colors.HexColor("#007DB8")
LIGHT_BLUE_RL = colors.HexColor("#40A8D8")
GREY_RL = colors.HexColor("#6C757D")

def make_drr_bar_drawing(summary: CalculationSummary, width: float = 400, height: float = 180) -> Drawing:
    d = Drawing(width, height)
    bc = VerticalBarChart()
    bc.x, bc.y = 40, 20
    bc.width, bc.height = width - 60, height - 40
    categories = [grp.category[:20] for grp in summary.workload_groups]
    drr_values = tuple(round(grp.avg_drr, 2) for grp in summary.workload_groups)
    bc.data = [drr_values]
    bc.categoryAxis.categoryNames = categories
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.bars[0].fillColor = DELL_BLUE_RL
    bc.valueAxis.valueMin = 0
    d.add(bc)
    return d


def make_pie_drawing(summary: CalculationSummary, width: float = 250, height: float = 200) -> Drawing:
    d = Drawing(width, height)
    pc = Pie()
    pc.x, pc.y = 60, 20
    pc.width, pc.height = 130, 130
    pc.data = [grp.total_provisioned_mib for grp in summary.workload_groups]
    pc.labels = [grp.category[:15] for grp in summary.workload_groups]
    # Dell blue + grey tones for slices
    grey_tones = [colors.HexColor(c) for c in
                  ["#007DB8", "#40A8D8", "#6C757D", "#ADB5BD", "#CED4DA", "#DEE2E6"]]
    for i in range(len(pc.data)):
        pc.slices[i].fillColor = grey_tones[i % len(grey_tones)]
    d.add(pc)
    return d
```

### Pattern 4: matplotlib Sankey → PNG → PDF (Platypus Flowable)
**What:** Render matplotlib Sankey to BytesIO PNG buffer, wrap as `reportlab.platypus.Image`.
**When to use:** PDF page 2 Sankey chart.
**Example:**
```python
# Source: matplotlib.sankey API docs + Phase 10 logo pattern (pdf_report.py _draw_header)
# Import is ISOLATED to this module to avoid matplotlib startup cost for non-PDF paths

def make_sankey_image_flowable(
    summary: CalculationSummary,
    width_pt: float = 500,
    height_pt: float = 200,
) -> "Image":
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend — MUST be set before pyplot import
    import matplotlib.pyplot as plt
    from matplotlib.sankey import Sankey
    from reportlab.platypus import Image

    fig, ax = plt.subplots(figsize=(width_pt / 72, height_pt / 72), dpi=150)
    ax.set_axis_off()
    ax.set_xticks([])
    ax.set_yticks([])

    total_provisioned = summary.total_provisioned_mib
    if total_provisioned == 0:
        plt.close(fig)
        return Image(BytesIO(b""), width=width_pt, height=height_pt)  # empty placeholder

    # Build flows: one positive input (provisioned), N outputs per category
    flows = [total_provisioned]
    labels = ["Provisioned"]
    orientations = [0]  # main trunk goes right

    for grp in summary.workload_groups:
        flows.append(-grp.total_required_mib)
        labels.append(f"{grp.category[:12]}\n{grp.avg_drr:.1f}x")
        orientations.append(-1)  # outputs go down

    scale = 1.0 / total_provisioned if total_provisioned > 0 else 1.0
    sankey = Sankey(ax=ax, scale=scale, offset=0.15, unit="GiB", format="%.0f")
    sankey.add(
        flows=flows,
        labels=labels,
        orientations=orientations,
        pathlengths=[0.2] * len(flows),
        patchlabel="Data\nReduction",
        facecolor="#007DB8",
    )
    diagrams = sankey.finish()
    # Color the last text bold
    diagrams[0].text.set_fontweight("bold")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", transparent=False)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_pt, height=height_pt)
```

### Pattern 5: PDF Page 2 with PageBreak
**What:** Insert `PageBreak()` flowable into story before chart section; use `onLaterPages` callback for header on page 2.
**When to use:** `generate_report_pdf()` story building, after the existing table.
**Example:**
```python
# Source: ReportLab docs ch5_platypus + programcreek PageBreak examples
from reportlab.platypus import PageBreak

# In generate_report_pdf(), after existing table append:
story.append(PageBreak())

# Charts heading
story.append(Paragraph(t("pdf.charts_heading"), heading_style))
story.append(Spacer(1, 10))

# Add Sankey image
story.append(make_sankey_image_flowable(summary))
story.append(Spacer(1, 8))

# Add ReportLab drawings side by side using a Table
chart_row = [[make_pie_drawing(summary), make_drr_bar_drawing(summary)]]
chart_table = Table(chart_row, colWidths=[250, 280])
story.append(chart_table)
story.append(Spacer(1, 8))

# Full-width before/after bar
story.append(make_before_after_bar_drawing(summary, width=500, height=160))

# Pass onLaterPages to apply header to page 2
def on_later_pages(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    _draw_header(canvas, doc, project_name, report_title,
                 dell_logo_preprocessed, company_logo_preprocessed)

doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
```

### Anti-Patterns to Avoid
- **Importing matplotlib at module level in pdf_report.py:** Adds startup overhead and backend conflicts with NiceGUI's event loop. Import inside the function that uses it.
- **Using `matplotlib.use()` after pyplot import:** Must call `matplotlib.use("Agg")` before any `import matplotlib.pyplot` to avoid backend warning.
- **Creating ECharts options inline in report.py:** Move all options dict construction to `charts.py` so the UI code stays clean and the options are unit-testable.
- **Sharing ReportLab `Drawing` references across pages:** ReportLab drawings are mutable; create a new instance per PDF render call.
- **Using per-category distinct colors:** Locked to Dell blue + grey palette. Do not use ECharts default rainbow colors.
- **Calling `plt.show()` in server code:** matplotlib must use the Agg backend (non-interactive); `plt.show()` is a no-op but `plt.close(fig)` is essential to prevent memory leaks.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sankey layout algorithm | Custom arrow/flow drawing | `matplotlib.sankey.Sankey` | Flow proportionality, curved paths, label placement are non-trivial |
| ECharts Sankey node positioning | Custom JS/Python layout | ECharts `type:'sankey'` with `layout:'none'` | Handles overlapping nodes, link curvature, tooltips |
| Chart color cycling | Custom index-based color picker | Fixed Dell palette list (6 entries, `% len`) | Small dataset; consistency with brand is the requirement |
| PNG embedding in PDF | Custom Base64 encoding | `reportlab.platypus.Image(BytesIO(...))` | Handles DPI, aspect ratio, PDF compression internally |
| Page header on page 2 | Separate first-page/later-page story | `doc.build(onFirstPage=..., onLaterPages=...)` | ReportLab's built-in mechanism; no manual page detection needed |

**Key insight:** Both chart stacks (ECharts for web, ReportLab+matplotlib for PDF) already have built-in data-to-visual pipelines. The only custom code needed is data mapping from `WorkloadGroupResult` fields to the expected input schema of each library.

---

## Common Pitfalls

### Pitfall 1: matplotlib Backend Conflict with NiceGUI
**What goes wrong:** Importing matplotlib at module level with the default TkAgg/Qt backend crashes or hangs when NiceGUI is running its asyncio event loop.
**Why it happens:** GUI backends try to interact with display/event loop systems incompatible with NiceGUI's server context.
**How to avoid:** Always set `matplotlib.use("Agg")` before any `import matplotlib.pyplot`, and keep the import inside the function (lazy import pattern).
**Warning signs:** `RuntimeError: main thread is not in main loop` or blank charts when running under NiceGUI.

### Pitfall 2: matplotlib Figure Memory Leak
**What goes wrong:** Each PDF generation creates a new matplotlib figure. Without `plt.close(fig)`, figures accumulate in memory.
**Why it happens:** matplotlib keeps internal references to all open figures.
**How to avoid:** Always call `plt.close(fig)` immediately after `fig.savefig()`. Use a try/finally block.
**Warning signs:** Memory usage grows linearly with PDF downloads over a session.

### Pitfall 3: ECharts Sankey "Source/Target Not Found" Error
**What goes wrong:** ECharts throws a console error and renders no chart when a link's `source` or `target` string does not exactly match a node `name`.
**Why it happens:** ECharts Sankey uses string identity for node lookup — a trailing space or different encoding causes a miss.
**How to avoid:** Use the exact same category string from `workload_groups[i].category` for both the node `name` and the link `source`/`target`. Do not truncate for node data.
**Warning signs:** Chart container renders empty; browser devtools shows "data not found" error.

### Pitfall 4: ReportLab VerticalBarChart Data Format
**What goes wrong:** Passing a flat list `[1.2, 3.4, ...]` as `bc.data` raises a TypeError or renders incorrectly.
**Why it happens:** `VerticalBarChart.data` expects a **list of tuples/lists** (each tuple = one series), not a flat list.
**How to avoid:** Always wrap in an outer list: `bc.data = [(1.2, 3.4, ...)]` for a single series, `[(series_a), (series_b)]` for grouped bars.
**Warning signs:** `AttributeError` on `data[0]`, or only one bar renders.

### Pitfall 5: ECharts Pie Default Rainbow Colors
**What goes wrong:** Without explicit `color` configuration, ECharts Pie renders with its default rainbow palette, violating the Dell brand requirement.
**Why it happens:** ECharts applies its default theme colors automatically.
**How to avoid:** Set a `color` array at the root of the options dict, or set `itemStyle.color` per data item in the series.
**Warning signs:** Chart shows orange, red, purple slices.

### Pitfall 6: PDF Page 2 Missing Header
**What goes wrong:** The branded header bar only appears on page 1; page 2 has no header.
**Why it happens:** `SimpleDocTemplate.build()` only calls `onFirstPage` by default; page 2 uses a blank template unless `onLaterPages` is provided.
**How to avoid:** Pass the same `_draw_header(...)` call in both `on_first_page` and `on_later_pages` callbacks.
**Warning signs:** PDF page 2 has charts but no Dell/company branding header.

### Pitfall 7: Small Dataset (1-2 Workload Categories)
**What goes wrong:** A single-category dataset causes a degenerate Sankey (one input, one output) which looks trivial; a pie with one slice looks like a full circle with no meaningful information.
**Why it happens:** No minimum category count check.
**How to avoid:** Add a guard: if `len(summary.workload_groups) < 2`, skip the Sankey and pie, and show only the bar charts with a note. Or still render but add a tooltip/subtitle explaining the single-category scenario.
**Warning signs:** Sankey with two nodes looks like an arrow, not a flow; pie is a full circle with one label.

---

## Code Examples

Verified patterns from official sources:

### ui.echart Constructor (NiceGUI 3.7.1 source)
```python
# Source: nicegui/elements/echart.py (installed at .venv/lib/python3.14/site-packages/)
from nicegui import ui

chart = ui.echart(
    options={
        "series": [{"type": "sankey", "data": nodes, "links": links}]
    },
    on_point_click=None,   # optional: Handler[EChartPointClickEventArguments]
    on_click=None,         # optional: Handler[EChartComponentClickEventArguments]
    renderer="canvas",     # or "svg"
    theme=None,            # dict or URL string
)

# Post-creation update (options is a property returning _props['options'])
chart.options["series"][0]["data"] = new_nodes
chart.update()  # inherited from Element base class — triggers re-render
```

### ECharts Sankey Options Dict
```python
# Source: Apache ECharts docs + NiceGUI echart discussions #3974
{
    "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
    "series": [{
        "type": "sankey",
        "layout": "none",         # manual node positioning (default for simple flows)
        "data": [                  # nodes list
            {"name": "Provisioned", "itemStyle": {"color": "#007DB8"}},
            {"name": "SQL",          "itemStyle": {"color": "#CED4DA"}},
            {"name": "Required",     "itemStyle": {"color": "#40A8D8"}},
        ],
        "links": [                 # directed edges
            {"source": "Provisioned", "target": "SQL",      "value": 500},
            {"source": "SQL",         "target": "Required", "value": 100},
        ],
        "lineStyle": {
            "color": "gradient",   # inherits gradient from source->target node colors
            "curveness": 0.5,
        },
        "emphasis": {"focus": "adjacency"},
    }],
}
```

### ReportLab PageBreak + onLaterPages
```python
# Source: ReportLab docs ch5_platypus, programcreek PageBreak examples
from reportlab.platypus import PageBreak, SimpleDocTemplate

story = [...]          # page 1 content
story.append(PageBreak())
story.append(...)      # page 2 content

def on_first_page(canvas, doc):
    _draw_header(canvas, doc, ...)

def on_later_pages(canvas, doc):
    _draw_header(canvas, doc, ...)   # same header on all pages

doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
```

### ReportLab Pie as Flowable
```python
# Source: ReportLab docs ch11_graphics
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib import colors

d = Drawing(200, 160)
pc = Pie()
pc.x, pc.y = 50, 15
pc.width, pc.height = 120, 120
pc.data = [300, 150, 75]                    # provisioned_mib per category
pc.labels = ["SQL", "VDI", "Exchange"]
pc.slices[0].fillColor = colors.HexColor("#007DB8")
pc.slices[1].fillColor = colors.HexColor("#6C757D")
pc.slices[2].fillColor = colors.HexColor("#ADB5BD")
d.add(pc)
story.append(d)       # Drawing IS a Platypus Flowable
```

### matplotlib Sankey → BytesIO PNG
```python
# Source: matplotlib.sankey API docs (matplotlib.org/stable/gallery/specialty_plots/sankey_basics.html)
import matplotlib
matplotlib.use("Agg")  # BEFORE pyplot import
import matplotlib.pyplot as plt
from matplotlib.sankey import Sankey
from io import BytesIO

fig, ax = plt.subplots(figsize=(7, 3), dpi=150)
ax.set_axis_off()

sankey = Sankey(ax=ax, scale=0.01, unit="GiB", format="%.0f")
sankey.add(
    flows=[1000, -300, -700],      # positive = input, negative = output
    labels=["Provisioned", "SQL", "Required"],
    orientations=[0, 1, -1],       # right, up, down
    patchlabel="DRR",
    facecolor="#007DB8",
)
diagrams = sankey.finish()

buf = BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
buf.seek(0)

# Embed in Platypus story
from reportlab.platypus import Image
story.append(Image(buf, width=500, height=200))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate chart library (e.g., Chart.js via `ui.add_body_html`) | `ui.echart` native to NiceGUI | NiceGUI ~2.x | No CDN, no custom JS glue code |
| ReportLab canvas-level drawing calls for charts | `Drawing` + `VerticalBarChart`/`Pie` as Flowable | ReportLab 3.x | Charts compose cleanly with text in Platypus story |
| `plt.savefig("file.png")` then read file | `fig.savefig(BytesIO(), format='png')` | matplotlib 3.x | No temp file, no filesystem dependency, works in containers |

**Deprecated/outdated:**
- `EChart._props['enable_3d']` → Use `enable_3d` kwarg in constructor (rename deprecated in NiceGUI 4.0)
- `reportlab.graphics.renderPM.drawToFile` for PNG export → Use Platypus `Image(BytesIO(...))` directly; renderPM has optional dependency on Pillow

---

## Open Questions

1. **`mathplot>=0.1` in pyproject.toml**
   - What we know: This is not matplotlib. It is likely a typo or leftover placeholder from an earlier planning note.
   - What's unclear: Whether it installs anything meaningful (it may fail silently or install a different package).
   - Recommendation: Replace with `matplotlib>=3.8` in pyproject.toml and run `uv pip install "matplotlib>=3.8"` to install.

2. **mypy type stubs for matplotlib**
   - What we know: matplotlib does not ship py.typed; mypy will warn about missing stubs.
   - What's unclear: Whether `matplotlib-stubs` or similar is needed for the CI to pass.
   - Recommendation: Add `[[tool.mypy.overrides]]` for `matplotlib.*` with `ignore_missing_imports = true` in `pyproject.toml`, matching the pattern used for other libraries.

3. **Chart section heading i18n**
   - What we know: A new `pdf.charts_heading` key is needed; all chart axis labels visible in UI need both `en.yaml` and `fr.yaml` entries.
   - What's unclear: Exact French translations for "Data Reduction Flow", "Workload Distribution", "DRR by Category", "Before / After Capacity".
   - Recommendation: Add i18n keys in both locales; plan task should include i18n key additions as a mandatory step.

4. **ECharts Sankey rendering with 1 category**
   - What we know: A single-category workload list produces a trivial Sankey (2 nodes, 2 links).
   - What's unclear: Whether ECharts renders this cleanly or shows an error.
   - Recommendation: Test during implementation; if it renders poorly, add a minimum-2-categories guard that falls back to showing only bar charts.

---

## Sources

### Primary (HIGH confidence)
- NiceGUI installed source — `nicegui/elements/echart.py` v3.7.1 — constructor signature, `options` property, `run_chart_method`, update mechanism confirmed by direct inspection
- `src/store_predict/services/pdf_report.py` — existing `_draw_header()` logo pattern (Phase 10) — BytesIO/ImageReader embedding confirmed
- `src/store_predict/pipeline/calculation.py` — `CalculationSummary`, `WorkloadGroupResult` dataclass fields confirmed
- `pyproject.toml` — current runtime dependencies confirmed; matplotlib NOT currently installed

### Secondary (MEDIUM confidence)
- [NiceGUI ui.echart docs](https://nicegui.io/documentation/echart) — constructor args, update approach, event types
- [matplotlib Sankey basics gallery](https://matplotlib.org/stable/gallery/specialty_plots/sankey_basics.html) — `flows`, `orientations`, `patchlabel`, `finish()`, post-finish customization
- [ReportLab ch11 graphics docs](https://docs.reportlab.com/reportlab/userguide/ch11_graphics/) — `VerticalBarChart`, `Pie`, `Drawing` as Flowable import paths
- [ReportLab ch5 platypus docs](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/) — `onLaterPages`, `PageBreak` usage

### Tertiary (LOW confidence)
- WebSearch results for ECharts Sankey color options — individual node `itemStyle.color` and `lineStyle.color: "gradient"` patterns (needs verification in ECharts 5.x release notes)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries directly inspected or confirmed by existing code
- Architecture: HIGH — patterns derived from existing `pdf_report.py` code + direct NiceGUI source inspection
- Pitfalls: MEDIUM — matplotlib/GUI backend issues well documented; some ECharts rendering edge cases (single category) untested
- i18n key needs: HIGH — inferred from codebase conventions, all existing keys follow same pattern

**Research date:** 2026-02-20
**Valid until:** 2026-03-22 (stable stack; matplotlib Sankey API has not changed in years; NiceGUI 3.x stable)
