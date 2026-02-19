# Architecture Research

**Domain:** Data processing web tool — milestone 2 feature integration (i18n, LLM classification, PDF branding, Excel export, UX polish)
**Researched:** 2026-02-19
**Confidence:** HIGH (existing code verified; libraries confirmed via web search)

## Context: Existing Architecture Snapshot

The app is production-stable with 30 modules. Before mapping new features, the concrete existing structure matters:

```
src/store_predict/
  main.py                          # ui.run(), page route imports
  config.py                        # Paths, APP_PORT, COMPANY_PREFIX_PATTERNS
  logging_config.py                # Logger; never log VM names
  data/DRR.csv                     # Reference ratios (shipped in package)

  pipeline/                        # Pure functions — zero UI imports
    ingestion.py                   # RVTools / LiveOptics parsing
    classification.py              # RuleRegistry, ClassificationRule, classify_dataframe()
    calculation.py                 # CalculationSummary, WorkloadGroupResult, calculate()
    models.py
    validation.py
    errors.py
    parsers/

  services/
    drr_table.py                   # DRRTable.from_csv(), get_ratio(), get_conservative_ratio()
    pdf_report.py                  # generate_report_pdf(summary, project_name) -> bytes

  ui/
    layout.py                      # layout() contextmanager — header, nav, dark toggle
    state.py                       # save/load session via app.storage.tab (JSON-serialized dicts)
    pages/
      upload.py                    # /upload — ingestion + classification trigger
      review.py                    # /review — AG Grid edit, workload dialogs, bulk update
      report.py                    # /report — summary cards, PDF download
    components/
      vm_table.py                  # create_vm_table() — AG Grid with inline editors
      workload_dialog.py           # WorkloadDialog — async multi-select dialog
      summary_stats.py             # build_summary_stats() — live metric cards
      dark_mode_toggle.py
```

**Critical contracts:**
- `pipeline/` never imports from `ui/` — the pipeline is UI-free and fully testable
- Session state lives in `app.storage.tab` as JSON-serializable `list[dict]`
- `classify_dataframe()` adds four columns: `workload_category`, `workload_subcategory`, `classification_rule`, `classification_confidence`
- `calculate()` accepts `list[dict[str, Any]]` (the session row_data), returns `CalculationSummary`
- `generate_report_pdf(summary, project_name)` returns `bytes`

---

## Feature Integration Map

### Feature 1: i18n (FR/EN runtime switching)

**Integration approach:** Python-layer translation dict + NiceGUI session storage for locale preference.

NiceGUI has no native i18n API as of version 3.4.x. The Quasar framework underneath has a language pack concept (`Quasar.lang.set()`), but this only affects Quasar component labels (date pickers, pagination text). App-level string translation requires a Python-side solution.

**Recommended approach:** `python-i18n` library with YAML translation files. It provides `i18n.t('key')` with placeholders, pluralization, and runtime locale switching via `i18n.set('locale', 'fr')`. The locale is stored per-tab in `app.storage.tab['locale']`.

**New modules required:**

```
src/store_predict/
  i18n/                            # NEW — translation infrastructure
    __init__.py                    # t() helper, set_locale(), get_locale()
    locales/
      en.yaml                      # English strings
      fr.yaml                      # French strings
```

**Integration points:**

```
ui/layout.py                       # MODIFIED: add language toggle button in header
                                   # Calls set_locale(), triggers page refresh
ui/state.py                        # MODIFIED: add get_locale() / set_locale()
                                   # that reads/writes app.storage.tab['locale']
ui/pages/*.py                      # MODIFIED: all user-facing strings wrapped in t()
ui/components/*.py                 # MODIFIED: column headers, button labels, notifications
services/pdf_report.py             # MODIFIED: PDF section headings use t() or locale param
```

**Data flow:**

```
User clicks FR/EN toggle in header
    -> set_locale('fr') writes app.storage.tab['locale'] = 'fr'
    -> ui.navigate.reload() or page re-render
    -> All t('key') calls return French strings
    -> PDF generation reads locale from session or explicit param
```

**Key constraint:** `app.storage.tab` is per-browser-tab; locale must be read from there on every page render, not from a process-global. Use `i18n.config.set('locale', get_locale())` at the top of each page handler function, before any `t()` calls.

**Pattern:**

```python
# i18n/__init__.py
import i18n
from store_predict.ui.state import get_locale

_LOCALES_DIR = Path(__file__).parent / "locales"
i18n.set("load_path", [str(_LOCALES_DIR)])
i18n.set("fallback", "en")

def t(key: str, **kwargs: object) -> str:
    locale = get_locale()  # reads app.storage.tab
    i18n.set("locale", locale)
    return i18n.t(key, **kwargs)
```

---

### Feature 2: LLM Classification Fallback

**Integration approach:** New `pipeline/llm_classifier.py` module called after the rules-based pass for VMs with `classification_confidence == "default"`.

The LLM fallback is a pipeline concern, not a UI concern. It fits cleanly after `classify_dataframe()` and before DRR lookup. LiteLLM is the right library — it provides a single `completion()` / `acompletion()` call that routes to OpenAI, Anthropic Claude, or a local Ollama endpoint based on a model-string prefix.

**New modules required:**

```
src/store_predict/
  pipeline/
    llm_classifier.py              # NEW — LLM fallback for unmatched VMs
  services/
    llm_config.py                  # NEW — provider config (model, base_url, api_key)
```

**Integration point — upload.py (existing):**

The upload handler in `ui/pages/upload.py` currently does:

```python
df = classify_dataframe(df, registry)
```

With LLM fallback, it becomes:

```python
df = classify_dataframe(df, registry)
if llm_enabled():
    df = await classify_unmatched_vms_with_llm(df, drr_table)
```

This is the only change to existing code. The LLM classifier operates only on rows where `classification_confidence == "default"`, leaving all rule-matched rows untouched.

**New component: `pipeline/llm_classifier.py`:**

```python
async def classify_unmatched_vms_with_llm(
    df: pd.DataFrame,
    drr_table: DRRTable,
    config: LLMConfig,
) -> pd.DataFrame:
    """For VMs with confidence='default', ask LLM to classify.

    Returns df with updated workload_category, workload_subcategory,
    classification_confidence='llm_fallback' for reclassified rows.
    """
    unmatched_mask = df["classification_confidence"] == "default"
    if not unmatched_mask.any():
        return df

    categories_json = [{"category": e.category, "subcategory": e.subcategory}
                       for e in drr_table.entries]

    tasks = []
    for idx, row in df[unmatched_mask].iterrows():
        tasks.append(_classify_one_vm(idx, row, categories_json, config))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Apply results back to df ...
    return df
```

**LLM config via `config.py` or environment:**

```python
# config.py additions
LLM_ENABLED: bool = bool(os.environ.get("LLM_ENABLED", ""))
LLM_MODEL: str = os.environ.get("LLM_MODEL", "ollama/llama3.2")
LLM_BASE_URL: str | None = os.environ.get("LLM_BASE_URL")  # for Ollama
LLM_API_KEY: str | None = os.environ.get("LLM_API_KEY")
```

LiteLLM model string format:
- OpenAI: `"gpt-4o-mini"`
- Anthropic: `"claude-3-haiku-20240307"`
- Ollama: `"ollama/llama3.2"` with `base_url="http://localhost:11434"`

**Structured output approach:** Send the full DRR category list as JSON in the system prompt. Request JSON response with `{"category": "...", "subcategory": "..."}`. Validate against known categories before applying. Fall back to "default" if LLM returns invalid category.

**UI surface:** Settings page or environment variables only. Do not expose model selection in the per-session UI — it is an admin concern, not a user concern.

---

### Feature 3: PDF Branding (Dell partner logo + customer logo)

**Integration point:** `services/pdf_report.py` — the `_draw_header()` function and `generate_report_pdf()` signature.

**Approach:** ReportLab's `canvas.drawImage()` accepts a file path or an `ImageReader` wrapping `BytesIO`. Logo images are stored on disk (configurable paths in `config.py`), loaded once, and drawn in the header callback.

**Signature change to `generate_report_pdf()`:**

```python
def generate_report_pdf(
    summary: CalculationSummary,
    project_name: str,
    partner_logo_path: Path | None = None,
    customer_logo_path: Path | None = None,
) -> bytes:
```

**Header layout with logos:**

```
┌─────────────────────────────────────────────────────┐
│ [Partner Logo left]   Title text   [Customer Logo right] │
│─────────────────────────────────────────────────────│
│ Project: ...   |   Date: 2026-02-19                  │
└─────────────────────────────────────────────────────┘
```

**`_draw_header()` modification:**

```python
def _draw_header(canvas, doc, project_name, partner_logo_path, customer_logo_path):
    canvas.saveState()
    width, height = A4
    bar_height = 55

    # Dark blue bar
    canvas.setFillColor(_BRAND_BLUE)
    canvas.rect(0, height - bar_height, width, bar_height, fill=1, stroke=0)

    # Partner logo (left side of bar)
    if partner_logo_path and partner_logo_path.exists():
        canvas.drawImage(str(partner_logo_path),
                         10 * mm, height - bar_height + 5,
                         width=35 * mm, height=12 * mm,
                         preserveAspectRatio=True, mask="auto")

    # Title (center)
    canvas.setFillColor(colors.white)
    canvas.setFont("VeraBd", 16)
    canvas.drawCentredString(width / 2, height - 32, t("report.title"))

    # Customer logo (right side)
    if customer_logo_path and customer_logo_path.exists():
        canvas.drawImage(str(customer_logo_path),
                         width - 50 * mm, height - bar_height + 5,
                         width=35 * mm, height=12 * mm,
                         preserveAspectRatio=True, mask="auto")
    canvas.restoreState()
```

**Logo upload in UI:** The report page gains two optional file upload inputs for logos. Uploaded logo bytes are stored in `app.storage.tab['partner_logo_bytes']` and `app.storage.tab['customer_logo_bytes']`. The report page writes them to temp files before calling `generate_report_pdf()`, then cleans up.

**Config-level defaults:** `config.py` may specify `PARTNER_LOGO_PATH` and `CUSTOMER_LOGO_DEFAULT_PATH` pointing to static assets shipped with the package. If session overrides are absent, defaults apply.

**Logo storage and session handling:**

```python
# state.py additions
def save_logo(key: str, data: bytes) -> None:
    import base64
    app.storage.tab[key] = base64.b64encode(data).decode()

def load_logo(key: str) -> bytes | None:
    import base64
    encoded = app.storage.tab.get(key)
    return base64.b64decode(encoded) if encoded else None
```

---

### Feature 4: Excel Export

**Integration approach:** New `services/excel_export.py` module. The report page gains a "Download Excel" button alongside "Download PDF".

Excel export requires `openpyxl` (already in dependencies) or `xlsxwriter` (not currently). Use `openpyxl` via `pandas.ExcelWriter` to leverage the existing dependency — no new package needed.

**New module: `services/excel_export.py`:**

```python
from io import BytesIO
import pandas as pd
from store_predict.pipeline.calculation import CalculationSummary

def generate_excel_report(summary: CalculationSummary, project_name: str) -> bytes:
    """Generate Excel workbook with multiple sheets, return bytes."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Sheet 1: Summary metrics (key/value pairs)
        summary_rows = [...]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)

        # Sheet 2: Workload breakdown
        breakdown_rows = [...]
        pd.DataFrame(breakdown_rows).to_excel(writer, sheet_name="Workload Breakdown", index=False)

        # Sheet 3: All VMs (detailed)
        vm_rows = [...]
        pd.DataFrame(vm_rows).to_excel(writer, sheet_name="VM Detail", index=False)

    return buf.getvalue()
```

**Integration point — `ui/pages/report.py`:**

Add a second download button:

```python
ui.button(
    t("report.download_excel"),
    on_click=lambda: _on_download_excel(summary, project_name),
    icon="table_view",
).classes("bg-green-700 text-white")
```

```python
def _on_download_excel(summary: CalculationSummary, project_name: str) -> None:
    from store_predict.services.excel_export import generate_excel_report
    xlsx_bytes = generate_excel_report(summary, project_name)
    safe_name = sanitize_filename(project_name)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    ui.download(xlsx_bytes, f"StorePredict_{safe_name}_{date_str}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
```

**No changes to pipeline/calculation.py** — `CalculationSummary` already has all the data needed.

---

## Updated System Architecture with New Features

```
┌──────────────────────────────────────────────────────────────────────┐
│                          UI Layer (NiceGUI)                           │
│                                                                      │
│  ui/layout.py  ←──────────── i18n/t()  ←── app.storage.tab['locale']│
│       │                                                              │
│  ┌────┴────┐  ┌──────────┐  ┌──────────┐                            │
│  │ /upload │  │ /review  │  │ /report  │                            │
│  └────┬────┘  └────┬─────┘  └─────┬────┘                           │
│       │            │              │                                  │
│       │            │         ┌────┴──────────────┐                  │
│       │            │         │  Download buttons  │                  │
│       │            │         │  PDF  |  Excel     │                  │
│       │            │         └────┬──────────┬────┘                 │
└───────┼────────────┼──────────────┼──────────┼──────────────────────┘
        │            │              │          │
        v            v              v          v
┌──────────────────────────────────────────────────────────────────────┐
│                       Pipeline / Services Layer                       │
│                                                                      │
│  pipeline/ingestion.py          services/pdf_report.py               │
│  pipeline/classification.py     (+ logo paths)                       │
│  pipeline/llm_classifier.py  ←─ LiteLLM ←── OpenAI/Claude/Ollama   │
│  pipeline/calculation.py        services/excel_export.py             │
│                                 (openpyxl via pandas.ExcelWriter)    │
│                                 services/drr_table.py                │
└──────────────────────────────────────────────────────────────────────┘
        │
        v
┌──────────────────────────────────────────────────────────────────────┐
│                         State Layer                                   │
│  app.storage.tab:  vm_data, project_name, locale,                    │
│                    partner_logo_bytes, customer_logo_bytes            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## New vs Modified Modules

| Module | Status | Change |
|--------|--------|--------|
| `i18n/__init__.py` | NEW | `t()` helper, locale management |
| `i18n/locales/en.yaml` | NEW | English translation catalog |
| `i18n/locales/fr.yaml` | NEW | French translation catalog |
| `pipeline/llm_classifier.py` | NEW | LLM fallback classification |
| `services/llm_config.py` | NEW | LiteLLM provider config dataclass |
| `services/excel_export.py` | NEW | Multi-sheet Excel generation |
| `config.py` | MODIFIED | Add `LLM_*` env vars, `PARTNER_LOGO_PATH`, `CUSTOMER_LOGO_DEFAULT_PATH` |
| `services/pdf_report.py` | MODIFIED | `generate_report_pdf()` gains logo params, `_draw_header()` draws images |
| `ui/state.py` | MODIFIED | Add `get_locale()`, `set_locale()`, `save_logo()`, `load_logo()` |
| `ui/layout.py` | MODIFIED | Add language toggle (FR/EN) button to header |
| `ui/pages/upload.py` | MODIFIED | Optionally call `classify_unmatched_vms_with_llm()` after rules pass |
| `ui/pages/report.py` | MODIFIED | Add Excel download button, logo upload inputs, wrap strings in `t()` |
| `ui/pages/review.py` | MODIFIED | Wrap strings in `t()` |
| `ui/pages/upload.py` | MODIFIED | Wrap strings in `t()` |
| `ui/components/vm_table.py` | MODIFIED | Column headers wrapped in `t()` |
| `pyproject.toml` | MODIFIED | Add `python-i18n`, `litellm` as optional dep or core dep |

---

## Suggested Build Order

The features have dependency relationships that dictate build order:

### Phase 1: i18n Foundation (must be first)

**Rationale:** Every other feature's UI strings need to go through `t()`. Building i18n last means retroactively wrapping every string — double the effort. Do it first with the two simplest strings, then string-wrap naturally as each feature is built.

Steps:
1. Add `python-i18n` dependency
2. Create `i18n/` package with `t()` wrapper and `get_locale()` / `set_locale()` on `app.storage.tab`
3. Create `en.yaml` and `fr.yaml` with placeholder keys for all existing UI strings
4. Replace strings in `layout.py` and one page to validate the pattern
5. Add FR/EN toggle to header
6. Expand YAML with all strings across all pages

### Phase 2: Excel Export (low risk, high value)

**Rationale:** Pure new service module with a new button. Zero risk to existing functionality. `openpyxl` is already a dependency. Fast to deliver, validates the download button pattern before PDF branding work.

Steps:
1. Create `services/excel_export.py` with three-sheet workbook
2. Add Download Excel button to `report.py`
3. Test with existing `CalculationSummary` data
4. Wrap button label in `t()` (benefits from Phase 1)

### Phase 3: PDF Branding (moderate risk, isolated change)

**Rationale:** Modifies an existing service but is well-isolated. The signature change to `generate_report_pdf()` is backwards-compatible (optional kwargs with defaults). The logo loading via session state is the riskiest part — base64 encoding large images in `app.storage.tab` needs size limits.

Steps:
1. Extend `config.py` with logo path constants
2. Add `save_logo()` / `load_logo()` to `state.py`
3. Add logo upload inputs to `report.py`
4. Modify `_draw_header()` in `pdf_report.py` to draw images conditionally
5. Extend `generate_report_pdf()` signature with optional logo path params
6. Test with and without logos; test with PNG and SVG inputs (SVG not supported by ReportLab — PNG only)

### Phase 4: LLM Classification Fallback (highest risk, optional feature)

**Rationale:** Builds last because it is optional, network-dependent, and has the most failure modes. By this point, the rest of the app is stable. The LLM path is disabled by default (`LLM_ENABLED` env var). It modifies only one line in the existing upload flow.

Steps:
1. Add `litellm` as optional dependency in `pyproject.toml`
2. Create `services/llm_config.py` with config dataclass
3. Create `pipeline/llm_classifier.py` with async classify function
4. Extend `config.py` with `LLM_*` env vars
5. Modify `upload.py` to call LLM fallback when enabled
6. Add UI indicator (e.g., notification) when LLM reclassification ran and how many VMs changed
7. Add `LLM_ENABLED=true` / model config to Docker Compose docs

### Phase 5: UX Polish (last, informed by all prior phases)

**Rationale:** UX polish touches every page. Do it last so the full feature set is in place. Avoid polishing pages that will change.

Scope: Loading indicators for LLM async work, confidence column color coding, column visibility toggles in AG Grid, improved empty-state pages.

---

## Component Boundary Rules (unchanged)

These rules from the original architecture must be maintained:

| Rule | Why |
|------|-----|
| `pipeline/` never imports from `ui/` | Keeps pipeline testable without NiceGUI |
| `i18n/t()` is safe to call from pipeline | Only if locale is passed as param; do not read `app.storage.tab` from pipeline modules |
| LLM config comes from env vars, not session | Provider credentials are server-side admin concerns |
| Logo bytes stored as base64 in `app.storage.tab` | NiceGUI tab storage is JSON; bytes must be encoded |
| `generate_report_pdf()` accepts file paths for logos, not bytes | Keeps function signature simple; caller handles temp files |

---

## Data Flows with New Features

### i18n Data Flow

```
Browser tab loads page
    -> page handler calls get_locale() -> reads app.storage.tab['locale']
    -> i18n.set('locale', locale)
    -> all t('key') calls return locale-appropriate string
    -> user clicks FR toggle
    -> set_locale('fr') writes app.storage.tab['locale'] = 'fr'
    -> ui.navigate.reload() re-runs page handler with new locale
```

### LLM Fallback Data Flow

```
File uploaded
    -> ingest_file() -> raw DataFrame
    -> classify_dataframe(df, registry) -> classified DataFrame
    -> [if LLM_ENABLED] classify_unmatched_vms_with_llm(df, drr_table)
          -> filter rows where classification_confidence == 'default'
          -> for each unmatched VM: litellm.acompletion(model, prompt)
          -> parse JSON response, validate category against DRR table
          -> update row: workload_category, workload_subcategory,
                         classification_confidence = 'llm_fallback'
    -> DRR lookup applied
    -> save_session_data(df, project_name)
    -> navigate to /review
```

### PDF Branding Data Flow

```
User uploads partner logo on /report page
    -> logo bytes base64-encoded into app.storage.tab['partner_logo_bytes']
User clicks Download PDF
    -> load_logo('partner_logo_bytes') -> bytes or None
    -> write bytes to NamedTemporaryFile
    -> generate_report_pdf(summary, project_name,
                           partner_logo_path=tmp_path)
    -> _draw_header() calls canvas.drawImage(partner_logo_path, ...)
    -> temp file deleted
    -> PDF bytes served to browser
```

### Excel Export Data Flow

```
User clicks Download Excel on /report page
    -> generate_excel_report(summary, project_name)
    -> pd.ExcelWriter(BytesIO(), engine='openpyxl')
    -> Sheet 1: Summary (project name, date, totals)
    -> Sheet 2: Workload Breakdown (one row per workload group)
    -> Sheet 3: VM Detail (one row per VM calculation)
    -> buf.getvalue() -> bytes
    -> ui.download(bytes, filename, media_type)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Global locale state

**What people do:** Set `i18n.set('locale', ...)` at process level in a request handler.
**Why wrong:** NiceGUI is multi-user; one tab's locale change pollutes another tab's translations mid-render.
**Do this instead:** Always set locale at the top of each page handler from `app.storage.tab['locale']`, immediately before any `t()` calls.

### Anti-Pattern 2: LLM calls in the calculation module

**What people do:** Call the LLM when calculating DRR because "it's already processing".
**Why wrong:** Calculation is a pure, synchronous, testable function. LLM calls are async, network-dependent, and slow.
**Do this instead:** LLM fallback lives in `pipeline/llm_classifier.py`, called by the upload handler after `classify_dataframe()`, before `calculate()`.

### Anti-Pattern 3: Storing logo bytes in app.storage.tab as raw bytes

**What people do:** `app.storage.tab['logo'] = image_bytes`
**Why wrong:** `app.storage.tab` is JSON-backed; raw bytes are not JSON-serializable. Silently fails or errors.
**Do this instead:** `app.storage.tab['logo'] = base64.b64encode(image_bytes).decode()` with matching decode on read.

### Anti-Pattern 4: Hardcoding translations in `t()` calls

**What people do:** `t("Total VMs")` using the display string as the key.
**Why wrong:** Key collisions, case-sensitivity bugs, impossible to have French keys.
**Do this instead:** Use dot-notation keys: `t("report.totals.vm_count")` mapping to `"Total VMs"` in `en.yaml`.

### Anti-Pattern 5: SVG logos in ReportLab

**What people do:** Upload an SVG logo and pass its path to `canvas.drawImage()`.
**Why wrong:** ReportLab's `drawImage()` does not support SVG natively — it silently fails or raises an obscure error.
**Do this instead:** Accept only PNG, JPEG, and GIF formats for logos. Validate file extension and magic bytes at upload time. Document this limitation in the UI.

---

## Integration Points Summary

| New Feature | Touches Existing Module | Change Scope |
|-------------|------------------------|--------------|
| i18n | `layout.py`, all pages, all components | Additive — wrap strings in `t()` |
| i18n | `state.py` | Add 2 functions |
| LLM fallback | `upload.py` | 3-line addition (guard + one await call) |
| LLM fallback | `config.py` | Add 4 env vars |
| PDF branding | `pdf_report.py` | 2 optional kwargs, `_draw_header()` extended |
| PDF branding | `state.py` | Add `save_logo()`, `load_logo()` |
| PDF branding | `report.py` | Add logo upload inputs |
| Excel export | `report.py` | Add one button + handler |

The pipeline modules `ingestion.py`, `classification.py`, `calculation.py`, `drr_table.py` are all unchanged.

---

## Sources

- [NiceGUI i18n Discussion](https://github.com/zauberzeug/nicegui/discussions/389) — community patterns for locale switching
- [NiceGUI Dynamic Language Discussion](https://github.com/zauberzeug/nicegui/discussions/4295) — Quasar.lang.set() approach
- [python-i18n on PyPI](https://pypi.org/project/python-i18n/) — YAML/JSON translation library
- [LiteLLM Documentation](https://docs.litellm.ai/docs/) — unified LLM provider API
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/json_mode) — JSON mode for classification
- [ReportLab canvas.drawImage](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/) — image placement in PDF
- [pandas.ExcelWriter](https://pandas.pydata.org/docs/reference/api/pandas.ExcelWriter.html) — openpyxl engine for Excel export
- [XlsxWriter with Pandas](https://xlsxwriter.readthedocs.io/working_with_pandas.html) — alternative engine reference

---

*Architecture research for: StorePredict milestone 2 — i18n, LLM fallback, PDF branding, Excel export*
*Researched: 2026-02-19*
