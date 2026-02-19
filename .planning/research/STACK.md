# Technology Stack

**Project:** StorePredict — Milestone 2 (i18n, LLM fallback, PDF branding, Excel export, UX polish)
**Researched:** 2026-02-19
**Confidence:** HIGH (versions verified via PyPI search; integration patterns verified via official docs)

---

## What Already Exists (Do NOT Re-Add)

The following are validated and shipped in v1.0. They appear here only so pyproject.toml changes are unambiguous.

| Package | Current pin | Status |
|---------|-------------|--------|
| `nicegui>=3.4,<4.0` | In pyproject.toml | Keep as-is |
| `pandas>=2.2,<4.0` | In pyproject.toml | Keep as-is — used for Excel export engine |
| `openpyxl>=3.1.2` | In pyproject.toml | Keep as-is — required by XlsxWriter-free path |
| `reportlab>=4.0` | In pyproject.toml | Keep as-is — extended for logo embedding |
| `pytest>=8.0` | dev dep | Keep as-is |
| `ruff>=0.9` | dev dep | Keep as-is |
| `mypy>=1.10` | dev dep | Keep as-is |
| `pandas-stubs>=2.2` | dev dep | Keep as-is |

---

## New Dependencies — Milestone 2

### Core Additions

| Technology | Version Pin | Purpose | Why This One |
|------------|-------------|---------|--------------|
| `python-i18n[YAML]` | `>=0.3.9` | Translation string lookup, YAML locale files | Zero-dependency, Rails-style `t('key')` API fits NiceGUI's Python-first model. JSON/YAML files are human-editable by non-developers. No compilation step (vs gettext .po/.mo workflow). Last version (0.3.9) is stable and complete — low maintenance burden is a feature, not a bug. |
| `litellm` | `>=1.61,<2.0` | Unified LLM provider adapter (OpenAI / Claude / Ollama) | Single `completion()` call works for all three providers. Handles retries, timeouts, provider-specific auth. Avoids writing three different client integrations. Actively developed (v1.61.x current as of Feb 2026). |
| `XlsxWriter` | `>=3.2.9` | Styled Excel export with formatting | More powerful than openpyxl for write-only styled output. Supports per-column widths, header bold/color, cell number formats, freeze panes — all needed for a polished sizing report. Used via `pandas.ExcelWriter(engine='xlsxwriter')`, so zero API churn on existing DataFrame code. |
| `Pillow` | `>=12.1.1` | Image validation and resizing for PDF logos | ReportLab's `Image()` Platypus flowable requires Pillow for PNG/JPEG handling. Used to validate uploaded logo dimensions before embedding. Already a transitive dep of many packages; explicit pin guarantees the version. |
| `pydantic-settings` | `>=2.13.0,<3.0` | Type-safe configuration from environment variables | LLM provider keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_BASE_URL), logo paths, and default locale must come from env/`.env` without hardcoding. `pydantic-settings` gives typed SecretStr fields, `.env` file loading, and works with Docker Compose `environment:` blocks. Integrates cleanly with existing `config.py`. |

### Supporting Libraries

| Library | Version Pin | Purpose | When to Use |
|---------|-------------|---------|-------------|
| `PyYAML` | Pulled in by `python-i18n[YAML]` | Parse YAML locale files | Automatically installed; no explicit pin needed |
| `openai` | `>=2.21.0` | OpenAI API (used via litellm, not directly) | Only add as explicit dep if calling OpenAI directly for structured outputs; litellm bundles its own OpenAI client — verify before adding |
| `anthropic` | `>=0.82.0` | Anthropic Claude API (used via litellm) | Same as above — litellm wraps it; only pin explicitly if direct SDK access needed |

> **Note on openai/anthropic:** litellm installs its own pinned versions of provider SDKs. Do **not** add `openai` or `anthropic` as direct deps unless you need them for something litellm does not expose. Avoid double-version conflicts.

---

## Recommended Stack by Feature

### Feature 1: i18n Framework (FR/EN switchable)

**Stack:** `python-i18n[YAML]` + stdlib `gettext` (not used — see below)

**Why python-i18n over stdlib gettext:**
- `gettext` requires `.po` → `msgfmt` → `.mo` compilation toolchain. No translation editor, no CI integration, extra Docker build step.
- `python-i18n` loads YAML files at startup with `i18n.load_path.append('locales/')`. No compilation.
- `i18n.t('report.title')` in Python code is readable and refactorable.
- Switching locale is `i18n.set('locale', 'fr')` — per-session in NiceGUI via `app.storage.tab['locale']`.

**Locale file convention:**
```
src/store_predict/locales/
  en.yml
  fr.yml
```

**NiceGUI integration pattern:**
- Store `locale` in `app.storage.tab` (already used for session isolation).
- Wrap all UI strings: `ui.label(t('upload.title'))`.
- Language selector in header triggers `ui.refreshable` page sections — NiceGUI refreshable context handles re-render.
- `ui.dark_mode()` and locale selector live together in the app header.

**What python-i18n does NOT handle:**
- Number/currency/date formatting — use Python's stdlib `locale.format_string()` or f-string formatting directly.
- Quasar component locale (date pickers, etc.) — use `ui.run_javascript("Quasar.lang.set(...)")` with the Quasar FR language pack loaded via `ui.add_body_html()`.

---

### Feature 2: LLM Fallback Classification (OpenAI / Claude / Ollama)

**Stack:** `litellm>=1.61` + `pydantic-settings>=2.13`

**Why litellm:**
- One adapter for all three required providers. `litellm.completion(model="gpt-4o", ...)` vs `litellm.completion(model="claude-3-5-sonnet-20241022", ...)` vs `litellm.completion(model="ollama/mistral", ...)` — identical call signature.
- Handles Ollama's non-standard base URL via `api_base` parameter.
- Structured output via `response_format={"type": "json_object"}` works across providers.
- Built-in timeout and retry — critical for UX when classification falls back to LLM.

**Configuration pattern (pydantic-settings):**
```python
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class LLMSettings(BaseSettings):
    llm_provider: str = "none"          # "openai" | "anthropic" | "ollama" | "none"
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

**Classification integration point:**
- In `classification.py`, after rules-based matching, if result is `Unknown Reducible` and `LLMSettings().llm_provider != "none"`, call async LLM with VM name + OS.
- LLM returns JSON `{"category": "...", "confidence": 0.8}`. Map to existing DRR categories.
- Wrap in try/except — LLM failure must fall back silently to `Unknown Reducible`, never crash pipeline.
- Add `llm_classified: bool` flag to VM model for UI badge display.

---

### Feature 3: PDF Branding (Dell Partner Logo + Company Logo)

**Stack:** `Pillow>=12.1.1` + existing `reportlab>=4.0`

**Why Pillow:**
- ReportLab's `reportlab.platypus.Image` and `canvas.drawImage()` both use Pillow internally for PNG/JPEG decoding.
- Pillow is needed to validate image dimensions before embedding (reject oversized uploads, compute aspect-ratio-correct scaling).
- `ImageReader` from `reportlab.lib.utils` wraps Pillow — use this for in-memory image bytes from NiceGUI upload.

**Integration pattern:**
```python
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import io

def embed_logo(logo_bytes: bytes, max_width_pt: float, max_height_pt: float) -> Image:
    pil_img = PILImage.open(io.BytesIO(logo_bytes))
    w_px, h_px = pil_img.size
    aspect = h_px / w_px
    draw_width = min(max_width_pt, max_height_pt / aspect)
    draw_height = draw_width * aspect
    return Image(ImageReader(io.BytesIO(logo_bytes)), width=draw_width, height=draw_height)
```

**Storage:** Logo bytes stored in `app.storage.tab` (session-scoped, consistent with existing architecture). No filesystem writes of uploaded logos.

**Dell partner logo:** Ship as a static asset in `src/store_predict/assets/dell_partner.png`. Load from package path at PDF generation time. Never accept this logo from user upload — it must be controlled.

---

### Feature 4: Excel Export

**Stack:** `XlsxWriter>=3.2.9` + existing `pandas>=2.2`

**Why XlsxWriter over openpyxl for export:**
- openpyxl is already used for *reading* RVTools/LiveOptics files. It can write, but formatting API is verbose and less capable.
- XlsxWriter provides: column autofit, header background color, number format strings, freeze top row, bold text — all in ~20 lines via `pandas.ExcelWriter`.
- Write-only limitation of XlsxWriter is not a problem — this is a one-shot export.

**Integration pattern:**
```python
import io
import pandas as pd

def export_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="VM Sizing", index=False)
        workbook = writer.book
        worksheet = writer.sheets["VM Sizing"]
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#0076CE", "font_color": "white"})
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)
            worksheet.set_column(col_num, col_num, max(len(col_name) + 2, 12))
    return buf.getvalue()
```

**NiceGUI download trigger:**
```python
ui.download(content=export_excel(df), filename="sizing_report.xlsx")
```

---

### Feature 5: UX Polish

**Stack:** Existing NiceGUI 3.x — no new deps needed

**What NiceGUI already provides (no additional packages):**
- `ui.dark_mode()` — system preference detection + toggle
- `ui.notify()` — toast notifications (success/error/warning)
- `ui.refreshable` — reactive re-render on locale/data change
- `ui.skeleton()` — loading states while LLM classifies
- `ui.tooltip()` — hover help on DRR values
- `ui.badge()` — "LLM classified" indicator on VM rows
- AG Grid `cellStyle` — conditional row coloring for LLM-vs-rules classification

**Dark mode note:** NiceGUI 2.0+ broke some Tailwind dark: variants (GitHub issue #3753). Use `ui.dark_mode()` value in Python conditionals rather than CSS `dark:` prefix for reliable behavior.

---

## Installation — pyproject.toml Changes

```toml
[project]
dependencies = [
    # Existing (unchanged)
    "nicegui>=3.4,<4.0",
    "pandas>=2.2,<4.0",
    "openpyxl>=3.1.2",
    "reportlab>=4.0",
    # New in Milestone 2
    "python-i18n[YAML]>=0.3.9",
    "litellm>=1.61,<2.0",
    "XlsxWriter>=3.2.9",
    "Pillow>=12.1.1",
    "pydantic-settings>=2.13.0,<3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.9",
    "mypy>=1.10",
    "pandas-stubs>=2.2",
]
```

> **mypy overrides needed:** Add `litellm.*`, `i18n.*`, `xlsxwriter.*` to `ignore_missing_imports = true` in pyproject.toml — none of these ship complete py.typed markers.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| i18n | `python-i18n[YAML]` | stdlib `gettext` | Requires .po/.mo compilation toolchain in Docker build; no runtime locale switching without reinstall |
| i18n | `python-i18n[YAML]` | `Babel` | Babel is comprehensive (CLDR dates/currencies) but heavy; overkill for FR/EN string substitution only |
| LLM adapter | `litellm` | Direct `openai` + `anthropic` + `requests` | Three separate integrations, three auth patterns, three retry implementations |
| LLM adapter | `litellm` | `langchain` | LangChain is 15x heavier, adds abstraction layers that fight the simple "classify one VM name" use case |
| Excel | `XlsxWriter` | `openpyxl` (write mode) | openpyxl write formatting API is verbose and less capable for styled headers/column widths |
| Excel | `XlsxWriter` | `pyexcel` | pyexcel is a thin abstraction with less styling support |
| Config | `pydantic-settings` | `python-dotenv` | python-dotenv only loads env vars; no type validation, no SecretStr masking, no IDE autocomplete |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `langchain` or `langchain-core` | Massive dependency tree, complex abstractions for a single LLM call | `litellm` — one function, same result |
| `openai` / `anthropic` as direct deps | litellm manages provider SDK versions internally; double-pinning causes conflicts | Let litellm manage these as its own transitive deps |
| `Babel` | CLDR overhead unnecessary for 2-language app with no date/currency formatting needs | `python-i18n[YAML]` for strings + stdlib `locale` for number formatting if needed |
| `weasyprint` | Requires system libraries (cairo, pango) making Docker image 200-400 MB larger | Extend existing ReportLab with Pillow for logo embedding |
| `python-docx` | Not needed — Word export is not in scope | — |
| `celery` / `redis` | LLM calls are fast enough (< 5s) to run inline in NiceGUI's async event loop | `asyncio.wait_for()` with timeout |

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `litellm>=1.61` | `openai>=1.0` (transitive) | litellm pins its own openai version; do not co-pin openai directly |
| `litellm>=1.61` | `anthropic>=0.20` (transitive) | Same as above |
| `XlsxWriter>=3.2.9` | `pandas>=2.2` | `ExcelWriter(engine='xlsxwriter')` stable since pandas 2.0 |
| `Pillow>=12.1.1` | `reportlab>=4.0` | ReportLab 4.x uses Pillow for image rendering internally |
| `pydantic-settings>=2.13` | `pydantic>=2.0` (transitive) | pydantic-settings 2.x requires pydantic v2; litellm also uses pydantic v2 — compatible |
| `python-i18n>=0.3.9` | `PyYAML>=6.0` (transitive) | PyYAML installed with `[YAML]` extra |
| `nicegui>=3.4` | All above | NiceGUI 3.x uses pydantic v2 internally — consistent |

---

## mypy Configuration Additions

Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = "litellm.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "i18n.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "xlsxwriter.*"
ignore_missing_imports = true
```

---

## Sources

- [python-i18n PyPI](https://pypi.org/project/python-i18n/) — version 0.3.9, YAML support confirmed
- [NiceGUI i18n Discussion #389](https://github.com/zauberzeug/nicegui/discussions/389) — gettext pattern in NiceGUI, confirmed runtime switching works
- [NiceGUI dynamic language discussion #4295](https://github.com/zauberzeug/nicegui/discussions/4295) — per-session locale approach confirmed
- [litellm PyPI](https://pypi.org/project/litellm/) — v1.61.x current as of Feb 2026; 400+ LLM providers
- [litellm docs](https://docs.litellm.ai/docs/) — OpenAI/Anthropic/Ollama unified `completion()` API confirmed
- [openai PyPI](https://pypi.org/project/openai/) — v2.21.0 released Feb 14, 2026
- [anthropic PyPI](https://pypi.org/project/anthropic/) — v0.82.0 released Feb 18, 2026
- [Pillow PyPI](https://pypi.org/project/pillow/) — v12.1.1 released Feb 11, 2026
- [XlsxWriter PyPI](https://pypi.org/project/xlsxwriter/) — v3.2.9 released Sep 16, 2025
- [XlsxWriter + pandas docs](https://xlsxwriter.readthedocs.io/working_with_pandas.html) — `ExcelWriter(engine='xlsxwriter')` pattern confirmed
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) — v2.13.0 released Feb 15, 2026
- [ReportLab docs ch5](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/) — `Image()` Platypus flowable + `ImageReader` pattern confirmed
- [ReportLab + Pillow integration](https://pythonassets.com/posts/create-pdf-documents-in-python-with-reportlab/) — Pillow required for image embedding confirmed
- [NiceGUI dark mode docs](https://nicegui.io/documentation/dark_mode) — `ui.dark_mode()` API confirmed
- [NiceGUI dark mode Tailwind issue #3753](https://github.com/zauberzeug/nicegui/issues/3753) — dark: CSS variants unreliable in NiceGUI 2.0+, confirmed

---

*Stack research for: StorePredict Milestone 2 — i18n, LLM fallback, PDF branding, Excel export, UX polish*
*Researched: 2026-02-19*
