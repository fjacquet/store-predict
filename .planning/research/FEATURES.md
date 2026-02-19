# Feature Research — StorePredict Milestone 2

**Domain:** Pre-sales sizing tool (Python web app, NiceGUI + pandas + ReportLab)
**Researched:** 2026-02-19
**Confidence:** HIGH for framework capabilities, MEDIUM for LLM classification patterns

---

## Context: What Already Exists (v1.0 baseline)

The following features are DONE and must not be re-built:

- File upload with format detection (RVTools xlsx, LiveOptics xlsx/csv)
- Rules-based VM classification engine (29 rules, 0% unknown on sample data)
- AG Grid interactive table with editable workload types and DRR overrides
- One-page PDF report (ReportLab Platypus, branded header, Vera fonts for French chars)
- Calculation engine (weighted avg DRR, required capacity, performance metrics)
- Docker deployment, CI/CD, MkDocs docs, 145 tests

The milestone adds four independent feature clusters: i18n, LLM fallback classification,
PDF branding (logos), and Excel export — plus UX polish.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that Dell pre-sales engineers will expect or that, if missing, make the product
feel incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| French UI strings | Primary user language is French; English-only UI is a barrier to adoption | MEDIUM | NiceGUI has no built-in i18n API — must implement a translation layer manually. Dict-based approach preferred over gettext for a 2-language app. |
| Language toggle (FR/EN) | Pre-sales engineers present to different audiences; need to switch on the fly | LOW | `ui.dark_mode()` pattern exists for toggle; language switch triggers page re-render via `ui.navigate.reload()` or tab-scoped locale state. |
| AG Grid column headers in French | The data table is the core interaction surface; English headers in a French context feel broken | MEDIUM | AG Grid Community locale pack (`@ag-grid-community/locale`) provides `AG_GRID_LOCALE_FR`. Column `headerName` values must also be translated separately — locale pack covers UI chrome only (filter buttons, menus). |
| Download sizing results as Excel | Pre-sales engineers share results with customers and colleagues via email; PDF is read-only, Excel is editable for follow-up | MEDIUM | `pandas.DataFrame.to_excel()` with `openpyxl` engine. No new dependencies needed — openpyxl is already in the stack via pandas. Styled output (header row, column widths) adds ~30 lines. |
| Dell partner logo in PDF header | Reports are presented to customers; unbranded reports look like internal drafts | LOW | ReportLab `Image()` flowable. Dell partner logo is a static asset bundled in `assets/`. PNG/SVG → PNG for ReportLab. Already using canvas callbacks in `_draw_header()`; logo is an additional `canvas.drawImage()` call. |
| Customer/company logo in PDF | Customer-facing sizing reports should carry the partner's company brand, not just Dell | MEDIUM | Logo upload via `ui.upload()`, stored via `app.storage.user` (server-side JSON persistence). ReportLab reads from bytes or file path. Must validate file type (PNG/JPEG) and size. |

### Differentiators (Competitive Advantage)

Features that set StorePredict apart from generic sizing spreadsheets and competing tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LLM fallback for unclassified VMs | When rules-based classifier produces "Unknown", LLM can infer workload type from VM name + OS using broader world knowledge — particularly useful for custom naming conventions | HIGH | Use LiteLLM as the provider-agnostic layer (100+ providers, unified API, built-in fallback/retry). Only call LLM for VMs classified as "Unknown Reducible". Use OpenAI structured outputs / Pydantic model for reliable JSON response. Configurable via env vars: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`. Ollama for air-gapped deployments. |
| LLM provider configurability (OpenAI / Claude / Ollama) | Pre-sales engineers operate in varied IT security contexts — some need cloud AI, others need on-premises/local models | MEDIUM | LiteLLM abstracts provider differences. `OLLAMA_BASE_URL` env var for local deployments. No code change needed to switch providers. Config page in UI exposes provider selection. |
| LLM classification confidence display | Shows users which VMs were auto-classified with high confidence vs. LLM-inferred — builds trust in results | LOW | Add `classification_source` field to VM data model: `"rules"` / `"llm"` / `"manual"`. Color-code rows in AG Grid: blue for LLM-classified, default for rules. |
| LLM batch mode (not one call per VM) | Sending VMs in batches reduces latency and API cost for large environments with many unknowns | MEDIUM | Batch unknown VMs into groups of 20-50. Single prompt with JSON array response. Requires careful prompt engineering to maintain accuracy across batch. |
| Excel export with DRR breakdown by workload | Excel file includes the same workload breakdown table as the PDF — enables customer-side customization | LOW | Add a second sheet "Workload Breakdown" alongside "VM List" sheet. Same data as PDF table. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-detect browser language for i18n | "Zero config" experience | NiceGUI's `ui.context.client` does expose `navigator.language` via JS but is unreliable on corporate VPNs and Citrix sessions where Dell pre-sales often operate. Also breaks when the same session is shared between two users on a demo device. | Explicit language toggle stored in `app.storage.tab`. Defaults to French (primary language). User picks once per session. |
| Real-time LLM classification as user types in VM name | "Smart" UX | Creates excessive API calls, adds latency to every keystroke, and the VM name field is not typically user-typed (it comes from uploaded data). | Classify once on upload. Re-classify on-demand via "Re-classify unknowns" button. |
| Full gettext/.po/.mo pipeline for i18n | Industry-standard i18n toolchain | Overkill for 2 languages + ~200 strings. Requires `msgfmt` binary, `.po` file compilation step in Docker build, Babel extraction script. Adds CI complexity with no translator workflow benefit (no external translators). | Dict-based `translations.py` with `{"fr": {...}, "en": {...}}` and a `t(key)` helper. Straightforward, no external tools. |
| Store uploaded logos in a database | "Proper" persistence | No database in the stack. Adding a DB for logo storage adds infra complexity disproportionate to the feature. | Store logos as files in a server-side `data/logos/` directory, keyed by session user ID from `app.storage.user`. File-based is sufficient for a single-container deployment. |
| Per-VM LLM classification (one API call per VM) | Accuracy guarantee | At 500 VMs with 10% unknown, that is 50 sequential API calls adding 30-120 seconds to the workflow. Cost at ~$0.001/call = acceptable, but latency is not. | Batch 20-50 unknowns per API call. Accept slight accuracy trade-off for >10x speed gain. |
| LLM classification for ALL VMs (not just unknowns) | "Let AI do everything" | The rules-based engine has 0% unknown rate on the test dataset. LLM costs and latency are unnecessary when rules already work. LLM also introduces non-determinism that makes results harder to audit. | LLM as fallback only — triggered when `classification_source == "unknown"`. |

---

## Feature Dependencies

```
i18n Translation Layer
    └──required by──> AG Grid FR Locale Headers
    └──required by──> PDF Report FR Labels
    └──required by──> Excel Export FR Column Headers

app.storage.user (already exists in NiceGUI)
    └──required by──> Company Logo Upload + Persistence

LLM Provider Config (env vars + UI config page)
    └──required by──> LLM Fallback Classification
                          └──required by──> LLM Confidence Display in AG Grid
                          └──required by──> LLM Batch Mode

ReportLab canvas._draw_header() (already exists)
    └──enhanced by──> Dell Logo Image (static asset)
    └──enhanced by──> Company Logo Image (uploaded)

pandas DataFrame (already exists in pipeline)
    └──enhances──> Excel Export (same data, different format)

Excel Export ──independent of──> LLM Fallback
PDF Branding ──independent of──> i18n (labels are embedded strings)
```

### Dependency Notes

- **i18n required before AG Grid headers**: The translation dict must exist before column `headerName` values can be set dynamically. Both must land in the same phase.
- **Logo upload required before PDF branding**: Uploading and persisting a logo is a prerequisite for rendering it in the PDF. Both are in the same phase but logo upload must be implemented first.
- **LLM config page required before LLM classification**: The classification call needs `provider`, `model`, and `api_key` from settings. A settings page (or env-var-only approach) must exist first. Env-var-only is simpler for v1 of the feature.
- **Excel export has no dependencies on new features**: It reads from the same session `vm_data` dict that the PDF report already uses. Can be implemented in any phase.

---

## MVP Definition for This Milestone

This is a subsequent milestone on a shipped product. "MVP" here means: minimum to make each
feature cluster valuable enough to ship.

### Ship With (Milestone 2 scope)

- [x] i18n: FR/EN toggle + translated UI strings (all pages), `t(key)` helper, dict-based
- [x] i18n: AG Grid column headers in French via `headerName` + AG Grid locale pack for FR
- [x] i18n: PDF report labels in French (date format, section headers, footer)
- [x] PDF branding: Dell partner logo in header (static PNG asset, right-aligned)
- [x] PDF branding: Custom company logo upload (PNG/JPEG, max 2 MB), stored per user session
- [x] Excel export: Download button on report page, VM list sheet + workload breakdown sheet
- [x] LLM fallback: Env-var config (provider/model/key), classify unknowns only, batch mode
- [x] LLM fallback: `classification_source` field, color-coded rows in AG Grid (rules/llm/manual)

### Add After Validation (Milestone 2.x)

- [ ] LLM provider selection UI (settings page) — env vars sufficient for v1
- [ ] LLM confidence score display (if provider returns logprobs) — provider-dependent
- [ ] i18n: Date/number locale formatting (French uses dd/mm/yyyy, comma decimal)
- [ ] PDF report: Two-language mode (FR + EN side-by-side columns) — complex layout

### Future Consideration (v2+)

- [ ] Third language support (German, Spanish for broader Dell partner network)
- [ ] LLM fine-tuning on historical classifications — only relevant after large deployment
- [ ] Dynamic Quasar theme color customization per partner brand — high complexity, low value

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| i18n FR/EN toggle + string translations | HIGH | MEDIUM | P1 |
| AG Grid FR locale + FR column headers | HIGH | LOW | P1 |
| Dell logo in PDF | HIGH | LOW | P1 |
| Company logo upload + PDF | HIGH | MEDIUM | P1 |
| Excel export | HIGH | LOW | P1 |
| LLM fallback for unknown VMs | MEDIUM | HIGH | P2 |
| LLM classification_source display | MEDIUM | LOW | P2 |
| LLM batch mode | MEDIUM | MEDIUM | P2 |
| PDF FR labels | MEDIUM | LOW | P1 |
| i18n date/number locale formatting | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for milestone 2 launch
- P2: Should have, add in same milestone if time allows
- P3: Nice to have, defer to milestone 3

---

## Implementation Notes per Feature

### i18n: Translation Layer

**Approach:** Dict-based `translations.py` with `t(key, lang=None)` helper.

```python
# src/store_predict/i18n.py
TRANSLATIONS = {
    "en": {
        "upload.title": "Upload",
        "report.total_vms": "Total VMs",
        "report.required_capacity": "Required Capacity",
        ...
    },
    "fr": {
        "upload.title": "Téléchargement",
        "report.total_vms": "Total de VMs",
        "report.required_capacity": "Capacité requise",
        ...
    }
}

def t(key: str, lang: str | None = None) -> str:
    lang = lang or app.storage.tab.get("language", "fr")
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)
```

Language stored in `app.storage.tab["language"]`. Toggle triggers `ui.navigate.reload()` to
re-render the current page with the new language. This is the simplest reliable approach
given NiceGUI's page-based rendering model — dynamic in-page language swapping requires
binding every label to a reactive value, which is disproportionate complexity.

**AG Grid headers:** Pass `headerName=t("grid.vm_name")` in column definitions at page
load time. AG Grid locale pack (`AG_GRID_LOCALE_FR`) injected via `ui.add_head_html()` for
UI chrome (filter buttons, "No rows to show", etc.).

### PDF Branding: Logos

**Dell logo:** Static PNG bundled at `src/store_predict/assets/dell_partner_logo.png`.
Size: ~150x50px. Placed right-aligned in `_draw_header()` via `canvas.drawImage()`.
Dell partner logo usage governed by Dell Technologies Partner Program brand guidelines —
verify logo tier matches actual partner tier before shipping.

**Company logo:** Uploaded via `ui.upload(accepted_file_types=".png,.jpg,.jpeg")`.
Server-side validation (magic bytes for PNG/JPEG). Stored as bytes in `app.storage.user`
(NiceGUI persists to `.nicegui/` JSON files — acceptable for images up to ~500 KB;
for larger files, store path to a `data/logos/` file instead).
Rendered in PDF footer or secondary header position.

**ReportLab pattern:**
```python
from reportlab.platypus import Image as RLImage
from io import BytesIO

logo_bytes = app.storage.user.get("company_logo_bytes")
if logo_bytes:
    logo_img = RLImage(BytesIO(logo_bytes), width=1.5*inch, height=0.5*inch,
                       hAlign="LEFT")
```

### Excel Export

**Approach:** `pandas.DataFrame.to_excel()` with `openpyxl` engine. Two sheets:
"VM List" (all VM rows) and "Workload Breakdown" (aggregated by category).
Column widths set via `worksheet.column_dimensions[col].width`.
Header row styled with bold font and blue fill using `openpyxl.styles`.

```python
from io import BytesIO
import pandas as pd

def generate_excel(vm_data: list[dict], summary) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(vm_data).to_excel(writer, sheet_name="VM List", index=False)
        _workload_df(summary).to_excel(writer, sheet_name="Workload Breakdown", index=False)
    return buf.getvalue()
```

Download triggered via `ui.download(content, filename)`. NiceGUI `ui.download()` uses a
single-use server route and works reliably for files up to 50 MB (RVTools exports are
typically 1-10 MB).

### LLM Fallback Classification

**Integration point:** `classification.py` — after rules pass, unknown VMs go to LLM batch.

**LiteLLM provider abstraction:**
```python
from litellm import completion

response = completion(
    model=os.environ["LLM_MODEL"],  # e.g. "gpt-4o-mini", "claude-3-haiku-20240307", "ollama/llama3"
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)
```

**Prompt structure:** Batch of 20-50 VMs with VM name + OS. Response: JSON dict mapping
VM name to `{"category": str, "subcategory": str, "confidence": "high"|"medium"|"low"}`.
Category/subcategory must be constrained to DRR.csv categories (include full list in prompt).

**Env vars required:**
```
LLM_PROVIDER=openai|anthropic|ollama
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434  # only for ollama
LLM_ENABLED=true  # feature flag; default false for safety
```

**Feature flag default off:** LLM calls cost money and require network access. Default
`LLM_ENABLED=false` so Docker deployments don't break in air-gapped environments. Users
opt in by setting the env var.

---

## Competitor Feature Analysis

StorePredict competes primarily against:
1. **Manual Excel spreadsheets** — the current baseline for most Dell pre-sales engineers
2. **Dell's internal sizing tools** — often web-only, not usable offline, not customizable
3. **Generic capacity planning tools** (Turbonomic, Virtana) — overkill, not Dell-specific

| Feature | Excel Spreadsheet | Dell Internal Tool | StorePredict v1 | StorePredict v2 (this milestone) |
|---------|-------------------|--------------------|-----------------|----------------------------------|
| French UI | N/A (user's Excel locale) | English-only | English-only | FR/EN toggle |
| Auto-classification | None | Limited | 29 rules, 0% unknown | + LLM fallback |
| PDF report | Manual formatting | Automated | One-page branded | + Dell + company logo |
| Excel export | Native | No | No | Yes |
| Offline use | Yes | No | Yes (Docker) | Yes |

---

## Sources

- NiceGUI i18n discussion: https://github.com/zauberzeug/nicegui/discussions/389
- NiceGUI dynamic language switching: https://github.com/zauberzeug/nicegui/discussions/4295
- NiceGUI AG Grid locale discussion: https://github.com/zauberzeug/nicegui/discussions/3899
- AG Grid localisation docs: https://www.ag-grid.com/javascript-data-grid/localisation/
- AG Grid community locale npm: https://www.npmjs.com/package/@ag-grid-community/locale
- NiceGUI download API: https://nicegui.io/documentation/download
- NiceGUI storage docs: https://nicegui.io/documentation/storage
- LiteLLM getting started: https://docs.litellm.ai/
- LiteLLM fallback docs: https://docs.litellm.ai/docs/proxy/reliability
- OpenAI structured outputs: https://platform.openai.com/docs/guides/structured-outputs
- ReportLab Platypus docs: https://docs.reportlab.com/reportlab/userguide/ch5_platypus/
- pandas to_excel with openpyxl: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_excel.html
- Dell partner brand guidelines (2025): https://www.delltechnologies.com/asset/fr-ca/solutions/business-solutions/briefs-summaries/partner-brand-guideline.pdf
- python-i18n library: https://pypi.org/project/python-i18n/
- XlsxWriter with pandas: https://xlsxwriter.readthedocs.io/working_with_pandas.html

---

*Feature research for: StorePredict Milestone 2 (i18n, LLM fallback, PDF branding, Excel export)*
*Researched: 2026-02-19*
