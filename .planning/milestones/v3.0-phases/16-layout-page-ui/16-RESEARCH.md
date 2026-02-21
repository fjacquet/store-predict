# Phase 16: Layout Page UI - Research

**Researched:** 2026-02-21
**Domain:** NiceGUI UI components — tabs, sliders, select, expansion panels, expandable table rows, session state
**Confidence:** HIGH

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-007 | Advanced Settings Panel — collapsible, 5 tunable parameters, triggers layout re-generation, stored in app.storage.tab | `ui.expansion` confirmed working; `ui.slider`, `ui.select`, `ui.number` all verified from nicegui.io docs; `app.storage.tab` pattern matches existing review/report pages |
| REQ-008 | Layout Page — Comparison View, 3 strategies side-by-side with REQ-005 metrics, visual recommendation indicator, tabs to switch | `ui.tabs` + `ui.tab_panels` confirmed; `ui.table` for comparison grid; icon/color indicator via `ui.icon` + Tailwind color classes |
| REQ-009 | Layout Page — Detail View, per-datastore table with expandable rows to see assigned VMs | `ui.table` with `add_slot('body', ...)` + Quasar `props.expand` toggle confirmed; no AG Grid enterprise needed |
| REQ-010 | Navigation and Guards — add Layout link to nav bar, empty-state card, reads from app.storage.tab | `layout.py` nav bar pattern established; empty-state guard identical to review/report pages |

</phase_requirements>

---

## Summary

Phase 16 adds the `/layout` page — a new NiceGUI page following the exact structural patterns established by `review.py` and `report.py`. It is the UI layer on top of the fully-implemented `generate_all_proposals()` function from Phase 14.

The page divides into two plans: Plan 16-01 covers the Comparison View (3-strategy side-by-side table) and the Advanced Settings panel (collapsible with 5 tunable constraints). Plan 16-02 covers the Detail View (per-datastore table with expandable rows drilling down to assigned VMs).

The critical implementation decisions are: (1) use `ui.table` with `add_slot('body', ...)` for the expandable datastore rows — not `ui.aggrid`, since AG Grid master-detail is enterprise-only and unavailable in NiceGUI's community edition; (2) use `ui.tabs` + `ui.tab_panels` (not toggles or radio buttons) for switching between the three strategy detail views; (3) use `ui.expansion` for the Advanced Settings panel (same component used in the existing rule suggestions panel in `review.py`).

**Primary recommendation:** Implement `ui/pages/layout.py` as a new `@ui.page("/layout")` function following the `report.py` structure — await connection, guard on session data, run `calculate()` + `generate_all_proposals()`, render comparison table, then render tabs for per-strategy detail with expandable datastore rows.

---

## Standard Stack

### Core (all already in project, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nicegui` | existing | All UI components | Project standard |
| `nicegui.app.storage.tab` | existing | Session state persistence | Established pattern across all pages |
| `store_predict.pipeline.calculation` | existing | `calculate()` from vm_data | Same as report.py |
| `store_predict.pipeline.layout_engine` | Phase 14 | `generate_all_proposals()` | The new engine from Phase 14 |
| `store_predict.pipeline.layout_models` | Phase 14 | `PlacementConstraints`, `LayoutProposal`, `DatastoreRecommendation`, `LayoutMetrics` | Dataclass models |
| `store_predict.i18n` | existing | `t()` for all strings | Project convention |
| `store_predict.ui.layout` | existing | `layout()` context manager | All pages use this |

### No New Dependencies

NFR-002 is satisfied — all UI work uses NiceGUI + existing project infrastructure.

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Module Structure

```
src/store_predict/ui/
├── pages/
│   ├── layout_page.py      # NEW: /layout route — Plan 16-01 + 16-02
│   ├── report.py           # Existing — reference pattern
│   └── review.py           # Existing — reference pattern
└── components/
    └── layout_settings.py  # Optional: extract Advanced Settings as component
```

Register in `main.py` with: `import store_predict.ui.pages.layout_page  # noqa: F401`

Add to nav bar in `ui/layout.py`: `ui.link(t("layout.layout"), "/layout").classes("text-white no-underline hover:underline")`

### Pattern 1: Page Guard (Empty State)

Identical to `report.py` and `review.py`. Always first, before any rendering.

```python
# Source: src/store_predict/ui/pages/report.py:36-52
@ui.page("/layout")
async def layout_page() -> None:
    await ui.context.client.connected()
    vm_data: list[dict[str, Any]] | None = app.storage.tab.get("vm_data")
    if not vm_data:
        with (
            layout("StorePredict - Layout"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("upload_file", size="3rem").classes("text-gray-400")
            ui.label(t("layout_page.no_data")).classes("text-xl text-gray-500")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return
```

### Pattern 2: Session State for Constraints (REQ-007)

Store `PlacementConstraints` fields individually in `app.storage.tab`. When settings change, re-build `PlacementConstraints` and call `generate_all_proposals()` again.

```python
# Source: src/store_predict/ui/pages/report.py + state.py patterns
def _load_constraints() -> PlacementConstraints:
    """Read constraint values from tab session, using defaults."""
    return PlacementConstraints(
        max_ds_capacity_mib=app.storage.tab.get("layout_max_ds_mib", 4 * 1024 * 1024),
        max_vms_per_ds=int(app.storage.tab.get("layout_max_vms", 25)),
        iops_budget_per_ds=float(app.storage.tab.get("layout_iops_budget", 100_000.0)),
        snapshot_reserve_pct=float(app.storage.tab.get("layout_snapshot_pct", 15.0)),
        growth_margin_pct=float(app.storage.tab.get("layout_growth_pct", 20.0)),
    )

def _save_constraints(c: PlacementConstraints) -> None:
    app.storage.tab["layout_max_ds_mib"] = c.max_ds_capacity_mib
    app.storage.tab["layout_max_vms"] = c.max_vms_per_ds
    app.storage.tab["layout_iops_budget"] = c.iops_budget_per_ds
    app.storage.tab["layout_snapshot_pct"] = c.snapshot_reserve_pct
    app.storage.tab["layout_growth_pct"] = c.growth_margin_pct
```

### Pattern 3: Advanced Settings Panel (REQ-007)

Use `ui.expansion` — the same component used in `review.py` for the rule suggestions panel (lines 172-176).

```python
# Source: review.py:172-176 (ui.expansion pattern)
# Source: nicegui.io/documentation/expansion
with ui.expansion(
    t("layout_page.settings_title"),
    icon="settings",
    caption=t("layout_page.settings_subtitle"),
).classes("w-full border border-gray-200 rounded-lg"):

    # Max DS capacity — dropdown (2/4/8/16/32/64 TB in MiB)
    TB_OPTIONS = {
        2 * 1024 * 1024: "2 TB",
        4 * 1024 * 1024: "4 TB",
        8 * 1024 * 1024: "8 TB",
        16 * 1024 * 1024: "16 TB",
        32 * 1024 * 1024: "32 TB",
        64 * 1024 * 1024: "64 TB",
    }
    ui.select(
        options=TB_OPTIONS,
        value=constraints.max_ds_capacity_mib,
        label=t("layout_page.max_ds_capacity"),
        on_change=lambda e: _on_settings_change(e, "max_ds_capacity_mib", results_container),
    ).classes("w-full")

    # Max VMs per DS — slider 5-50
    with ui.row().classes("w-full items-center gap-4"):
        ui.label(t("layout_page.max_vms_per_ds")).classes("text-sm min-w-40")
        ui.slider(
            min=5, max=50, step=1,
            value=constraints.max_vms_per_ds,
            on_change=lambda e: _on_settings_change(e, "max_vms_per_ds", results_container),
        ).classes("flex-1")
        ui.label().bind_value_from(slider, "value").classes("text-sm font-mono w-8")

    # IOPS budget — number input
    ui.number(
        label=t("layout_page.iops_budget"),
        value=constraints.iops_budget_per_ds,
        min=10_000, max=1_000_000, step=10_000,
        on_change=lambda e: _on_settings_change(e, "iops_budget_per_ds", results_container),
    ).classes("w-full")

    # Snapshot reserve % — slider 0-30
    ui.slider(min=0, max=30, step=1, value=constraints.snapshot_reserve_pct, ...).classes("flex-1")

    # Growth margin % — slider 0-40
    ui.slider(min=0, max=40, step=1, value=constraints.growth_margin_pct, ...).classes("flex-1")
```

### Pattern 4: Tabs for Strategy Switching (REQ-008)

```python
# Source: nicegui.io/documentation/tabs
with ui.tabs() as strategy_tabs:
    consol_tab = ui.tab(t("strategy.consolidation"), icon="compress")
    perf_tab   = ui.tab(t("strategy.performance"), icon="speed")
    unif_tab   = ui.tab(t("strategy.uniform"), icon="balance")

with ui.tab_panels(strategy_tabs, value=consol_tab).classes("w-full"):
    with ui.tab_panel(consol_tab):
        _build_strategy_detail(proposals[0])
    with ui.tab_panel(perf_tab):
        _build_strategy_detail(proposals[1])
    with ui.tab_panel(unif_tab):
        _build_strategy_detail(proposals[2])
```

### Pattern 5: Comparison Table (REQ-008)

Use `ui.table` (not `ui.aggrid`) for the side-by-side comparison. The table is read-only — no editing needed. Row-per-metric, 4 columns: Metric, Consolidation, Performance, Uniform.

```python
# Source: report.py:103-130 (ui.table pattern)
# Source: nicegui.io/documentation/table
columns = [
    {"name": "metric", "label": t("layout_page.metric"), "field": "metric", "align": "left"},
    {"name": "consolidation", "label": t("strategy.consolidation"), "field": "consolidation", "align": "right"},
    {"name": "performance",   "label": t("strategy.performance"),   "field": "performance",   "align": "right"},
    {"name": "uniform",       "label": t("strategy.uniform"),       "field": "uniform",       "align": "right"},
]
rows = [
    {"metric": t("metrics.ds_count"),       "consolidation": p[0].metrics.total_ds_count,        ...},
    {"metric": t("metrics.raw_capacity"),   "consolidation": _fmt_tib(p[0].metrics.total_raw_capacity_mib), ...},
    {"metric": t("metrics.avg_util"),       "consolidation": f"{p[0].metrics.avg_utilization_pct:.1f}%", ...},
    {"metric": t("metrics.isolation_score"),"consolidation": f"{p[0].metrics.isolation_score:.2f}", ...},
    # ... all REQ-005 metrics
]
ui.table(columns=columns, rows=rows).classes("w-full")
```

### Pattern 6: Expandable Datastore Table with VM Drill-Down (REQ-009)

Use `ui.table` with `add_slot('body', ...)` and `add_slot('header', ...)`. The expand toggle is pure Vue/Quasar via `props.expand`. VM list in the expanded row is rendered as static HTML in the slot template.

```python
# Source: github.com/zauberzeug/nicegui/discussions/574 (verified working)
# Source: nicegui.io/documentation/table
def _build_datastore_table(datastores: tuple[DatastoreRecommendation, ...]) -> None:
    columns = [
        {"name": "expand",    "label": "",             "field": "name"},
        {"name": "name",      "label": t("ds.name"),   "field": "name",     "align": "left"},
        {"name": "raw_cap",   "label": t("ds.raw_cap"),"field": "raw_cap",  "align": "right"},
        {"name": "used",      "label": t("ds.used"),   "field": "used",     "align": "right"},
        {"name": "util_pct",  "label": t("ds.util"),   "field": "util_pct", "align": "right"},
        {"name": "vm_count",  "label": t("ds.vms"),    "field": "vm_count", "align": "right"},
        {"name": "iops",      "label": t("ds.iops"),   "field": "iops",     "align": "right"},
        {"name": "workloads", "label": t("ds.workloads"), "field": "workloads", "align": "left"},
    ]
    rows = [
        {
            "name": ds.name,
            "raw_cap": _fmt_tib(ds.raw_capacity_mib),
            "used": _fmt_tib(ds.used_capacity_mib),
            "util_pct": f"{ds.utilization_pct:.1f}%",
            "vm_count": ds.vm_count,
            "iops": f"{ds.total_iops:,.0f}",
            "workloads": ", ".join(sorted(ds.workload_types)),
            # Embed VM list as newline-separated string for template rendering
            "vm_names": [vm.vm_name for vm in ds.assigned_vms],
        }
        for ds in datastores
    ]

    table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
    table.add_slot('header', r'''
        <q-tr :props="props">
            <q-th auto-width />
            <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
        </q-tr>
    ''')
    table.add_slot('body', r'''
        <q-tr :props="props">
            <q-td auto-width>
                <q-btn size="sm" color="primary" round dense
                       @click="props.expand = !props.expand"
                       :icon="props.expand ? 'expand_less' : 'expand_more'" />
            </q-td>
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td colspan="100%" class="bg-gray-50">
                <div class="p-2">
                    <div class="text-xs font-semibold text-gray-500 mb-1">VMs assigned:</div>
                    <div v-for="vm in props.row.vm_names" :key="vm"
                         class="text-xs font-mono text-gray-700 py-0.5">{{ vm }}</div>
                </div>
            </q-td>
        </q-tr>
    ''')
```

### Pattern 7: Capacity Bar in Table (REQ-009)

For per-datastore mini stats, use a `ui.linear_progress` rendered outside the table (one per datastore card), or encode utilization as a colored badge in the table text. The capacity bar approach works best as a separate `ui.card` layout per datastore if a full card layout is preferred over a pure table.

Two viable approaches — choose based on planner:

**Option A: Pure table with utilization % text + color class** (simpler, no slot complexity)
```python
# Color-code the util_pct cell based on value using Tailwind via slot
# util_pct < 60 → green, 60-80 → yellow, >80 → red
table.add_slot('body-cell-util_pct', r'''
    <q-td :props="props">
        <span :class="props.row.util_pct_raw > 80 ? 'text-red-600 font-bold' :
                      props.row.util_pct_raw > 60 ? 'text-yellow-600' : 'text-green-600'">
            {{ props.value }}
        </span>
    </q-td>
''')
```

**Option B: Progress bar in dedicated column** (more visual, more complexity)
Use `ui.linear_progress(value=util_pct/100)` in a `ui.column` layout outside the table, rendering one card per datastore.

Recommendation: Option A (inline color) for the table row, keep linear_progress only for the datastore cards in a summary header if needed.

### Pattern 8: Recommended Strategy Indicator (REQ-008)

Compute the "recommended" strategy by scoring: prefer highest isolation_score weighted with fewest datastores. Display with a star icon or highlighted column header.

```python
# Source: NiceGUI ui.icon, Tailwind color classes (verified in review.py, report.py)
def _recommend_strategy(proposals: list[LayoutProposal]) -> str:
    """Return strategy_name of the recommended proposal."""
    # Performance strategy is preferred for mixed workload; consolidation for homogeneous
    # Simple heuristic: highest isolation_score wins; ties broken by fewer datastores
    scored = sorted(proposals,
                    key=lambda p: (-p.metrics.isolation_score, p.metrics.total_ds_count))
    return scored[0].strategy_name

# Render visual indicator next to strategy name in comparison table header
# or as a badge: ui.badge("Recommended", color="green") next to the tab label
```

### Pattern 9: Reactive Re-generation on Settings Change

When any Advanced Settings control fires `on_change`, re-run `generate_all_proposals()` and update the results container using `.clear()` + rebuild pattern (same as `_rebuild_stats` in `review.py`).

```python
# Source: review.py:152-156 (_rebuild_stats pattern)
results_container = ui.column().classes("w-full")

def _rebuild_layout(container: ui.column, vm_data: list, constraints: PlacementConstraints) -> None:
    summary = calculate(vm_data)
    proposals = generate_all_proposals(summary, constraints)
    container.clear()
    with container:
        _build_comparison_table(proposals)
        _build_strategy_tabs(proposals)

def _on_settings_change(event, field: str, container: ui.column, vm_data: list) -> None:
    app.storage.tab[f"layout_{field}"] = event.value
    constraints = _load_constraints()
    _rebuild_layout(container, vm_data, constraints)
```

### Anti-Patterns to Avoid

- **Using ui.aggrid for the datastore table:** AG Grid master-detail is enterprise-only and not available in NiceGUI's community edition. Use `ui.table` with `add_slot('body', ...)` instead.
- **Using ui.teleport for expanded row content:** Known DOM rebuilding issues on resize. Use the `props.expand` toggle in the body slot template directly (static HTML in the Vue template).
- **Using global state for constraints:** Store each constraint in `app.storage.tab` with prefixed keys (e.g., `layout_max_ds_mib`) to avoid collision with other page state.
- **Forgetting to re-run `calculate()` before `generate_all_proposals()`:** The vm_data in tab storage is a list of dicts — `calculate()` must be called each time constraints change to produce a fresh `CalculationSummary`.
- **Naming the page module `layout.py`:** That name conflicts with `ui/layout.py` (the shared layout context manager). Name the new module `layout_page.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible settings panel | Custom show/hide toggle | `ui.expansion` | Already used in review.py, battle-tested |
| Strategy switching | Custom button group with visibility | `ui.tabs` + `ui.tab_panels` | NiceGUI native, accessible, handles panel lifecycle |
| Slider inputs | Custom range input | `ui.slider(min, max, step, value)` | NiceGUI native with Quasar QSlider underneath |
| Capacity dropdown | Custom HTML select | `ui.select(options={mib: label})` | Dict options natively maps values to display labels |
| Session state | Custom storage | `app.storage.tab` | Project-wide convention for all pages |
| VM list in expanded row | Separate API call or state | Embed `vm_names` list in row dict | Data is already in proposals — pass through |

**Key insight:** All required UI patterns already have NiceGUI native implementations. The only "unusual" pattern is the expandable table row, which uses `add_slot('body', ...)` with Vue template syntax — a pattern documented in NiceGUI's GitHub discussions.

---

## Common Pitfalls

### Pitfall 1: Module Name Collision

**What goes wrong:** Creating `src/store_predict/ui/pages/layout.py` shadows the existing `src/store_predict/ui/layout.py` in relative imports.

**Why it happens:** Both files are named `layout`. Python import resolution will find the wrong one when using `from store_predict.ui.layout import layout`.

**How to avoid:** Name the new page module `layout_page.py` (the route is still `/layout`).

**Warning signs:** Import errors for `layout()` context manager in the new file.

### Pitfall 2: ui.aggrid Master-Detail Requires Enterprise License

**What goes wrong:** Attempting to use `masterDetail: True` in `ui.aggrid` options — it silently fails or throws a JS console error.

**Why it happens:** AG Grid master-detail is an enterprise feature. NiceGUI ships community edition only.

**How to avoid:** Use `ui.table` with `add_slot('body', ...)` for expandable rows. The Quasar `q-tr / props.expand` pattern provides full expand/collapse with no license required.

**Warning signs:** `masterDetail` config option does nothing, rows don't expand.

### Pitfall 3: Frozen PlacementConstraints Cannot Be Mutated

**What goes wrong:** Trying to update `constraints.max_vms_per_ds = new_value` fails because `PlacementConstraints` is `frozen=True`.

**Why it happens:** All pipeline dataclasses are frozen by project convention.

**How to avoid:** Create a new `PlacementConstraints` instance from `app.storage.tab` values every time settings change. Use `dataclasses.replace()` if building from an existing instance.

**Warning signs:** `FrozenInstanceError` at runtime.

### Pitfall 4: Vue Template Variables in f-strings

**What goes wrong:** Writing `f'<div>{ props.row.name }</div>'` — Python's f-string evaluates the curly braces as Python expressions.

**Why it happens:** Vue templates use `{{ }}` syntax that conflicts with Python f-strings.

**How to avoid:** Use raw strings (`r'''...'''`) for all `add_slot` template content. Never use f-strings for Vue template HTML.

**Warning signs:** `KeyError: 'props'` or template renders empty.

### Pitfall 5: `calculate()` Must Be Called Per-Settings-Change

**What goes wrong:** Caching the `CalculationSummary` and only re-running `generate_all_proposals()` with new constraints — the summary already has `vm_calculations` built from the original data, and IOPS defaults are applied inside `generate_all_proposals()`. This is actually fine since `CalculationSummary` is deterministic from `vm_data`. However, if `vm_data` might change (user navigated to review and back), always reload from `app.storage.tab`.

**How to avoid:** Re-run `calculate(vm_data)` fresh from `app.storage.tab["vm_data"]` each time settings change. It is fast enough (microseconds for typical datasets).

### Pitfall 6: Slider `on_change` Fires on Every Pixel

**What goes wrong:** Settings re-generation fires dozens of times per slider drag, causing UI jank.

**Why it happens:** NiceGUI sliders emit `on_change` on every value change during drag.

**How to avoid:** NiceGUI sliders support `throttle` parameter (via `.props('throttle=500')`). Alternatively, bind slider value to a display label and only trigger re-generation `on_value_change` event when the user releases (check NiceGUI `on_change` vs `on_value_change` semantics).

**Warning signs:** Slow page response when dragging sliders with large VM datasets.

---

## Code Examples

### Complete Page Skeleton

```python
# Source: report.py structure adapted for layout page
# File: src/store_predict/ui/pages/layout_page.py

from __future__ import annotations

from typing import Any
from nicegui import app, ui
from store_predict.i18n import t
from store_predict.pipeline.calculation import calculate
from store_predict.pipeline.layout_engine import generate_all_proposals
from store_predict.pipeline.layout_models import PlacementConstraints, LayoutProposal
from store_predict.ui.layout import layout


@ui.page("/layout")
async def layout_page() -> None:
    """Layout recommendations page with three datastore strategies."""
    await ui.context.client.connected()

    vm_data: list[dict[str, Any]] | None = app.storage.tab.get("vm_data")
    if not vm_data:
        with (
            layout("StorePredict - Layout"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("grid_view", size="3rem").classes("text-gray-400")
            ui.label(t("layout_page.no_data")).classes("text-xl text-gray-500")
            ui.button(t("report.go_to_upload"), on_click=lambda: ui.navigate.to("/upload"), icon="arrow_forward")
        return

    constraints = _load_constraints()
    summary = calculate(vm_data)
    proposals = generate_all_proposals(summary, constraints)

    with layout("StorePredict - Layout"), ui.column().classes("w-full p-4 gap-4"):
        ui.label(t("layout_page.title")).classes("text-2xl font-bold")

        # Advanced Settings (collapsible)
        _build_settings_panel(constraints, vm_data, results_container=None)  # placeholder

        # Results container (comparison + detail tabs)
        results_container = ui.column().classes("w-full")
        with results_container:
            _render_results(proposals)
```

### Navigation Bar Update

```python
# Source: src/store_predict/ui/layout.py — add one line
# BEFORE: ui.link(t("layout.report"), "/report").classes(...)
# AFTER:
ui.link(t("layout.report"),  "/report"). classes("text-white no-underline hover:underline")
ui.link(t("layout.layout"), "/layout").classes("text-white no-underline hover:underline")
```

### Session Key Conventions

```python
# Source: state.py patterns (app.storage.tab key naming)
LAYOUT_SESSION_KEYS = {
    "max_ds_mib": "layout_max_ds_mib",       # int, default 4*1024*1024
    "max_vms":    "layout_max_vms",            # int, default 25
    "iops_budget":"layout_iops_budget",        # float, default 100_000.0
    "snapshot_pct":"layout_snapshot_pct",      # float, default 15.0
    "growth_pct": "layout_growth_pct",         # float, default 20.0
}
```

### MiB Formatting Helper

```python
# Source: pdf_report.py format_storage() pattern — adapt for layout page
def _fmt_tib(mib: float) -> str:
    """Format MiB as TiB with 2 decimal places."""
    return f"{mib / (1024 * 1024):.2f} TiB"

def _fmt_gib(mib: float) -> str:
    """Format MiB as GiB with 1 decimal place."""
    return f"{mib / 1024:.1f} GiB"
```

---

## Existing Codebase Integration Points

### Data Flow

```
app.storage.tab["vm_data"]          # list[dict] — from upload/review pages
    └── calculate(vm_data)          # -> CalculationSummary (same as report.py:55)
        └── generate_all_proposals(summary, constraints)  # -> list[LayoutProposal] (3 items)
            ├── proposals[0]  # consolidation (LayoutProposal)
            ├── proposals[1]  # performance   (LayoutProposal)
            └── proposals[2]  # uniform       (LayoutProposal)
```

### Key Existing APIs to Reuse

| What | Source | How Used in Phase 16 |
|------|--------|----------------------|
| `layout()` context manager | `ui/layout.py` | All pages use `with layout("title"):` |
| `_summary_card()` | `report.py:194-197` | Copy pattern for metrics cards |
| `ui.expansion` | `review.py:172-176` | Advanced Settings panel |
| `app.storage.tab.get("vm_data")` | `report.py:36` | Load session data |
| `ui.table(columns, rows)` | `report.py:130` | Comparison table |
| `_rebuild_stats` pattern | `review.py:152-156` | Re-render results on settings change |
| `ui.notify(...)` | All pages | Error feedback |
| `t()` | All pages | All user-facing strings |

### PlacementConstraints Defaults (from layout_models.py)

```python
# Source: src/store_predict/pipeline/layout_models.py:91-98
max_ds_capacity_mib: float = 4 * 1024 * 1024   # 4 TiB
max_vms_per_ds: int = 25
iops_budget_per_ds: float = 100_000.0
snapshot_reserve_pct: float = 15.0
growth_margin_pct: float = 20.0
```

### LayoutMetrics Fields Available for Comparison Table

```python
# Source: src/store_predict/pipeline/layout_models.py:127-144
total_ds_count: int
total_raw_capacity_mib: float
total_usable_capacity_mib: float
total_used_capacity_mib: float
avg_utilization_pct: float
min_utilization_pct: float
max_utilization_pct: float
avg_vm_density: float
max_vm_density: int
total_iops_placed: float
max_iops_single_ds: float
iops_headroom_pct: float
isolation_score: float          # 0.0-1.0
snapshot_granularity_rating: str  # "fine" | "medium" | "coarse"
oversized_vm_count: int
```

### DatastoreRecommendation Fields for Detail Table

```python
# Source: src/store_predict/pipeline/layout_models.py:111-124
name: str                           # e.g. "DS_CONSOL_01"
raw_capacity_mib: float
usable_capacity_mib: float
assigned_vms: tuple[VMCalculation, ...]  # Iterate for drill-down
used_capacity_mib: float
utilization_pct: float
total_iops: float
vm_count: int
workload_types: frozenset[str]      # For display: sorted(workload_types)
```

---

## i18n Keys Required (REQ-011 — estimated 35-40 keys)

### New keys for `en.yaml` and `fr.yaml`

```yaml
# layout navigation link (add to existing layout: section)
layout:
  layout: Layout  # FR: Disposition

# New top-level section
layout_page:
  title: Datastore Layout Recommendations
  no_data: No calculation data available. Please upload a file first.
  settings_title: Advanced Settings
  settings_subtitle: Adjust constraints to regenerate layouts
  max_ds_capacity: Max Datastore Capacity
  max_vms_per_ds: Max VMs per Datastore
  iops_budget: IOPS Budget per Datastore
  snapshot_reserve: Snapshot Reserve %
  growth_margin: Growth Margin %
  metric: Metric
  recommended: Recommended
  comparison_heading: Strategy Comparison
  detail_heading: "Strategy Detail: %{strategy}"
  no_datastores: No datastores generated for this strategy.

strategy:
  consolidation: Consolidation
  performance: Performance
  uniform: Uniform
  consolidation_desc: Minimize datastore count
  performance_desc: Maximize workload isolation
  uniform_desc: Balanced utilization

metrics:
  ds_count: Datastore Count
  raw_capacity: Raw Capacity (TiB)
  usable_capacity: Usable Capacity (TiB)
  used_capacity: Used Capacity (TiB)
  avg_utilization: Avg Utilization %
  min_utilization: Min Utilization %
  max_utilization: Max Utilization %
  avg_vm_density: Avg VMs/Datastore
  max_vm_density: Max VMs/Datastore
  total_iops: Total IOPS Placed
  max_iops_ds: Max IOPS (single DS)
  iops_headroom: IOPS Headroom %
  isolation_score: Isolation Score
  snapshot_rating: Snapshot Granularity
  oversized_vms: Oversized VMs

ds:
  name: Datastore
  raw_cap: Raw Capacity
  used: Used
  util: Utilization %
  vms: VMs
  iops: IOPS
  workloads: Workload Types
  vm_list: Assigned VMs
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AG Grid for all tables | `ui.table` for read-only, `ui.aggrid` only for editable | NiceGUI patterns | AG Grid master-detail is enterprise — use ui.table for layout page |
| Custom collapse panels | `ui.expansion` (Quasar QExpansionItem) | NiceGUI 1.x | Already used in review.py rule suggestions panel |
| Separate pages per strategy | `ui.tabs` + `ui.tab_panels` on single page | NiceGUI 1.x | Better UX, single route /layout |
| Static pre-computed layouts | Reactive re-generation on settings change | Phase 16 | Settings stored in app.storage.tab, re-generate on change |

---

## Open Questions

1. **Slider throttle mechanism**
   - What we know: NiceGUI sliders fire `on_change` on every increment during drag
   - What's unclear: Whether `.props('throttle=500')` works reliably with Quasar QSlider in NiceGUI's event bridge, or if we should use `on_value_change` (fires on release only)
   - Recommendation: Use `on_change` with a simple debounce via Python (track last-changed timestamp) OR test `.props('throttle=500')` in development — either works, `.props` is simpler

2. **Recommended strategy logic**
   - What we know: REQ-008 says "visual indicator based on workload mix" — not a specific algorithm
   - What's unclear: Exact scoring formula for recommending one strategy over others
   - Recommendation: Recommend "Performance" when `isolation_score > 0.5`; "Consolidation" when homogeneous workloads (single workload category); "Uniform" otherwise. This is a heuristic the planner can refine.

3. **VM list rendering in expanded row**
   - What we know: VM names are strings; `props.row.vm_names` is a list embedded in the row dict
   - What's unclear: How NiceGUI serializes a list field in a row dict for access in the Vue template — needs testing whether `v-for="vm in props.row.vm_names"` works or if we need a joined string
   - Recommendation: Serialize as a joined string `"\n".join(vm_names)` in the row dict to avoid serialization ambiguity; split in the template with CSS white-space handling. Alternatively, store as a list and test in dev — NiceGUI serializes row dicts as JSON so lists should work.

---

## Sources

### Primary (HIGH confidence)

- `src/store_predict/ui/pages/review.py` — full page pattern, ui.expansion usage (lines 172-176), `_rebuild_stats` pattern (152-156)
- `src/store_predict/ui/pages/report.py` — guard pattern, ui.table usage (lines 103-130), `_summary_card` helper
- `src/store_predict/ui/layout.py` — nav bar structure, `layout()` context manager
- `src/store_predict/ui/state.py` — `app.storage.tab` pattern for session keys
- `src/store_predict/pipeline/layout_models.py` — `PlacementConstraints`, `DatastoreRecommendation`, `LayoutMetrics`, `LayoutProposal` dataclass fields
- `src/store_predict/pipeline/layout_engine.py:525-562` — `generate_all_proposals()` signature, return structure
- `nicegui.io/documentation/tabs` — `ui.tabs`, `ui.tab`, `ui.tab_panels`, `ui.tab_panel` API
- `nicegui.io/documentation/expansion` — `ui.expansion` API (value, text, icon, caption, group)
- `nicegui.io/documentation/slider` — `ui.slider` API (min, max, step, value, on_change)
- `nicegui.io/documentation/select` — `ui.select` with dict options {value: label}
- `nicegui.io/documentation/linear_progress` — `ui.linear_progress` for capacity bars (value 0-1)
- `nicegui.io/documentation/table` — `ui.table` with `add_slot('body', ...)` for expandable rows

### Secondary (MEDIUM confidence)

- `github.com/zauberzeug/nicegui/discussions/574` — Confirmed working `props.expand` pattern for expandable rows in ui.table via Quasar scoped slots
- `github.com/zauberzeug/nicegui/discussions/3614` — Confirmed that `ui.teleport` on expansion rows has DOM rebuilding issues; `props.expand` approach is preferred

### Tertiary (LOW confidence)

- WebSearch results on AG Grid master-detail: enterprise feature confirmed unavailable in NiceGUI community edition — verified against discussion #2251 and nicegui-aggrid-enterprise GitHub repo

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all patterns exist in the codebase
- Architecture: HIGH — page structure, guard pattern, session state, nav registration all verified against existing pages
- NiceGUI component APIs: HIGH — verified against official docs for tabs, expansion, slider, select, table expand
- AG Grid master-detail limitation: HIGH — confirmed enterprise-only, verified against NiceGUI discussions
- Pitfalls: HIGH — module naming collision verified by reading imports; frozen dataclass verified in layout_models.py; f-string vs raw string is well-known

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (NiceGUI is stable; `ui.table` expand/collapse pattern is established)
