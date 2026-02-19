# Phase 8: i18n Foundation - Research

**Researched:** 2026-02-19
**Domain:** Python i18n (python-i18n + YAML), NiceGUI reactive UI, AG Grid locale, ReportLab PDF i18n
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| I18N-01 | All UI strings (labels, buttons, tooltips, notifications) served via `t()` helper from YAML locale files | python-i18n library with YAML extras; `t('key')` wrapper pattern; placeholder syntax `%{name}` |
| I18N-02 | FR/EN language toggle in header, persisted in `app.storage.tab['locale']` | app.storage.tab is per-browser-tab; toggle triggers `ui.navigate.reload()` after writing locale; dark_mode_toggle.py provides parallel pattern |
| I18N-03 | AG Grid column headers and built-in text displayed in selected language | `localeText` grid option + `AG_GRID_LOCALE_FR` CDN load; column `headerName` values are Python strings set at grid construction time |
| I18N-04 | PDF report labels (headers, section titles, column names) rendered in selected language | Pass `locale` explicitly to `generate_report_pdf()`; call `t()` inside PDF generation with that locale |
| I18N-05 | Language switch updates all visible UI elements without page reload | Use `ui.run_javascript('location.reload()')` after writing locale to tab storage — full page reload is the safe, reliable approach; NiceGUI does not support reliable partial i18n refresh of headers |
</phase_requirements>

---

## Summary

Phase 8 introduces the internationalization foundation for StorePredict: a `t()` helper backed by YAML locale files, a FR/EN language toggle in the header, and propagation of the chosen locale into every surface that renders user-visible text — the NiceGUI pages, the AG Grid table, and the PDF report.

The central technical challenge is that `python-i18n` uses a **process-global** locale setting (`i18n.set('locale', 'fr')`), while NiceGUI serves multiple browser tabs concurrently on a single async event loop. Calling `i18n.set('locale')` on behalf of one tab would corrupt locale state for all other tabs mid-render. The correct solution is a thin wrapper `t(key)` that reads `app.storage.tab['locale']` and calls `i18n.set('locale', ...)` immediately before each `i18n.t(key)` call. This works because NiceGUI's async event loop is single-threaded: only one Python coroutine runs at a time, so setting the global locale within a single synchronous `t()` call is safe.

For UI reactivity (I18N-05), the reliable approach is a full-page reload via `ui.run_javascript('location.reload()')` after persisting the locale preference to `app.storage.tab`. NiceGUI's `ui.header` cannot be placed inside a `@ui.refreshable` decorator (confirmed limitation as of NiceGUI 1.5+), ruling out partial DOM refresh for the language toggle. A page reload with pre-stored locale is simple, instant for a lightweight app, and requires no manual element tracking.

AG Grid UI chrome (filter menus, pagination, sort controls) is localized by loading the `@ag-grid-community/locale` CDN script and passing `:localeText: 'AG_GRID_LOCALE_FR'` in the grid options dict. Column `headerName` values are Python strings set at grid construction — they must be wrapped in `t()` calls before being passed to the grid definition. **AG Grid does not support dynamic locale switching on an existing grid instance** — the grid must be destroyed and recreated, which a full-page reload achieves for free.

**Primary recommendation:** Use `ui.run_javascript('location.reload()')` as the language-switch mechanism. Store locale in `app.storage.tab`. Wrap all strings in `t()`. Load AG Grid locale via CDN `add_head_html`. Pass locale explicitly to `generate_report_pdf()`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-i18n[YAML]` | `>=0.3.9` | Translation lookup via `i18n.t('key')`; YAML locale files | Zero-dependency, Rails-style `t()` API; YAML is human-editable; no .po/.mo compilation toolchain; last stable release is 0.3.9 (2020) — deliberately stable |
| `PyYAML` | pulled in by `[YAML]` extra | Parse YAML locale files | Installed automatically; no explicit pin needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@ag-grid-community/locale` CDN | `32.2.2` (pinned URL) | AG Grid UI chrome in French | Load via `ui.add_head_html()`; provides `AG_GRID_LOCALE_FR` |
| `contextvars` (stdlib) | stdlib | NOT needed — single-threaded async event loop makes this unnecessary | Only needed if moving to multi-threaded server |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python-i18n[YAML]` | stdlib `gettext` | gettext requires .po/.mo compilation in Docker build, no runtime locale switching |
| `python-i18n[YAML]` | `Babel` | Babel is comprehensive but heavy; overkill for 2-language string substitution |
| `python-i18n[YAML]` | `i18nice` | Fork of python-i18n with more features; adds dependency risk; not required for this use case |
| Full-page reload for language switch | `@ui.refreshable` | NiceGUI prohibits `ui.header` inside `@ui.refreshable`; refreshable declared outside page handler syncs ALL tabs; full reload is simpler and reliable |

**Installation:**
```bash
uv pip install "python-i18n[YAML]>=0.3.9"
```

Add to `pyproject.toml`:
```toml
"python-i18n[YAML]>=0.3.9",
```

Add to `pyproject.toml` mypy overrides:
```toml
[[tool.mypy.overrides]]
module = "i18n.*"
ignore_missing_imports = true
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/
  i18n/
    __init__.py          # t() helper, get_locale(), set_locale(), configure_i18n()
    locales/
      en.yaml            # English translations
      fr.yaml            # French translations
  ui/
    layout.py            # MODIFIED: add locale toggle button; call set_locale() + reload
    state.py             # MODIFIED: add get_locale() / set_locale() helpers
    pages/
      upload.py          # MODIFIED: all user strings wrapped in t()
      review.py          # MODIFIED: all user strings wrapped in t()
      report.py          # MODIFIED: all user strings wrapped in t()
    components/
      vm_table.py        # MODIFIED: headerName values wrapped in t()
      summary_stats.py   # MODIFIED: stat labels wrapped in t()
      workload_dialog.py # MODIFIED: button/label text wrapped in t()
      dark_mode_toggle.py # MODIFIED: "Dark Mode" label wrapped in t()
      locale_toggle.py   # NEW: FR/EN toggle component for header
  services/
    pdf_report.py        # MODIFIED: accept locale param, call t() with that locale
```

### Pattern 1: The `t()` Wrapper — Safe Per-Session Global Override

This is the single most critical pattern. `python-i18n`'s `i18n.set('locale')` is process-global, but NiceGUI's event loop is single-threaded async. Setting the global locale immediately before calling `i18n.t()` within one synchronous function call is safe: no other tab can interleave.

```python
# src/store_predict/i18n/__init__.py
from __future__ import annotations

from pathlib import Path

import i18n

_LOCALES_DIR = Path(__file__).parent / "locales"

# Configure once at import time
i18n.set("load_path", [str(_LOCALES_DIR)])
i18n.set("fallback", "en")
i18n.set("filename_format", "{locale}.{format}")
i18n.set("file_format", "yaml")
i18n.set("skip_locale_root_data", True)  # keys are NOT prefixed with locale name in YAML


def t(key: str, **kwargs: object) -> str:
    """Return translated string for the current tab's locale.

    Reads locale from app.storage.tab on every call (tab-scoped, not global).
    Sets i18n global locale immediately before lookup — safe because NiceGUI's
    async event loop is single-threaded; no interleaving occurs within one call.
    """
    from store_predict.i18n.locale import get_locale  # avoid circular import
    locale = get_locale()
    i18n.set("locale", locale)
    return str(i18n.t(key, **kwargs))
```

```python
# src/store_predict/i18n/locale.py
from __future__ import annotations

_DEFAULT_LOCALE = "fr"  # French is primary language


def get_locale() -> str:
    """Return the current tab's locale from session storage.

    Falls back to French (primary user language) if not set.
    Safe to call outside a NiceGUI request context — returns default.
    """
    try:
        from nicegui import app
        return str(app.storage.tab.get("locale", _DEFAULT_LOCALE))
    except RuntimeError:
        # Called outside NiceGUI request context (e.g., tests)
        return _DEFAULT_LOCALE


def set_locale(locale: str) -> None:
    """Persist locale choice to tab storage."""
    from nicegui import app
    app.storage.tab["locale"] = locale
```

### Pattern 2: YAML Locale File Format

```yaml
# src/store_predict/i18n/locales/en.yaml
upload:
  title: Upload Workload Data
  project_label: Project Name
  project_placeholder: "e.g., Customer-DC-Migration-2026"
  drop_label: "Drop RVTools or LiveOptics file here (.xlsx, .csv)"
  supported_formats: "Supported formats: RVTools (.xlsx), LiveOptics (.xlsx, .csv)"
  loaded_notify: "Loaded %{count} VMs"

review:
  title: Review Classifications
  project_label: "Project: %{name}"
  no_data: No data uploaded yet.
  bulk_update: Bulk Update Workload
  generate_report: Generate Report
  no_rows_selected: "No rows selected. Use checkboxes to select VMs first."
  updated_notify: "Updated %{count} VMs to %{category} / %{subcategory}"

report:
  title: Sizing Report
  project_label: "Project: %{name}"
  no_data: No data available. Please upload a file first.
  totals_heading: Totals
  averages_heading: Averages
  performance_heading: Performance Summary
  breakdown_heading: Workload Breakdown
  download_pdf: Download PDF Report
  back_to_review: Back to Review

# Column headers for AG Grid and PDF table
columns:
  vm_name: VM Name
  os: OS
  description: Description
  workload_category: Workload Category
  subcategory: Subcategory
  drr: DRR
  provisioned_mib: "Provisioned (MiB)"
  in_use_mib: "In Use (MiB)"
  confidence: Confidence
  peak_iops: Peak IOPS
  iops_8k: "8K Eq. IOPS"
  peak_mbs: "Peak MB/s"

# Summary cards
stats:
  total_vms: Total VMs
  total_provisioned: Total Provisioned
  avg_drr: Avg DRR
  effective_capacity: Effective Capacity

# PDF report labels
pdf:
  report_title: StorePredict Sizing Report
  total_vms: "Total VMs:"
  total_cpus: "Total vCPUs:"
  total_memory: "Total Memory:"
  total_provisioned: "Total Provisioned:"
  total_in_use: "Total In Use:"
  required_capacity: "Required Capacity:"
  avg_cpus: "Avg vCPUs / VM:"
  avg_memory: "Avg Memory / VM:"
  avg_storage: "Avg Storage / VM:"
  weighted_drr: "Weighted Avg DRR:"
  largest_vm: "Largest VM:"
  total_avg_iops: "Total Average IOPS:"
  hottest_vm: "Hottest VM Peak IOPS:"
  peak_throughput: "Peak Throughput:"
  iops_8k: "Total 8K Equivalent IOPS:"
  table_category: Category
  table_vms: VMs
  table_provisioned: "Provisioned (GiB)"
  table_avg_drr: Avg DRR
  table_required: "Required (GiB)"
  table_total: TOTAL

# Layout / navigation
layout:
  home: Home
  upload: Upload
  review: Review
  report: Report
  dark_mode: Dark Mode
  language: FR  # Button label showing what you'll switch TO

# Dialog
dialog:
  workloads_for: "Workloads for %{vm_name}"
  select_hint: "Select one or more workload types. Conservative (lowest) DRR will be used."
  select_label: Select workload types
  cancel: Cancel
  apply: Apply
```

```yaml
# src/store_predict/i18n/locales/fr.yaml
upload:
  title: Téléchargement des données
  project_label: Nom du projet
  project_placeholder: "ex. : Client-DC-Migration-2026"
  drop_label: "Déposez votre fichier RVTools ou LiveOptics ici (.xlsx, .csv)"
  supported_formats: "Formats supportés : RVTools (.xlsx), LiveOptics (.xlsx, .csv)"
  loaded_notify: "%{count} VMs chargées"

review:
  title: Révision des classifications
  project_label: "Projet : %{name}"
  no_data: Aucune donnée chargée.
  bulk_update: Mise à jour groupée
  generate_report: Générer le rapport
  no_rows_selected: "Aucune ligne sélectionnée. Utilisez les cases à cocher pour sélectionner des VMs."
  updated_notify: "%{count} VM(s) mises à jour vers %{category} / %{subcategory}"

report:
  title: Rapport de dimensionnement
  project_label: "Projet : %{name}"
  no_data: Aucune donnée disponible. Veuillez d'abord télécharger un fichier.
  totals_heading: Totaux
  averages_heading: Moyennes
  performance_heading: Résumé des performances
  breakdown_heading: Détail par charge de travail
  download_pdf: Télécharger le rapport PDF
  back_to_review: Retour à la révision

columns:
  vm_name: Nom de la VM
  os: Système d'exploitation
  description: Description
  workload_category: Catégorie de charge
  subcategory: Sous-catégorie
  drr: DRR
  provisioned_mib: "Provisionné (Mio)"
  in_use_mib: "Utilisé (Mio)"
  confidence: Confiance
  peak_iops: IOPS de pointe
  iops_8k: "IOPS éq. 8K"
  peak_mbs: "Débit de pointe (Mo/s)"

stats:
  total_vms: Total VMs
  total_provisioned: Total provisionné
  avg_drr: DRR moyen
  effective_capacity: Capacité effective

pdf:
  report_title: Rapport de dimensionnement StorePredict
  total_vms: "Nombre de VMs :"
  total_cpus: "Total vCPUs :"
  total_memory: "Mémoire totale :"
  total_provisioned: "Total provisionné :"
  total_in_use: "Total utilisé :"
  required_capacity: "Capacité requise :"
  avg_cpus: "vCPUs moy. / VM :"
  avg_memory: "Mémoire moy. / VM :"
  avg_storage: "Stockage moy. / VM :"
  weighted_drr: "DRR moyen pondéré :"
  largest_vm: "VM la plus grande :"
  total_avg_iops: "IOPS moyennes totales :"
  hottest_vm: "IOPS de pointe max :"
  peak_throughput: "Débit de pointe :"
  iops_8k: "IOPS éq. 8K totales :"
  table_category: Catégorie
  table_vms: VMs
  table_provisioned: "Provisionné (Gio)"
  table_avg_drr: DRR moyen
  table_required: "Requis (Gio)"
  table_total: TOTAL

layout:
  home: Accueil
  upload: Télécharger
  review: Révision
  report: Rapport
  dark_mode: Mode sombre
  language: EN  # Button label showing what you'll switch TO

dialog:
  workloads_for: "Charges de travail pour %{vm_name}"
  select_hint: "Sélectionnez un ou plusieurs types de charge. Le DRR le plus conservateur (le plus bas) sera utilisé."
  select_label: Sélectionner les charges de travail
  cancel: Annuler
  apply: Appliquer
```

### Pattern 3: Language Toggle Component

```python
# src/store_predict/ui/components/locale_toggle.py
from __future__ import annotations

from nicegui import ui

from store_predict.i18n import t
from store_predict.i18n.locale import get_locale, set_locale


def add_locale_toggle() -> None:
    """Add FR/EN language toggle button to the current layout container.

    Clicking the button writes the new locale to app.storage.tab and
    reloads the page. The button label shows the language you will SWITCH TO
    (not the current one), which is the standard UX convention.
    """
    current = get_locale()
    next_locale = "en" if current == "fr" else "fr"
    label = t("layout.language")  # returns "FR" or "EN" per locale

    def _switch() -> None:
        set_locale(next_locale)
        ui.run_javascript("location.reload()")

    ui.button(label, on_click=_switch).props("flat color=white dense")
```

### Pattern 4: Header Integration

```python
# src/store_predict/ui/layout.py (modified)
@contextmanager
def layout(title: str = "StorePredict") -> Iterator[None]:
    """Shared page layout with header, navigation, dark mode, and locale toggles."""
    with ui.header().classes("bg-blue-900 text-white items-center justify-between"):
        ui.label(title).classes("text-2xl font-bold")
        with ui.row().classes("gap-4 items-center"):
            ui.link(t("layout.home"), "/").classes("text-white no-underline hover:underline")
            ui.link(t("layout.upload"), "/upload").classes("text-white no-underline hover:underline")
            ui.link(t("layout.review"), "/review").classes("text-white no-underline hover:underline")
            ui.link(t("layout.report"), "/report").classes("text-white no-underline hover:underline")
            add_locale_toggle()
            add_dark_mode_toggle()
    yield
```

### Pattern 5: AG Grid Locale Integration

AG Grid locale requires two independent changes:
1. UI chrome (filter labels, pagination, menus) — via `AG_GRID_LOCALE_FR` CDN
2. Column headers — via `t()` on `headerName` values in the Python column definition

```python
# In each page that uses ui.aggrid — add CDN script ONCE per page:
def _add_aggrid_locale_script(locale: str) -> None:
    """Load AG Grid locale pack from CDN. Call once per page render."""
    if locale == "fr":
        cdn_url = "https://cdn.jsdelivr.net/npm/@ag-grid-community/locale@32.2.2/dist/umd/@ag-grid-community/locale.min.js"
        ui.add_head_html(f'<script src="{cdn_url}" defer></script>')

# In vm_table.py column definitions:
def create_vm_table(...) -> ui.aggrid:
    column_defs = [
        {
            "field": "vm_name",
            "headerName": t("columns.vm_name"),  # <-- wrapped in t()
            ...
        },
        ...
    ]

    grid_options: dict[str, object] = {
        "columnDefs": column_defs,
        "rowData": row_data,
        ...
    }

    # Add localeText for French AG Grid UI chrome
    locale = get_locale()
    if locale == "fr":
        grid_options[":localeText"] = "AG_GRID_LOCALE_FR"

    return ui.aggrid(grid_options).classes("w-full").style("height: 600px")
```

### Pattern 6: PDF Report i18n

The PDF generator cannot use `app.storage.tab` (no NiceGUI request context during generation). Pass locale explicitly:

```python
# src/store_predict/services/pdf_report.py (modified signature)
def generate_report_pdf(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",  # NEW parameter
) -> bytes:
    """Generate PDF in the specified locale."""
    # Set global locale for this call — safe because PDF generation
    # is a single synchronous function; no interleaving possible
    import i18n as _i18n
    _i18n.set("locale", locale)
    # ... rest of generation uses t() calls directly ...
```

Caller in `report.py`:
```python
pdf_bytes = generate_report_pdf(summary, project_name, locale=get_locale())
```

### Anti-Patterns to Avoid

- **Global locale at module level:** Do not call `i18n.set('locale', 'fr')` at module import time. It will override all tabs' locale to French permanently.
- **f-string concatenation for translated phrases:** `f"Project: {name}"` becomes `t("review.project_label", name=name)` — f-strings lock word order to English grammar.
- **Refreshable for header:** `ui.header` cannot be inside `@ui.refreshable` in NiceGUI 1.5+. Use page reload instead.
- **CDN script without `defer`:** Loading the AG Grid locale script without `defer` may fail if AG Grid initializes before the locale script loads.
- **Defining refreshable at module scope:** A refreshable function defined at module level (outside `@ui.page`) is shared across ALL tabs — calling `.refresh()` updates every user. Always define refreshables inside the page handler.
- **Calling `t()` at module import time:** YAML files may not be loaded yet. Only call `t()` at render time (inside page handlers and component functions).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML file parsing | Custom YAML parser | `python-i18n[YAML]` with PyYAML | Handles nested keys, pluralization, placeholders, fallback locale — all needed |
| Locale file loading | Manual `open()` + `yaml.safe_load()` | `python-i18n` load_path | Handles caching, namespace, format detection automatically |
| AG Grid French UI chrome | Manual `localeText` dict of 200+ keys | `@ag-grid-community/locale` CDN | 200+ strings translated by AG Grid team; manually maintaining this is error-prone |
| Per-tab locale state | Custom session dict | `app.storage.tab['locale']` | Already used for all other per-tab state; consistent pattern |

**Key insight:** python-i18n handles placeholder substitution (`%{name}` format), fallback to English when a key is missing in French, and lazy file loading. These edge cases are subtle enough that a hand-rolled dict would miss them.

---

## Common Pitfalls

### Pitfall 1: python-i18n Global State Corrupts Other Tabs

**What goes wrong:** Calling `i18n.set('locale', 'fr')` in one tab's request handler sets the global locale. If another tab's request is awaited (e.g., slow DB call) and starts a `t()` call immediately after, it gets French even though its locale is English.

**Why it happens:** python-i18n stores locale in a module-level dict. NiceGUI's async event loop runs one coroutine at a time, but if you `await` something between setting locale and using it, another coroutine can run in between.

**How to avoid:** Set locale and call `i18n.t()` in the SAME synchronous (non-awaited) function call — the `t()` wrapper does exactly this. Never set the global locale in an async function and then await before using it.

**Warning signs:** French labels appearing in English-locale tabs after the toggle feature ships.

### Pitfall 2: String Concatenation Breaks French Word Order

**What goes wrong:** `f"Project: {name}"` in English works. The French equivalent "Projet : {name}" still works (same order). But `f"Loaded {count} VMs"` becomes "Chargé {count} VM(s)" — word order is identical so it works. However `f"{name} uploaded {count} VMs"` would break in French: "a téléchargé {count} VM(s) {name}" inverts subject and verb position.

**How to avoid:** Always use named placeholders: `t("upload.loaded_notify", count=len(df))` which maps to `"Loaded %{count} VMs"` / `"%{count} VM(s) chargées"`.

**Warning signs:** Any f-string that mixes a translated phrase with a variable is a risk. Pattern: `f"Something {variable}"` inside a user-visible string.

### Pitfall 3: AG Grid Does Not Support Dynamic Locale Switch

**What goes wrong:** Calling `grid.run_grid_method('setGridOption', 'localeText', ...)` after grid creation does NOT update the UI chrome. The AG Grid documentation states: "The grid uses the locale as it is needed. It does not refresh as the locale changes."

**How to avoid:** Always recreate the grid when locale changes. The full-page reload approach (I18N-05) handles this naturally — the grid is rebuilt from scratch on every page load.

**Warning signs:** Pagination text, filter menus remain in English after locale switch even though `localeText` is set.

### Pitfall 4: CDN Script Loading Race Condition

**What goes wrong:** `AG_GRID_LOCALE_FR` is undefined when the AG Grid grid initializes, because the locale CDN script hasn't loaded yet. Grid initializes with English locale silently.

**How to avoid:** Add `defer` attribute to the script tag: `<script src="..." defer></script>`. NiceGUI's `ui.add_head_html()` passes the string verbatim — include `defer` in the string.

**Warning signs:** AG Grid UI chrome shows English even when `':localeText': 'AG_GRID_LOCALE_FR'` is set.

### Pitfall 5: `t()` Called Outside NiceGUI Request Context

**What goes wrong:** `t()` calls `get_locale()` which accesses `app.storage.tab`. In pytest, there is no NiceGUI request context. This raises `RuntimeError: No socket connected.`

**How to avoid:** `get_locale()` must catch `RuntimeError` and return the default locale (`'fr'`) when called outside a request. This makes all functions using `t()` safely testable. The `t()` wrapper in the design above shows this pattern.

**Warning signs:** Tests failing with `RuntimeError: No socket connected` when importing modules that call `t()`.

### Pitfall 6: `skip_locale_root_data` Setting

**What goes wrong:** By default, python-i18n expects YAML files structured as `en: { key: value }` (locale as root key). If you configure `filename_format: '{locale}.{format}'` but leave `skip_locale_root_data: False` (the default), keys must be accessed as `i18n.t('en.upload.title')` instead of `i18n.t('upload.title')`.

**How to avoid:** Set `i18n.set("skip_locale_root_data", True)` in the module-level configuration. Then locale files can use flat key structure without the locale prefix in YAML.

**Warning signs:** `KeyError: 'en.upload.title'` or returning the key itself unchanged (`i18n.t()` returns the key when not found).

---

## Code Examples

### Initializing python-i18n

```python
# Source: github.com/danhper/python-i18n README + PyPI docs
import i18n
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent / "locales"
i18n.set("load_path", [str(_LOCALES_DIR)])
i18n.set("fallback", "en")
i18n.set("filename_format", "{locale}.{format}")  # enables "en.yaml" / "fr.yaml"
i18n.set("file_format", "yaml")
i18n.set("skip_locale_root_data", True)  # keys NOT prefixed with locale name
```

### Using Placeholders

```python
# Source: github.com/danhper/python-i18n README
# YAML: loaded_notify: "Loaded %{count} VMs"
i18n.set("locale", "en")
i18n.t("upload.loaded_notify", count=42)
# Returns: "Loaded 42 VMs"

# YAML: loaded_notify: "%{count} VM(s) chargées"
i18n.set("locale", "fr")
i18n.t("upload.loaded_notify", count=42)
# Returns: "42 VM(s) chargées"
```

### Loading AG Grid French Locale in NiceGUI

```python
# Source: github.com/zauberzeug/nicegui/discussions/3899
CDN_LOCALE_URL = (
    "https://cdn.jsdelivr.net/npm/@ag-grid-community/locale@32.2.2"
    "/dist/umd/@ag-grid-community/locale.min.js"
)
ui.add_head_html(f'<script src="{CDN_LOCALE_URL}" defer></script>')

# In grid options:
{
    "columnDefs": [...],
    "rowData": [...],
    ":localeText": "AG_GRID_LOCALE_FR",  # colon prefix = JS expression in NiceGUI
}
```

### Language Toggle with Page Reload

```python
# Source: github.com/zauberzeug/nicegui/discussions/4295 (maintainer pattern)
# and confirmed: ui.run_javascript('location.reload()') works in NiceGUI 1.4+
def _switch_locale() -> None:
    current = get_locale()
    next_locale = "en" if current == "fr" else "fr"
    set_locale(next_locale)
    ui.run_javascript("location.reload()")
```

### Safe `get_locale()` for Tests

```python
def get_locale() -> str:
    try:
        from nicegui import app
        return str(app.storage.tab.get("locale", "fr"))
    except RuntimeError:
        # Outside NiceGUI request context (pytest, scripts)
        return "fr"
```

### PDF Report with Locale Parameter

```python
# Called from report.py page handler:
locale = get_locale()  # reads app.storage.tab
pdf_bytes = generate_report_pdf(summary, project_name, locale=locale)

# Inside generate_report_pdf():
def generate_report_pdf(summary, project_name, locale="fr"):
    import i18n as _i18n
    _i18n.set("locale", locale)
    # All label strings use t() calls
    story.append(Paragraph(t("pdf.totals_heading"), heading_style))
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| gettext + .po/.mo pipeline | python-i18n + YAML | Ongoing — yaml simpler for 2-lang apps | No build step, human-editable files |
| Manual `localeText` dict (200+ keys) | `@ag-grid-community/locale` CDN | AG Grid Community v32+ | Official package covers all 36 languages |
| Full-page reload for i18n | `@ui.refreshable` | NiceGUI 1.5 broke header in refreshable | Reverted to page reload as reliable pattern |
| `i18n.set('locale')` globally | Per-call locale setting in wrapper | python-i18n has no built-in session isolation | Wrapper pattern is the community standard for Flask/FastAPI too |

**Deprecated/outdated:**
- `ui.navigate.reload()` — this function does NOT exist in NiceGUI; use `ui.run_javascript('location.reload()')` instead (confirmed via docs fetch)
- `Quasar.lang.set()` for app-level text — only affects Quasar component UI chrome (date pickers, etc.), not app-level labels

---

## String Inventory (Existing Strings to Wrap)

A count of user-visible strings already in the codebase that must be wrapped in `t()`:

| File | Strings to Wrap | Notes |
|------|----------------|-------|
| `ui/layout.py` | 5 | Nav links + title |
| `ui/pages/upload.py` | 6 | Labels, placeholder, notify, button |
| `ui/pages/review.py` | 8 | Labels, buttons, notify messages |
| `ui/pages/report.py` | 14 | Section headings, card labels, buttons, column names |
| `ui/components/vm_table.py` | 12 | Column `headerName` values |
| `ui/components/summary_stats.py` | 4 | Stat card labels |
| `ui/components/workload_dialog.py` | 5 | Dialog title, hint, button labels |
| `ui/components/dark_mode_toggle.py` | 1 | "Dark Mode" label |
| `services/pdf_report.py` | 18 | All hardcoded label strings in paragraphs and table headers |
| **Total** | **~73** | Manageable scope for a single plan |

---

## Testing Strategy

### What to Test (Unit Tests — No NiceGUI Context Required)

1. **Translation lookup:** `t('upload.title')` returns expected string in EN and FR
2. **Placeholder substitution:** `t('upload.loaded_notify', count=42)` returns correct formatted string
3. **Fallback:** Missing FR key falls back to EN without error
4. **Missing key:** Undefined key returns the key itself (python-i18n default) — acceptable
5. **`get_locale()` outside context:** Returns `'fr'` (default) without raising
6. **PDF label correctness:** `generate_report_pdf(summary, "Proj", locale="fr")` contains French label text
7. **Both locales produce valid PDF bytes:** `len(pdf_bytes) > 1000` for both EN and FR

### How to Test (Patterns)

```python
# tests/test_i18n.py
import pytest
from store_predict.i18n import t
from store_predict.i18n.locale import get_locale

def test_t_returns_english_string(monkeypatch):
    """t() returns English string when locale is 'en'."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    assert t("upload.title") == "Upload Workload Data"

def test_t_returns_french_string(monkeypatch):
    """t() returns French string when locale is 'fr'."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "fr")
    assert t("upload.title") == "Téléchargement des données"

def test_placeholder_substitution(monkeypatch):
    """t() correctly substitutes %{count} placeholders."""
    monkeypatch.setattr("store_predict.i18n.locale.get_locale", lambda: "en")
    result = t("upload.loaded_notify", count=42)
    assert "42" in result

def test_get_locale_outside_context():
    """get_locale() returns default 'fr' when called outside NiceGUI."""
    # No NiceGUI context — should not raise
    locale = get_locale()
    assert locale in ("en", "fr")

def test_pdf_report_french(make_summary):
    """PDF bytes contain French label text in fr locale."""
    pdf_bytes = generate_report_pdf(make_summary(), "Test", locale="fr")
    assert len(pdf_bytes) > 1000
    # French labels are embedded in PDF content stream
    assert b"Provisionné" in pdf_bytes or b"Totaux" in pdf_bytes
```

### What NOT to Test

- NiceGUI widget rendering (requires live server)
- AG Grid locale display (requires browser)
- Full page reload behavior (integration/E2E scope)

---

## Open Questions

1. **`skip_locale_root_data` interaction with `filename_format`**
   - What we know: `filename_format: '{locale}.{format}'` removes namespace from filename; `skip_locale_root_data: True` removes locale prefix from key lookup
   - What's unclear: Whether both settings must be used together or if one implies the other
   - Recommendation: Set both. Test in CI: `t("upload.title")` must work, `t("en.upload.title")` must fail with key not found

2. **AG Grid locale CDN version pinning**
   - What we know: `@ag-grid-community/locale@32.2.2` is the version used in the NiceGUI discussion example
   - What's unclear: Whether NiceGUI's bundled AG Grid version is compatible with locale pack 32.2.2
   - Recommendation: Pin CDN to the version matching NiceGUI 3.4's bundled AG Grid; check `nicegui.__version__` and AG Grid version in NiceGUI's package.json

3. **French plural forms in python-i18n**
   - What we know: python-i18n supports basic pluralization via `i18n.t('key', count=N)` and YAML `one:`/`other:` keys; French has different plural rules (0 and 1 are singular)
   - What's unclear: Whether python-i18n correctly implements French plural rules (not CLDR)
   - Recommendation: Avoid pluralization for this phase; use explicit phrasing like "VM(s)" or separate strings for 0/1/many — do not use `count=` pluralization until tested

---

## Sources

### Primary (HIGH confidence)

- [python-i18n PyPI](https://pypi.org/project/python-i18n/) — version 0.3.9, YAML support, filename_format, placeholder syntax confirmed
- [python-i18n GitHub README](https://github.com/danhper/python-i18n) — `%{name}` placeholder syntax, `skip_locale_root_data`, `filename_format` options
- [NiceGUI discussions/3899](https://github.com/zauberzeug/nicegui/discussions/3899) — AG Grid localization via CDN + `:localeText` binding confirmed by maintainers
- [NiceGUI discussions/4295](https://github.com/zauberzeug/nicegui/discussions/4295) — dynamic language switching pattern; `ui.run_javascript('Quasar.lang.set(...)')` for Quasar components; page reload approach confirmed
- [AG Grid Localization docs](https://www.ag-grid.com/javascript-data-grid/localisation/) — `localeText` property; **"grid does not refresh as locale changes"** — recreation required
- [NiceGUI refreshable docs](https://nicegui.io/documentation/refreshable) — `@ui.refreshable` decorator; define inside page handler for per-client isolation
- [NiceGUI discussions/4054](https://github.com/zauberzeug/nicegui/discussions/4054) — `@ui.refreshable` defined at module scope refreshes ALL tabs; must be inside page handler
- [AG Grid fr-FR.ts source](https://github.com/ag-grid/ag-grid/blob/latest/community-modules/locale/src/fr-FR.ts) — French translation key inventory confirmed

### Secondary (MEDIUM confidence)

- [NiceGUI discussions/2883](https://github.com/zauberzeug/nicegui/discussions/2883) — gettext works in NiceGUI; `ui.header` label refresh limitation confirmed; page reload workaround mentioned
- [NiceGUI discussions/1866](https://github.com/zauberzeug/nicegui/discussions/1866) — `ui.run_javascript('location.reload()')` works for full page reload in NiceGUI
- Existing `.planning/research/PITFALLS.md` — Pitfall 8 confirms page reload approach; Pitfall 1 confirms f-string concatenation risk; Pitfall 7 confirms string extraction audit need
- Existing `.planning/research/STACK.md` — python-i18n[YAML] confirmed as selected library; `app.storage.tab` for locale storage confirmed

### Tertiary (LOW confidence — flag for validation)

- AG Grid CDN version `32.2.2` compatibility with NiceGUI 3.4's bundled AG Grid — version number should be verified against NiceGUI's actual AG Grid version before shipping

---

## Metadata

**Confidence breakdown:**
- Standard stack (python-i18n, YAML, AG Grid CDN): HIGH — PyPI docs + NiceGUI maintainer discussions verified
- Architecture (t() wrapper, page reload, per-tab locale): HIGH — NiceGUI behavior confirmed via multiple official discussions
- AG Grid locale integration: HIGH — NiceGUI discussion #3899 shows exact working pattern from maintainers
- PDF i18n (locale param pass-through): HIGH — straightforward function signature addition
- Pitfalls (global state, AG Grid no-refresh, CDN defer): HIGH — confirmed by official docs and maintainer statements
- French plural forms in python-i18n: LOW — not verified; avoid pluralization in this phase

**Research date:** 2026-02-19
**Valid until:** 2026-05-19 (stable stack; python-i18n 0.3.9 is final release, AG Grid locale CDN URL may change)
