# Project Research Summary

**Project:** StorePredict v1.1 (Milestone 2)
**Domain:** Pre-sales sizing tool -- Python web app (NiceGUI + pandas + ReportLab)
**Researched:** 2026-02-19
**Confidence:** HIGH

## Executive Summary

StorePredict v1.0 is a shipped, stable product with 145+ tests, Docker deployment, and a complete ingestion-classification-calculation pipeline. Milestone 2 adds four independent feature clusters: i18n (FR/EN), PDF branding (Dell + custom logos), Excel export, and LLM-based classification fallback for unrecognized VMs. The existing architecture cleanly separates pipeline logic from UI, which means each feature can be added with minimal disruption to existing code. No architectural overhaul is needed.

The recommended build order is i18n first, then Excel export, then PDF branding, then LLM classification last. This order is driven by three factors: (1) i18n must come first because every subsequent feature's UI strings should go through `t()` from the start, avoiding a costly string audit later; (2) Excel export and PDF branding are low-risk, high-value additions that use existing dependencies or well-understood libraries; (3) LLM classification is the highest-risk, lowest-priority feature with the most failure modes (async event loop blocking, Docker networking, prompt injection, non-deterministic outputs). The user explicitly confirmed LLM is lower priority and should come last. LiteLLM is the right adapter library, with confirmed OpenRouter support via its 400+ provider list.

The primary risks are: string concatenation patterns breaking French translations (must audit all f-strings before wrapping in `t()`), synchronous LLM calls blocking NiceGUI's event loop (must use async clients exclusively), PNG transparency rendering as black boxes in ReportLab PDFs (must pre-process with Pillow), and Ollama `localhost` failing inside Docker containers (must document `host.docker.internal`). All risks have straightforward mitigations documented in the pitfalls research.

## Key Findings

### Recommended Stack

Five new dependencies are needed. All versions have been verified on PyPI and confirmed compatible with the existing NiceGUI 3.x + pydantic v2 stack.

**Core technologies:**
- **python-i18n[YAML] >=0.3.9**: YAML-based translation files with `t('key')` API -- no compilation step, human-editable locale files, runtime locale switching via `i18n.set('locale', 'fr')`
- **litellm >=1.61,<2.0**: Unified LLM adapter for OpenAI, Anthropic, Ollama, and OpenRouter -- single `completion()` call, handles auth and retries, avoids three separate integrations
- **XlsxWriter >=3.2.9**: Styled Excel export via `pandas.ExcelWriter(engine='xlsxwriter')` -- superior formatting API for headers, column widths, freeze panes compared to openpyxl write mode
- **Pillow >=12.1.1**: Image validation and PNG transparency handling for ReportLab logo embedding -- required for `canvas.drawImage(mask='auto')`
- **pydantic-settings >=2.13.0,<3.0**: Type-safe env var configuration with `SecretStr` for LLM API keys -- integrates with `.env` files and Docker Compose

**What NOT to add:** LangChain (massive, overkill), direct openai/anthropic SDKs (let litellm manage), Babel (overkill for 2 languages), weasyprint (adds 200-400MB to Docker image), celery/redis (LLM calls are fast enough for NiceGUI's async loop).

### Expected Features

**Must have (table stakes):**
- FR/EN language toggle with all UI strings translated (primary users are French)
- AG Grid column headers and locale pack in French
- Dell partner logo in PDF header (static asset, controlled)
- Custom company logo upload for PDF branding
- Excel export with VM list + workload breakdown sheets
- PDF report labels in French

**Should have (differentiators):**
- LLM fallback classification for "Unknown Reducible" VMs using litellm
- LLM provider configurability (OpenAI / Claude / Ollama / OpenRouter)
- Classification source indicator in AG Grid (rules vs. LLM vs. manual)
- LLM batch mode (20-50 VMs per request to reduce latency)

**Defer (v2+):**
- LLM provider selection UI (env vars sufficient for v1)
- Third language support
- Date/number locale formatting (French dd/mm/yyyy, comma decimals)
- LLM fine-tuning on historical classifications

### Architecture Approach

The existing three-layer architecture (UI / Pipeline-Services / State) remains unchanged. New features slot in as new modules (`i18n/__init__.py`, `pipeline/llm_classifier.py`, `services/excel_export.py`, `services/llm_config.py`) with minimal modifications to existing modules. The critical boundary rule -- `pipeline/` never imports from `ui/` -- is preserved. LLM classification lives in the pipeline layer, called after `classify_dataframe()` and before `calculate()`. i18n is a cross-cutting concern accessed via `t()` from any layer, but locale state is always read from `app.storage.tab`, never from process globals.

**Major components:**
1. **i18n package** (`i18n/`) -- `t()` helper, YAML locale files (en.yaml, fr.yaml), locale state in `app.storage.tab['locale']`
2. **LLM classifier** (`pipeline/llm_classifier.py`) -- async classification of unmatched VMs via litellm, with circuit breaker and timeout
3. **Excel export service** (`services/excel_export.py`) -- multi-sheet workbook generation via pandas + XlsxWriter
4. **PDF branding** (modified `services/pdf_report.py`) -- logo embedding via ReportLab `canvas.drawImage()` with Pillow pre-processing

### Critical Pitfalls

1. **String concatenation breaks translation** -- Audit all f-strings before i18n. Use named placeholders in translation keys: `t('report.project', name=project_name)` not `f"Project: {project_name}"`. Phase: i18n.
2. **Sync LLM calls block NiceGUI event loop** -- Use `litellm.acompletion()` (async) exclusively. Never use sync `completion()` in an async handler. Set 30s timeout. Phase: LLM.
3. **Ollama localhost fails in Docker** -- Make `OLLAMA_BASE_URL` configurable via env var. Document `host.docker.internal:11434` for Docker Desktop. Add health check on startup. Phase: LLM.
4. **PNG transparency renders as black in ReportLab** -- Pre-process logos with Pillow: convert mode `'P'` to `'RGBA'`, use `mask='auto'` in `drawImage()`. Phase: PDF branding.
5. **LLM API key exposure in logs** -- Catch `openai.APIError` specifically, log only status code. Never store keys in session storage. Sanitize VM names before prompts (prompt injection risk). Phase: LLM.

## Implications for Roadmap

Based on research, the milestone should be structured as 5 phases:

### Phase 1: i18n Foundation
**Rationale:** Every subsequent feature's UI strings must go through `t()`. Building i18n first means strings are wrapped naturally as each feature is built. Building it last would require a full retroactive string audit -- double the effort.
**Delivers:** FR/EN language toggle, `t()` helper with YAML locale files, all existing UI strings translated, AG Grid French locale pack, PDF report labels in French.
**Addresses:** Table stakes features (French UI, AG Grid FR headers, PDF FR labels).
**Avoids:** Pitfall 1 (string concatenation), Pitfall 5 (French plural forms), Pitfall 7 (missed string extraction), Pitfall 8 (language switch not updating rendered UI).
**Stack:** python-i18n[YAML]

### Phase 2: Excel Export
**Rationale:** Pure additive feature with zero risk to existing functionality. XlsxWriter adds better formatting than openpyxl write mode. Fast to deliver, validates the download button pattern before PDF branding work.
**Delivers:** Download Excel button on report page, multi-sheet workbook (Summary, Workload Breakdown, VM Detail), styled headers and column widths.
**Addresses:** Table stakes feature (Excel export for sharing with customers).
**Avoids:** Pitfall 11 (BytesIO seek), Pitfall 12 (XlsxWriter modify limitation).
**Stack:** XlsxWriter + existing pandas

### Phase 3: PDF Branding
**Rationale:** Modifies an existing service but is well-isolated. The `generate_report_pdf()` signature change is backwards-compatible (optional kwargs). Riskiest part is PNG transparency handling and maintaining the one-page constraint.
**Delivers:** Dell partner logo in PDF header (static asset), custom company logo upload (PNG/JPEG), logo validation and aspect-ratio-correct scaling.
**Addresses:** Table stakes features (Dell logo, company logo in PDF).
**Avoids:** Pitfall 4 (PNG transparency), Pitfall 13 (one-page PDF constraint), SVG rejection.
**Stack:** Pillow + existing ReportLab

### Phase 4: LLM Classification Fallback
**Rationale:** Highest-risk, lowest-priority feature per user direction. Builds last because it is optional, network-dependent, and has the most failure modes. By this point, the rest of the app is stable. Feature is disabled by default (`LLM_ENABLED=false`).
**Delivers:** Async LLM classification of "Unknown Reducible" VMs, litellm provider abstraction (OpenAI/Claude/Ollama/OpenRouter), env-var configuration, circuit breaker, classification source indicator in AG Grid.
**Addresses:** Differentiator features (LLM fallback, provider configurability, classification source display).
**Avoids:** Pitfall 2 (sync blocking), Pitfall 3 (Ollama Docker), Pitfall 6 (API key exposure), Pitfall 9 (unrecognized categories), Pitfall 10 (timeout hang).
**Stack:** litellm + pydantic-settings

### Phase 5: UX Polish
**Rationale:** Touches every page. Do it last so the full feature set is in place. Avoid polishing pages that will change in earlier phases.
**Delivers:** Loading indicators for LLM, confidence column color coding, improved error states, dark mode refinements, tooltip help on DRR values, consistent notification patterns.
**Addresses:** Cross-cutting UX improvements informed by all prior phases.
**Avoids:** UX pitfalls (no loading state, language preference persistence, generic filenames).

### Phase Ordering Rationale

- **i18n first** is non-negotiable: every feature built after i18n gets French strings for free. Building i18n last means wrapping 200+ strings retroactively.
- **Excel before PDF branding** because Excel is a pure addition (new module, new button), while PDF branding modifies existing code. Ship the safe feature first.
- **LLM last** per explicit user direction and because it has the most failure modes, requires network access, and is an optional differentiator rather than a table-stakes feature.
- **UX polish last** because it touches every page and benefits from seeing the complete feature set before deciding what to polish.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (i18n):** Needs research on python-i18n thread safety under NiceGUI's multi-user concurrency model. AG Grid locale pack injection method should be validated against NiceGUI's bundled AG Grid.
- **Phase 4 (LLM):** Needs research on litellm's OpenRouter-specific model string format and structured output support across providers. Prompt engineering for batch classification needs iteration.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Excel):** pandas + XlsxWriter pattern is thoroughly documented. No unknowns.
- **Phase 3 (PDF branding):** ReportLab `drawImage()` + Pillow is well-established. Logo upload via NiceGUI `ui.upload()` is documented.
- **Phase 5 (UX polish):** NiceGUI component API is stable and well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified on PyPI; compatibility confirmed across pydantic v2 ecosystem |
| Features | HIGH | Feature set validated against existing codebase; dependency graph mapped; anti-features identified |
| Architecture | HIGH | Existing code structure verified; integration points identified with specific module/function references |
| Pitfalls | HIGH | All pitfalls verified against official docs, GitHub issues, and community reports |

**Overall confidence:** HIGH

### Gaps to Address

- **OpenRouter model string format in litellm:** litellm supports 400+ providers including OpenRouter, but the exact model string format (`openrouter/model-name` vs. `model-name` with `api_base`) should be validated during Phase 4 planning. User has OpenRouter credits, so this must work.
- **NiceGUI `app.storage.tab` size limits for base64 logos:** Storing logo bytes as base64 in JSON-backed tab storage may hit limits for large images. Need to validate max practical size or fall back to temp file storage during Phase 3.
- **AG Grid Community locale pack delivery:** The `@ag-grid-community/locale` npm package provides `AG_GRID_LOCALE_FR`, but NiceGUI bundles AG Grid internally. Need to confirm how to inject the locale pack without conflicting with NiceGUI's AG Grid setup.
- **python-i18n thread safety:** NiceGUI is multi-user. `i18n.set('locale', ...)` is a global call. Need to confirm that setting locale per-request before `t()` calls is safe under concurrent requests, or implement a thread-local wrapper.

## Sources

### Primary (HIGH confidence)
- [python-i18n PyPI](https://pypi.org/project/python-i18n/) -- YAML support, API pattern
- [litellm PyPI](https://pypi.org/project/litellm/) and [docs](https://docs.litellm.ai/docs/) -- provider abstraction, structured output
- [XlsxWriter docs](https://xlsxwriter.readthedocs.io/working_with_pandas.html) -- pandas integration
- [Pillow PyPI](https://pypi.org/project/pillow/) -- version 12.1.1
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- env var configuration
- [ReportLab docs](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/) -- Image flowable, canvas.drawImage
- [pandas ExcelWriter](https://pandas.pydata.org/docs/reference/api/pandas.ExcelWriter.html) -- openpyxl/xlsxwriter engines

### Secondary (MEDIUM confidence)
- [NiceGUI i18n Discussion #389](https://github.com/zauberzeug/nicegui/discussions/389) -- community i18n patterns
- [NiceGUI Dynamic Language #4295](https://github.com/zauberzeug/nicegui/discussions/4295) -- per-session locale approach
- [AG Grid localisation docs](https://www.ag-grid.com/javascript-data-grid/localisation/) -- locale pack usage
- [Ollama Docker Networking #3652](https://github.com/ollama/ollama/issues/3652) -- host.docker.internal pattern
- [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) -- prompt injection prevention

### Tertiary (LOW confidence)
- NiceGUI dark mode Tailwind issue #3753 -- dark: CSS variant workarounds (may be fixed in newer NiceGUI)
- Dell partner brand guidelines -- logo tier requirements need partner-specific verification

---
*Research completed: 2026-02-19*
*Ready for roadmap: yes*
