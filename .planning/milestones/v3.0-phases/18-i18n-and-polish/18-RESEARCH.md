# Phase 18: i18n & Polish — Research

**Researched:** 2026-02-21
**Domain:** Internationalization audit, tooltip/online help, edge-case polish, navigation hardcoding
**Confidence:** HIGH

## Summary

Phase 18 is a polish phase. Phases 14–17 already added ~45+ layout-related i18n keys, so the i18n system is mature and the YAML files are structurally complete (197 keys each in EN and FR, perfectly in sync — 0 parity gaps). The primary remaining work is three-fold:

**First**, there is one confirmed hardcoded user-facing string remaining in the codebase: `"VMs assigned:"` (line 326, `layout_page.py`) inside a Quasar Vue slot template passed via `table.add_slot()`. This string is inside a Python raw-string that generates Vue/HTML, so `t()` cannot be called inline — but the translated string CAN be injected by using Python f-string interpolation before passing the template. Additionally, `report_print.py` has two internal error messages (`"Invalid or expired print token."` and `"No data to print."`) that are user-visible (shown in the Playwright render window) but are internal/developer-facing errors, not end-user-facing strings. These are low priority.

**Second**, online help/tooltips have been explicitly flagged as belonging to Phase 18. Currently zero tooltips exist anywhere in the UI (confirmed by codebase scan). NiceGUI's `.tooltip(text)` method chains onto any element and is the correct approach. This needs FR+EN keys added to both locale YAML files.

**Third**, navigation polish: all `layout("StorePredict - Upload")` style browser tab titles are hardcoded English strings. These are minor (browser tab, not visible in UI body) but can be improved with i18n keys. The charts service (`charts.py`) has hardcoded English node names `"Provisioned"` and `"Required"` in the ECharts Sankey and before/after bar chart options — these appear as chart legend labels visible to end users.

**Primary recommendation:** Fix the `"VMs assigned:"` slot string via f-string injection, add ~15–20 tooltip keys to both locale YAML files with NiceGUI `.tooltip()` method, fix chart legend strings via `t()`, and document the `report_print.py` error strings as intentionally internal.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-011 | i18n — All new UI strings through `t()`: strategy names, metric labels, column headers, advanced settings labels. Both `en.yaml` and `fr.yaml`. Estimated ~30-40 new i18n keys. | Strategy names (`strategy.*`), metric labels (`metrics.*`), column headers (`columns.*`), and advanced settings labels (`layout_page.*`) are already complete from phases 14–17. What remains: 1 hardcoded slot string, ~15-20 tooltip keys, chart legend strings, and `report_print.py` internal errors. |
</phase_requirements>

---

## Standard Stack

### Core (already in use — no changes needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-i18n` | in use | `t()` lookup, YAML loading, `%{var}` substitution, EN fallback | Already wired throughout codebase |
| `nicegui` | in use | `.tooltip(text)` method on all elements | Chainable, zero-dep, confirmed by Context7 docs |
| `yaml` (PyYAML) | in use | Locale file format | Existing convention |

### Supporting (none new required)

No new libraries needed. All i18n infrastructure is in place.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `.tooltip()` method | `ui.tooltip()` as separate widget | `.tooltip()` chains on any element; `ui.tooltip()` requires placement inside a `with element:` block — harder to read. Stick with `.tooltip()`. |
| f-string slot injection | NiceGUI `props` binding | Slot templates are Python raw-strings — f-string interpolation of the already-translated string is the only viable approach here. |

---

## Architecture Patterns

### Current i18n Structure (confirmed)

```
src/store_predict/i18n/locales/
├── en.yaml    # 197 keys (19 top-level sections)
└── fr.yaml    # 197 keys (19 top-level sections, 0 parity gap)
```

**Key count per section:**

| Section | Keys | Status |
|---------|------|--------|
| `home` | 3 | Complete |
| `upload` | 9 | Complete |
| `review` | 7 | Complete |
| `report` | 19 | Complete |
| `columns` | 12 | Complete |
| `stats` | 16 | Complete |
| `pdf` | 31 | Complete |
| `layout` | 7 | Complete (nav links, dark mode, lang toggle) |
| `layout_page` | 15 | Complete |
| `strategy` | 6 | Complete |
| `metrics` | 15 | Complete |
| `ds` | 8 | Complete |
| `dialog` | 5 | Complete |
| `llm` | 6 | Complete |
| `detail_bar` | 7 | Complete |
| `rule_suggestions` | 6 | Complete |
| `storage_model` | 4 | Complete |
| `error` | 2 | Complete |
| `excel` | 19 | Complete |
| **TOTAL** | **197** | **EN == FR (zero gap)** |

### Pattern 1: Tooltip via `.tooltip()` Method (HIGH confidence)

**What:** Chain `.tooltip(text)` on any NiceGUI element. Returns `Self` for chaining.
**When to use:** Any interactive control or metric label where the user might need context.
**Example:**
```python
# Source: https://nicegui.io/documentation/tooltip
from nicegui import ui
from store_predict.i18n import t

ui.slider(min=0, max=30, step=1, value=15) \
    .classes("w-full") \
    .tooltip(t("tooltip.snapshot_reserve"))
```

### Pattern 2: Slot Template F-String Injection (HIGH confidence)

**What:** The `table.add_slot()` body slot is a Python raw-string. To include a translated label, construct the slot string with Python f-string interpolation before passing it.
**When to use:** Any Quasar slot template that needs a localized string.
**Example:**
```python
# Source: layout_page.py pattern analysis
from store_predict.i18n import t

vms_assigned_label = t("ds.vm_list")  # new key: "Assigned VMs" / "VMs assignées"
table.add_slot(
    "body",
    f'''
    <q-tr v-show="props.expand" :props="props">
      <q-td colspan="100%" class="bg-gray-50">
        <div class="p-2">
          <div class="text-sm font-semibold text-gray-600 mb-1">{vms_assigned_label}:</div>
          ...
        </div>
      </q-td>
    </q-tr>
    ''',
)
```

**Note:** `ds.vm_list` already exists in both YAML files (`"Assigned VMs"` / `"VMs assignées"`). No new key needed — the fix is purely in `layout_page.py`.

### Pattern 3: Chart Legend Localization (MEDIUM confidence)

**What:** ECharts node/series `"name"` strings appear in chart legends. Currently `"Provisioned"` and `"Required"` are hardcoded in `charts.py`.
**When to use:** Any chart series label visible in the UI legend.
**Example:**
```python
# Source: src/store_predict/services/charts.py
from store_predict.i18n import t

nodes = [{"name": t("chart.provisioned"), "itemStyle": {"color": DELL_BLUE}}]
nodes.append({"name": t("chart.required"), "itemStyle": {"color": LIGHT_BLUE}})
```
This requires 2 new keys: `chart.provisioned` and `chart.required` in both YAML files.

### Anti-Patterns to Avoid

- **Inline strings in slot templates:** Never embed translated text as Python string literals inside `add_slot()` — use f-string pre-computation.
- **Adding keys only to one locale:** Always add to both `en.yaml` AND `fr.yaml` simultaneously; the test suite validates parity.
- **Translating `report_print.py` error strings:** These are internal developer/ops messages (shown only when Playwright hits an expired token or empty session). They are NOT end-user facing. Leave them in English — they are intentionally outside i18n scope.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip rendering | Custom hover widget | `.tooltip()` on NiceGUI element | One-liner, Quasar-backed, keyboard-accessible |
| Slot i18n | Vue `$t()` or dynamic slot props | Python f-string pre-interpolation | NiceGUI slot templates are static Python strings; f-string is the only viable approach |
| Locale parity check | Manual review | `test_ux_polish.py` pattern (YAML key scan) | Already tested in `test_ux_polish.py::test_i18n_yaml_is_valid` |

---

## Common Pitfalls

### Pitfall 1: Quasar Slot Templates Cannot Call Python
**What goes wrong:** Developer tries `t("key")` inside an `add_slot()` raw-string body. This fails because the slot body is Vue/HTML evaluated client-side — Python code cannot execute there.
**Why it happens:** Confusion between server-side Python rendering and client-side Vue rendering.
**How to avoid:** Always pre-compute translated strings in Python, then inject via f-string interpolation before passing to `add_slot()`.
**Warning signs:** Any `t(` call inside a `r'''...'''` raw-string body.

### Pitfall 2: Tooltip Text Not Available at Module Load Time
**What goes wrong:** Calling `t("tooltip.key")` at module level (outside a function) when locale is not yet set. This can return the wrong locale.
**Why it happens:** `get_locale()` reads from `app.storage.tab` which requires a NiceGUI context.
**How to avoid:** Always call `t()` inside page-render functions (inside `@ui.page` decorated functions), not at module-level.

### Pitfall 3: Chart "name" Fields Are Data Nodes, Not Just Labels
**What goes wrong:** Localizing node names in the Sankey chart breaks the link references. Sankey links use `"source"/"target"` fields that must match node `"name"` values exactly.
**Why it happens:** ECharts Sankey requires `source` and `target` in links to exactly equal the `name` in nodes.
**How to avoid:** When localizing chart nodes, also update the link `source`/`target` values to use the same translated strings. Assign translated name to a variable first:
```python
provisioned_label = t("chart.provisioned")
required_label = t("chart.required")
nodes = [{"name": provisioned_label, ...}]
links = [{"source": provisioned_label, "target": grp.category, ...}]
```

### Pitfall 4: Browser Tab Titles (`layout("StorePredict - Upload")`)
**What goes wrong:** Browser tab titles are hardcoded English in all `layout("StorePredict - X")` calls.
**Why it happens:** These were passed as plain strings; no i18n was applied.
**How to avoid:** Add `page_title.*` keys OR note these as acceptable (browser tab titles are typically not required to be localized for internal tools). The title is also shown in the header as `APP_TITLE` ("StorePredict") which is a product name and should stay untranslated. The subtitle (e.g., "- Upload") is the i18n concern. Decision: Scope to what adds user value.
**Recommendation:** Add `layout.page_upload`, `layout.page_review`, etc. keys OR leave browser tab titles as-is (pre-sales tool, English tab titles are acceptable). Flag as LOW priority.

---

## Code Examples

### Example 1: Adding Tooltip to an Advanced Settings Slider

```python
# Source: nicegui.io/documentation/tooltip + layout_page.py pattern
from store_predict.i18n import t

max_vms_slider = ui.slider(
    min=5, max=50, step=1,
    value=constraints.max_vms_per_ds,
).classes("w-full").props("label-always")
max_vms_slider.tooltip(t("tooltip.max_vms_per_ds"))
```

### Example 2: Tooltip on a Column Header (Detail Bar)

```python
# Source: nicegui.io/documentation/tooltip
from nicegui import ui
from store_predict.i18n import t

with ui.column().classes("gap-0 min-w-28"):
    ui.label(label).classes("text-xs text-gray-500")  \
        .tooltip(t(f"tooltip.{field_key}"))
    ui.label(value).classes("text-sm font-mono")
```

### Example 3: Fixing the Slot "VMs assigned:" Hardcode

```python
# Source: layout_page.py line 286-338, using ds.vm_list key (already exists)
from store_predict.i18n import t

vms_label = t("ds.vm_list")  # "Assigned VMs" (EN) / "VMs assignées" (FR)
table.add_slot(
    "body",
    f'''
    <q-tr v-show="props.expand" :props="props">
      <q-td colspan="100%" class="bg-gray-50">
        <div class="p-2">
          <div class="text-sm font-semibold text-gray-600 mb-1">{vms_label}:</div>
          <div v-for="vm in props.row.vm_names" :key="vm" class="text-sm text-gray-700 ml-2">
            {{{{ vm }}}}
          </div>
        </div>
      </q-td>
    </q-tr>
    ''',
)
```

**IMPORTANT:** Vue double-brace interpolation `{{ vm }}` must be escaped to `{{{{ vm }}}}` in a Python f-string.

---

## Audit: Confirmed Remaining i18n Work

### Confirmed Hardcoded User-Facing Strings

| File | Line | String | Severity | Fix |
|------|------|--------|----------|-----|
| `layout_page.py` | 326 | `"VMs assigned:"` in slot template | HIGH | F-string inject `t("ds.vm_list")` (key already exists) |
| `charts.py` | 35, 38 | `"Provisioned"`, `"Required"` node names (Sankey + before/after chart) | MEDIUM | New `chart.*` keys + fix Sankey link sources |
| `charts.py` | 79 | `"Single category"` (pie subtitle) | LOW | New `chart.single_category` key |
| `charts.py` | 108 | `"DRR"` (y-axis label) | LOW | Could use existing `columns.drr` key |
| `charts.py` | 133 | `"GiB"` (y-axis label in before/after) | LOW | New `chart.gib_unit` key or leave as unit abbreviation |

### Confirmed Internal-Only (Not i18n Scope)

| File | Line | String | Rationale |
|------|------|--------|-----------|
| `report_print.py` | 52 | `"Invalid or expired print token."` | Playwright internal route, never seen by end users |
| `report_print.py` | 63 | `"No data to print."` | Playwright internal route, never seen by end users |
| `layout.py` | 22 | `"StorePredict - Upload"` etc. in `layout()` calls | Browser tab title only; product name acceptable in English |
| All IngestionError messages | various | File format errors, column missing errors | Already tested to be caught + shown via `str(exc)` or `t("error.unexpected")`. These are technical validation messages — consider wrapping in a generic user message. |

### IngestionError Messages — Closer Examination

In `upload.py` line 204: `ui.notify(str(exc), type="negative")` — this passes raw `IngestionError` messages directly to the user. These messages contain technical details like `"Expected columns like 'VM Name' or 'VM OS'. Found: [...]"`. For Phase 18, consider one of:
1. **Leave as-is** (pre-sales engineers are technical, raw messages are informative)
2. **Add a generic wrapper** with a localized prefix: `t("error.ingestion_prefix") + str(exc)`
3. **Fully localize** by adding specific i18n keys for each IngestionError — complex, high effort

**Recommendation:** Option 1 or Option 2. Option 3 is out of scope given complexity.

---

## Proposed New i18n Keys for Phase 18

### Tooltip Keys (~15-20 new keys per locale)

Proposed `tooltip.*` section to add to both YAML files:

```yaml
tooltip:
  # Upload page
  llm_toggle: "Enable AI (LLM) classification for unknown VMs"
  # Review page
  bulk_update: "Apply a workload category to all selected rows"
  storage_model: "Select the target Dell storage platform — affects DRR coefficients"
  # Report page
  download_pdf: "Download a one-page sizing report as PDF"
  download_excel: "Download full data as Excel workbook (4 sheets)"
  upload_logo: "Add your company logo to the PDF report header"
  # Layout page
  max_ds_capacity: "Maximum raw capacity per datastore (TiB)"
  max_vms_per_ds: "Maximum number of VMs that can share one datastore"
  iops_budget: "Maximum IOPS workload per datastore before splitting"
  snapshot_reserve: "Percentage of datastore capacity reserved for snapshots"
  growth_margin: "Additional capacity buffer for future growth"
  # Metrics (in comparison table)
  isolation_score: "0.0 = all workloads mixed; 1.0 = all workloads isolated"
  snapshot_rating: "Qualitative rating: how granularly snapshots can target this layout"
  oversized_vms: "VMs too large to fit in a standard-sized datastore — given dedicated datastores"
  iops_headroom: "Remaining IOPS capacity after workload placement"
```

**Total new keys: ~15 in each locale file = ~30 new i18n keys total** (within the REQ-011 estimate of ~30-40).

### Chart Keys (~5 new keys per locale)

```yaml
chart:
  provisioned: "Provisioned"       # EN / "Provisionné" FR
  required: "Required"              # EN / "Requis" FR
  single_category: "Single category"  # EN / "Catégorie unique" FR
  drr_axis: "DRR"                   # unit label (same in both)
  gib_axis: "GiB"                   # unit label (same in both)
```

---

## Scope Decisions

### In Scope for Phase 18-01

1. Fix `"VMs assigned:"` hardcode in `layout_page.py` slot template (use existing `ds.vm_list` key)
2. Fix chart legend strings in `charts.py` (`"Provisioned"`, `"Required"`, `"Single category"`)
3. Add `tooltip.*` section to both YAML files (~15 keys each)
4. Add `.tooltip(t("tooltip.X"))` to key UI elements across all 4 pages
5. Add `chart.*` section to both YAML files (~5 keys each)
6. Tests: validate tooltip keys exist in both locales, validate slot template uses `ds.vm_list`

### Out of Scope (deliberately)

- Browser tab title localization (`"StorePredict - Upload"` etc.) — product name, acceptable in EN
- `report_print.py` error messages — internal Playwright-only route, not user-facing
- Fully localizing IngestionError messages — high complexity for pre-sales (technical) audience
- Vue `$t()` system — NiceGUI uses Python-side rendering; client-side i18n not needed
- Adding `report.go_to_layout` navigation button (no phase requirement for this)

---

## Edge Cases

### 0 VMs After Upload

**Current behavior:** `calculate()` returns an empty `CalculationSummary`; `layout_page.py` guards `vm_data` presence with the `if not vm_data:` empty-state card. The layout engine is not called when `vm_data` is empty.
**Status:** Handled. No action needed.

### Single VM

**Current behavior:** `generate_all_proposals()` with 1 VM creates 1 datastore in each strategy. The Sankey chart falls back to `echart_before_after_options()` when `len(workload_groups) < 2` — this is handled already.
**Status:** Handled. No action needed.

### Oversized VMs

**Current behavior:** `layout_engine.py` separates VMs whose `required_mib > usable_capacity_mib` and gives each a dedicated datastore (named `..._OVER_...`). The `oversized_vm_count` metric is surfaced in the comparison table and PDF.
**Phase 18 concern:** The `metrics.oversized_vms` key already exists and is translated in both locales. The number shown in the UI is purely numeric. If `oversized_vm_count > 0`, the user gets a count — no additional warning message exists.
**Recommendation:** Add an `oversized_vms_warning` tooltip or contextual label when count > 0, explaining what an oversized VM is and what the dedicated datastore means. This adds clarity for pre-sales users. Add key `tooltip.oversized_vms` (already in proposed tooltip list).

---

## Navigation Polish

### Current Navigation Architecture

All pages use `layout("StorePredict - Upload")` etc. The `layout()` context manager:
1. Renders a `ui.header` with the title + nav links + toggles
2. The title in the header is the string argument (e.g., `"StorePredict - Upload"`)

### What's Already Good

- Nav links (`Home`, `Upload`, `Review`, `Report`, `Layout`) are all localized via `t("layout.X")`
- `Dark Mode` toggle is localized
- Language toggle (`FR`/`EN`) is localized
- All empty-state cards use `ui.button` (not `ui.link`) — already validated by `test_ux_polish.py`

### What Needs Polish

- **Active page indicator:** The nav bar has no visual highlighting for the current page. Adding CSS `font-bold` or `underline` to the active link would improve UX. This requires comparing the current URL against each nav link.
- **Browser tab titles:** Hardcoded `"StorePredict - Upload"` etc. Low priority; acceptable as-is for a pre-sales tool.

**Recommendation for Phase 18:** Add active-page CSS highlighting to `layout.py` nav links. This is navigation polish without i18n implications.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All UI strings hardcoded | All strings via `t()` | Phases 12-17 | Full FR/EN support |
| No tooltips anywhere | To be added in Phase 18 | Phase 18 | Contextual help for pre-sales |
| No layout page | Full layout page with 3 strategies | Phases 14-16 | New feature complete |
| No PDF/Excel layout | Layout in both exports | Phase 17 | Export complete |

---

## Open Questions

1. **IngestionError localization scope**
   - What we know: Raw error messages (technical column names, sheet names) are shown to users via `str(exc)` in upload.py line 204
   - What's unclear: Whether pre-sales engineers benefit from technical details or a friendly French message
   - Recommendation: Keep raw messages (pre-sales engineers are technical); add a generic `error.ingestion_hint` key as a prefix if desired

2. **Active page highlighting in nav**
   - What we know: `layout.py` builds all nav links but has no URL-awareness
   - What's unclear: How to get the current URL in the `layout()` context (NiceGUI provides `ui.context.client.page.url` but may require async context)
   - Recommendation: Use a CSS class approach — pass an optional `active_page` parameter to `layout()` and compare against link targets

3. **Chart legend strings in ECharts**
   - What we know: `"Provisioned"` and `"Required"` appear in Sankey nodes AND before/after bar series; Sankey links reference these by name
   - What's unclear: Whether the Sankey chart's locale-aware node names would break if categories contain special characters
   - Recommendation: Pre-compute translated names as variables and use consistently in both nodes and links

---

## Sources

### Primary (HIGH confidence)
- Codebase scan of `/Users/fjacquet/Projects/store-predict/src/store_predict/` — confirmed by direct file reading
- `/website/nicegui_io` via Context7 — `.tooltip(text)` method confirmed, chainable on any element
- `en.yaml` and `fr.yaml` direct reading — 197 keys each, zero parity gap confirmed

### Secondary (MEDIUM confidence)
- Phase 16 VERIFICATION.md — confirms 40+ layout i18n keys were added in phase 16
- Phase 17 VERIFICATION.md — confirms PDF/Excel layout i18n keys added in phase 17

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing infrastructure, no new libraries
- Architecture: HIGH — patterns confirmed by direct codebase analysis
- Pitfalls: HIGH — slot template constraint verified by reading actual code
- i18n key audit: HIGH — computed by Python AST + YAML parsing of actual files
- Tooltip count estimate: MEDIUM — count of ~15 keys is an estimate based on UI element scan

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable codebase; 30-day validity)
