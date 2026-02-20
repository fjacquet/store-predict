# Roadmap — StorePredict

## Milestones

- **v1.0 MVP Sizing Tool** — Phases 1-7 (shipped 2026-02-19)
- **v1.1 i18n, Branding & Intelligence** — Phases 8-12 (active)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-7) — SHIPPED 2026-02-19</summary>

- [x] Phase 1: Project Foundation & DRR Table (2/2 plans)
- [x] Phase 2: File Ingestion Pipeline (2/2 plans)
- [x] Phase 3: Workload Classification Engine (2/2 plans)
- [x] Phase 4: UI — Upload & Review Pages (3/3 plans)
- [x] Phase 5: Calculation & PDF Report (3/3 plans)
- [x] Phase 6: Polish, Docs & Deployment (5/5 plans)
- [x] Phase 7: UI Bug Fixes & Report Enhancements (5/5 plans)

See [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

### Phase 8: i18n Foundation

**Goal:** Internationalize all UI strings with FR/EN toggle, including AG Grid and PDF report labels.

**Requirements:** I18N-01, I18N-02, I18N-03, I18N-04, I18N-05

**Why first:** Every subsequent feature's UI strings must go through `t()` from day one. Building i18n last would require a retroactive audit of 200+ strings.

**Delivers:**

- `i18n/` package with `t()` helper and YAML locale files (en.yaml, fr.yaml)
- FR/EN language toggle in header, persisted in `app.storage.tab['locale']`
- All existing UI strings (upload page, review page, report page) wrapped in `t()`
- AG Grid French locale pack for column headers and built-in text
- PDF report labels (section titles, column names, footer) in selected language

**New deps:** python-i18n[YAML] >=0.3.9

**Key risks:** python-i18n `set('locale')` is global — need per-session wrapper. String concatenation (f-strings) must use named placeholders.

**Plans:** 3/3 plans complete

Plans:

- [x] 08-01-PLAN.md — i18n package infrastructure: t() helper, YAML locale files, locale_toggle component
- [x] 08-02-PLAN.md — UI string wrapping: all 65 strings in pages/components/layout + AG Grid locale
- [x] 08-03-PLAN.md — PDF report locale parameter + i18n unit test suite

---

### Phase 08.1: LiveOptics ZIP extraction (INSERTED)

**Goal:** Accept LiveOptics ZIP exports directly on the upload page. Detect .zip uploads, extract the LiveOptics xlsx using a known filename pattern, and pass xlsx bytes through the existing pipeline unchanged.

**Depends on:** Phase 8
**Plans:** 1/1 plans complete

Plans:

- [ ] 08.1-01-PLAN.md — ZIP extraction module, validation patch, upload page wiring, and test suite

### Phase 9: Excel Export

**Goal:** Export VM table with DRR calculations as a styled multi-sheet .xlsx workbook.

**Requirements:** XLSX-01, XLSX-02, XLSX-03, XLSX-04, XLSX-05

**Why second:** Pure additive feature with zero risk to existing code. Validates the download button pattern before PDF branding work.

**Delivers:**

- Download Excel button on report page (alongside existing PDF download)
- Summary sheet with capacity and performance metrics
- Workload Breakdown sheet with per-category aggregations
- VM Detail sheet with all VMs, workloads, DRR values, and capacities
- Styled headers, auto-sized columns, frozen header rows

**New deps:** XlsxWriter >=3.2.9

**Key risks:** BytesIO seek(0) before download. XlsxWriter cannot modify existing files (write-only). All strings via `t()`.

**Estimated plans:** 1-2

---

### Phase 10: PDF Branding

**Goal:** Add Dell partner logo and optional custom company logo to PDF reports.

**Requirements:** BRAND-01, BRAND-02, BRAND-03, BRAND-04, BRAND-05

**Why third:** Modifies existing `pdf_report.py` but is well-isolated. Optional kwargs keep signature backwards-compatible.

**Delivers:**

- Dell partner logo in PDF header (static asset shipped with app)
- Logo upload UI on report page (PNG/JPEG, validated)
- Custom company logo embedded in PDF alongside Dell logo
- Logo validation (format, size) and aspect-ratio-correct scaling
- PNG transparency handled via Pillow pre-processing (no black backgrounds)

**New deps:** Pillow >=12.1.1

**Key risks:** PNG mode 'P' must be converted to 'RGBA'. One-page constraint — logos must not push content to page 2. `app.storage.tab` size limits for base64 images.

**Estimated plans:** 2

---

### Phase 11: LLM Classification Fallback

**Goal:** Use LLM to classify VMs that the rules engine marks as "Unknown Reducible", with configurable provider support.

**Requirements:** LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07

**Why fourth:** Highest-risk, lowest-priority feature per user direction. Disabled by default. By this point the rest of the app is stable.

**Delivers:**

- `pipeline/llm_classifier.py` — async LLM classification of unmatched VMs
- litellm provider abstraction (OpenAI, Anthropic, Ollama, OpenRouter)
- `services/llm_config.py` — pydantic-settings config with SecretStr for API keys
- Feature disabled by default (`LLM_ENABLED=false`), opt-in via env vars
- Classification source indicator in AG Grid (rules / LLM / manual)
- Response validation against known DRR workload categories
- 30s timeout, circuit breaker, sanitized logging

**New deps:** litellm >=1.61,<2.0 ; pydantic-settings >=2.13.0,<3.0

**Key risks:** Must use `litellm.acompletion()` (async) — sync calls block NiceGUI event loop. Ollama localhost fails in Docker (use `host.docker.internal`). Prompt injection via VM names. OpenRouter model string format needs validation.

**Estimated plans:** 2-3

---

### Phase 12: UX Polish

**Goal:** Improve navigation flow, loading states, error handling, and notification consistency across all pages.

**Requirements:** UX-01, UX-02, UX-03, UX-04

**Why last:** Touches every page. Benefits from seeing the complete feature set before deciding what to polish.

**Delivers:**

- Loading/progress indicators for file upload, LLM classification, report generation
- Meaningful error messages (not generic tracebacks) for all failure modes
- Consistent notification pattern (success/warning/error toasts) across all pages
- Navigation flow improvements: clear next-step guidance after upload and after review
- Dark mode refinements if needed

**New deps:** None

**Key risks:** Must not regress existing functionality. Dark mode Tailwind `dark:` variants unreliable in NiceGUI — use Python conditionals.

**Estimated plans:** 1-2

---

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-02-19 |
| 2. Ingestion | v1.0 | 2/2 | Complete | 2026-02-19 |
| 3. Classification | v1.0 | 2/2 | Complete | 2026-02-19 |
| 4. UI Upload & Review | v1.0 | 3/3 | Complete | 2026-02-19 |
| 5. Calculation & PDF | v1.0 | 3/3 | Complete | 2026-02-19 |
| 6. Polish & Deploy | v1.0 | 5/5 | Complete | 2026-02-19 |
| 7. UI Fixes & Report | v1.0 | 5/5 | Complete | 2026-02-19 |
| 8. i18n Foundation | v1.1 | 3/3 | Complete | 2026-02-20 |
| 8.1. LiveOptics ZIP | v1.1 | 0/1 | Pending | — |
| 9. Excel Export | v1.1 | 0/? | Pending | — |
| 10. PDF Branding | v1.1 | 0/? | Pending | — |
| 11. LLM Classification | v1.1 | 0/? | Pending | — |
| 12. UX Polish | v1.1 | 0/? | Pending | — |
