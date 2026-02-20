# Phase 8: i18n Foundation - Research

**Researched:** 2026-02-19
**Domain:** Python i18n (python-i18n + YAML), NiceGUI reactive UI, AG Grid locale, ReportLab PDF i18n
**Confidence:** HIGH

## Summary

Phase 8 introduces the internationalization foundation for StorePredict: a `t()` helper backed by YAML locale files, a FR/EN language toggle in the header, and propagation of the chosen locale into every surface that renders user-visible text — NiceGUI pages, the AG Grid table, and the PDF report. French is the primary locale; English is the fallback. All UI strings must go through `t()` — hardcoded text in the UI layer is a lint violation.

## Key Findings

### t() Helper Pattern

`python-i18n` with YAML extras provides the `t()` function. Wrap it in a project-level helper that reads `app.storage.tab['locale']` so callers need no locale argument.

```python
# src/store_predict/i18n/__init__.py
import i18n as _i18n
from nicegui import app

_i18n.set("file_format", "yaml")
_i18n.set("filename_format", "{locale}.{format}")
_i18n.set("load_path", [str(Path(__file__).parent / "locales")])
_i18n.set("fallback", "en")

def t(key: str, **kwargs: object) -> str:
    locale = app.storage.tab.get("locale", "fr")
    return _i18n.t(key, locale=locale, **kwargs)
```

Placeholder syntax uses `%{name}`: `"upload.loaded_notify: Fichier chargé — %{count} VMs"`.

### Language Toggle with Page Reload

The safest strategy for NiceGUI is a full page reload after writing the locale to `app.storage.tab`. Partial reactive updates are unreliable for headers and AG Grid columns built at construction time.

```python
def _toggle_locale() -> None:
    current = app.storage.tab.get("locale", "fr")
    app.storage.tab["locale"] = "en" if current == "fr" else "fr"
    ui.navigate.reload()
```

### AG Grid Locale via localeText

AG Grid column `headerName` values are Python strings set at construction time — they are translated on page build. Built-in AG Grid UI text (pagination, filters, "No Rows") is set via the `localeText` grid option loaded from a CDN-hosted `AG_GRID_LOCALE_FR` object.

```python
ui.run_javascript("""
  fetch('https://cdn.jsdelivr.net/...ag-grid-locale-fr.js')
    .then(r => r.text()).then(code => eval(code))
    .then(() => { myGrid.api.setGridOption('localeText', agGridLocaleFR); });
""")
```

### PDF Locale Propagation

Pass `locale` explicitly to `generate_report_pdf()`. At function entry, call `i18n.set("locale", locale)` before any `t()` call. PDF generation is synchronous — no coroutine interleaving risk.

```python
def generate_report_pdf(summary, project_name, locale="fr") -> bytes:
    _i18n.set("locale", locale)
    # All t() calls now use the explicit locale
```

### YAML Key Hierarchy

Namespace keys by feature area to prevent collisions. Both locale files must be kept in sync — a missing key falls back to English, not a KeyError.

```yaml
# fr.yaml
upload:
  title: "Téléversement du fichier"
  drop_label: "Déposez votre fichier ici"
  loaded_notify: "Fichier chargé — %{count} VMs"
report:
  download_pdf: "Télécharger le rapport PDF"
```

### Module Import: `i18n` vs `i18n.config`

The `python-i18n` package installs as the `i18n` top-level module. Import it as `import i18n as _i18n` to avoid shadowing the project's own `store_predict.i18n` package at the call sites that need both.

## Anti-Patterns

- **Calling `t()` from pipeline modules:** Pipeline code (`ingestion.py`, `classification.py`) has no NiceGUI context. Use hardcoded English strings for `IngestionError` messages; the UI layer displays them via `ui.notify(str(exc))`.
- **Using a loop variable named `t`:** It shadows the `t()` import. Use `wt`, `row`, or any other name in loops.
- **Building AG Grid column defs before locale is set:** Column `headerName` strings are baked into the grid spec at construction time. Always build column defs inside the page function (which runs per-request with the correct locale), not at module load time.

## Dependencies

| Package | Version | Notes |
|---------|---------|-------|
| python-i18n | >=0.3.9 | Core library |
| python-i18n[YAML] | same | Required for YAML locale files |

No AG Grid or PDF library changes needed — locale is passed at call time.
