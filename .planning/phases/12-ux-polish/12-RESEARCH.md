# Phase 12: UX Polish - Research

**Researched:** 2026-02-20
**Domain:** NiceGUI UI patterns — loading indicators, error handling, notification consistency, navigation flow
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Loading/progress indicators during file upload, LLM classification, and report generation | `ui.spinner`, `ui.linear_progress`, `ui.notification` with spinner, button `.disable()`/`.enable()` pattern |
| UX-02 | Meaningful error messages for upload failures, LLM errors, and export failures | Typed `ui.notify()` with `type="negative"`, `IngestionError.message` field, i18n error keys |
| UX-03 | Consistent notification pattern (success/warning/error) across all pages | `ui.notify()` type matrix (positive/negative/warning/info), standardized call site pattern |
| UX-04 | Navigation flow improvements (clear next-step guidance after upload, after review) | Prominent CTA buttons post-upload, next-step hint label after success, `ui.navigate.to()` |
</phase_requirements>

---

## Summary

Phase 12 polishes the three existing pages (upload, review, report) without changing their functional logic. The codebase is already well-structured: `_handle_upload` is async, `ui.notify()` is used throughout, and `IngestionError` carries a user-facing `.message` field. The main gaps are: (1) no visual feedback while the upload pipeline runs — the page is silent for the several seconds that ingestion + classification + optional LLM call take; (2) the bare `f"Unexpected error: {exc}"` fallback leaks raw exception text; (3) `ui.notify()` type values are used inconsistently (sometimes `"info"` for informational LLM messages, sometimes `"positive"`); (4) after a successful upload the user is navigated automatically but there is no explicit "what happens next" guidance; after opening /review directly with no data only a plain text link back to upload is shown.

The recommended approach is: add a `ui.spinner` + `ui.linear_progress(value=0, show=True)` overlay during upload processing (show/hide via `.visible`), disable the upload widget or button while processing, improve the bare `except Exception` clause to use categorized i18n keys, lock down the `ui.notify()` type to the four canonical values (positive/negative/warning/info), and add a prominent "Go to Review" CTA card after a successful upload notification instead of relying on auto-navigation alone.

**Primary recommendation:** Use `ui.spinner` + `.visible` toggling and `button.disable()`/`.enable()` as the standard loading pattern; do not reach for `ui.notification` (the persistent variant) for simple one-shot feedback — keep `ui.notify()` for all toasts.

---

## Standard Stack

### Core (already in use — no new deps)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `ui.spinner` | NiceGUI built-in | Rotating loading indicator | Native, zero-dep, Quasar-backed |
| `ui.linear_progress` | NiceGUI built-in | Determinate/indeterminate bar | Matches Quasar QLinearProgress |
| `ui.notify()` | NiceGUI built-in | Toast notifications | Already used on all 3 pages |
| `ui.notification` | NiceGUI built-in | Persistent updatable notification | Use for LLM classification only (long-running) |
| `button.disable()` / `.enable()` | NiceGUI built-in | Prevent double-submit | Official API, not `.props("disabled")` |
| `run.io_bound()` | `nicegui.run` | Run blocking sync code off event loop | Prevents UI freeze during ingestion |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ui.spinner` + `.visible` | `ui.linear_progress(indeterminate=True)` | Linear bar is more "progress" looking; spinner is lighter — use spinner for upload, linear for LLM batch |
| `ui.notify()` | `ui.notification` (persistent) | Persistent needed only when you want to update message mid-operation (LLM batch) |
| Auto-navigate after upload | Explicit CTA button | CTA is clearer; keep auto-navigate AND show a card with "View Results" button as fallback |

---

## Architecture Patterns

### Recommended Project Structure (unchanged)

```
src/store_predict/
├── ui/
│   ├── pages/
│   │   ├── upload.py       # Add spinner overlay, disable/enable upload widget
│   │   ├── review.py       # Add "Generate Report" CTA prominence, no_data improvement
│   │   └── report.py       # Add loading state on PDF/Excel download buttons
│   ├── components/
│   │   └── (no new files)  # Keep loading pattern inline per-page for now
│   └── layout.py           # Nav links — add active-page highlight if desired
└── i18n/locales/
    ├── en.yaml             # Add error.*, upload.processing, nav.* keys
    └── fr.yaml             # Mirror all new keys in French
```

### Pattern 1: Spinner Overlay During Async Handler

**What:** Show a spinner + disable the upload widget while `_handle_upload` runs. Hide on completion (success or error).

**When to use:** Any async handler that takes >500ms (upload pipeline, LLM batch).

```python
# Source: NiceGUI docs + Discussion #816 + Discussion #2729
# In upload_page():
spinner = ui.spinner(size="xl").classes("absolute top-1/2 left-1/2").props("color=primary")
spinner.visible = False

progress = ui.linear_progress(value=0).props("indeterminate").classes("w-full")
progress.visible = False

upload_widget = ui.upload(
    label=t("upload.drop_label"),
    on_upload=_handle_upload,
    auto_upload=True,
    max_file_size=50_000_000,
).props('accept=".xlsx,.csv,.zip"').classes("w-full")

# In _handle_upload():
async def _handle_upload(e: object) -> None:
    upload_widget.disable()
    spinner.visible = True
    progress.visible = True
    try:
        # ... pipeline ...
        ui.notify(t("upload.loaded_notify", count=len(df)), type="positive")
        ui.navigate.to("/review")
    except IngestionError as exc:
        ui.notify(exc.message, type="negative")
    except Exception as exc:
        ui.notify(t("error.unexpected"), type="negative")
    finally:
        spinner.visible = False
        progress.visible = False
        upload_widget.enable()
```

**Key constraint:** `upload_widget` must be defined in the outer `upload_page` scope before `_handle_upload` closes over it. Use a mutable container (`list`) or a class if closure over a local var is tricky.

### Pattern 2: Persistent Notification for LLM Batch

**What:** Replace the simple `ui.notify(t("llm.classifying"), type="info")` with a persistent `ui.notification` that you can update with the result count.

**When to use:** LLM classification — the only operation that is genuinely long and where the user benefits from seeing progress update in place.

```python
# Source: NiceGUI docs — ui.notification (persistent)
# In _handle_upload():
if llm_cfg.enabled:
    notif = ui.notification(t("llm.classifying"), spinner=True, timeout=None, type="info")
    try:
        vm_records = await classify_unknown_vms_async(vm_records, drr_table_for_llm, llm_cfg)
        df = pd.DataFrame(vm_records)
        llm_count = sum(1 for r in vm_records if r.get("classification_confidence") == "llm")
        if llm_count > 0:
            notif.message = t("llm.classified_notify", count=llm_count)
            notif.type = "positive"
            notif.spinner = False
        else:
            notif.close()
    except Exception:
        notif.message = t("llm.error")
        notif.type = "negative"
        notif.spinner = False
```

**Note:** `ui.notification` supports `notif.message = ...` and `notif.type = ...` attribute assignment for in-place updates (verified in NiceGUI docs). Set `timeout=None` to prevent auto-dismiss mid-operation.

### Pattern 3: Button Disable/Enable for Report Downloads

**What:** Disable PDF and Excel download buttons during generation to prevent double-click.

**When to use:** `_on_download` and `_on_download_excel` on report page.

```python
# Source: NiceGUI Discussion #1864, #560
pdf_btn = ui.button(t("report.download_pdf"), on_click=lambda: _on_download_guarded(pdf_btn, summary, project_name), icon="download").classes("bg-blue-700 text-white")

async def _on_download_guarded(btn: ui.button, summary: object, project_name: str) -> None:
    btn.disable()
    try:
        _on_download(summary, project_name)
    finally:
        btn.enable()
```

**Note:** `.disable()` / `.enable()` are the official API. Using `.props("disabled")` works but `.props("disable")` (Quasar prop, no "d") is the underlying mechanism — prefer the method form.

### Pattern 4: Next-Step Guidance Card After Upload

**What:** After successful upload, before navigating away, show a brief CTA so users understand what is happening. Also improve the "no data" state on review and report pages.

**When to use:** UX-04 — navigation flow.

```python
# After save_session_data(), before navigate:
ui.notify(t("upload.loaded_notify", count=len(df)), type="positive")
# Short delay lets the notify render, then navigate
await asyncio.sleep(0.3)
ui.navigate.to("/review")
```

For the no-data state on review/report pages, replace the plain `ui.label` + `ui.link` with a `ui.card` + `ui.icon` + `ui.button`:

```python
# review_page() no-data state — improved
with ui.card().classes("p-8 items-center gap-4 text-center"):
    ui.icon("cloud_upload", size="4rem").classes("text-blue-400")
    ui.label(t("review.no_data")).classes("text-xl text-gray-500")
    ui.button(t("report.go_to_upload"), on_click=lambda: ui.navigate.to("/upload"), icon="arrow_forward").classes("bg-blue-700 text-white")
```

### Pattern 5: Blocking Ingestion in Thread Pool

**What:** `ingest_file()` and `classify_dataframe()` are synchronous and can take 1-3 seconds on large files. Wrapping them in `run.io_bound` frees the event loop so the spinner actually renders.

**When to use:** Any sync call taking >100ms inside an async page handler.

```python
# Source: nicegui.run documentation, Discussion #2018
from nicegui import run

df = await run.io_bound(ingest_file, tmp_path)
df = await run.io_bound(classify_dataframe, df, registry)
```

**Critical caveat:** `run.io_bound` runs in a thread pool. Code inside it CANNOT access `app.storage.tab` or `app.storage.user` — those are context-local. Only pass plain data (DataFrames, paths) in and out.

### Anti-Patterns to Avoid

- **Anti-pattern: Calling `.props("disabled")` instead of `.disable()`** — `.props("disabled")` toggles a Quasar prop but `.disable()` is the element API. Use `.disable()` / `.enable()`.
- **Anti-pattern: `f"Unexpected error: {exc}"` in notify** — Leaks stack trace / exception class names to users. Always use an i18n key: `t("error.unexpected")`.
- **Anti-pattern: `dark:` Tailwind variants** — Unreliable in NiceGUI. Use Python conditionals and `app.storage.user["dark_mode"]` checks where color customization is needed.
- **Anti-pattern: `ui.notification` for all toasts** — Reserve persistent `ui.notification` for LLM (long-running). Use `ui.notify()` everywhere else.
- **Anti-pattern: Building spinner inside the async task** — Spinner must be created before the task starts (in the synchronous page setup), then shown/hidden via `.visible`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loading indicator | Custom JS overlay | `ui.spinner` + `.visible` | NiceGUI-native, no JS needed |
| Progress bar | Custom div with width style | `ui.linear_progress` | Quasar QLinearProgress, accessible |
| Toast notifications | Custom notification widget | `ui.notify()` | Built-in, supports type, timeout, position |
| Updatable notification | Re-rendering notify | `ui.notification` with attribute updates | Designed for in-place updates |
| Button lock | `time.sleep()` debounce | `.disable()` / `.enable()` | Event-loop-safe, no thread issues |
| Thread offloading | `threading.Thread` directly | `await run.io_bound(fn, *args)` | Integrates with asyncio event loop |

**Key insight:** NiceGUI's Quasar-backed element library already covers every UX need in this phase. Any custom solution adds JS, CSS, or threading complexity with no benefit.

---

## Common Pitfalls

### Pitfall 1: Spinner Never Shows (Blocking Event Loop)

**What goes wrong:** `spinner.visible = True` then immediately calling a blocking sync function — the spinner never renders because the event loop is blocked.

**Why it happens:** NiceGUI's UI updates are sent to the browser at the next event loop yield. If the next thing after `spinner.visible = True` is a blocking call, the yield never happens before the pipeline completes.

**How to avoid:** Wrap sync calls in `await run.io_bound(fn, *args)`. After `spinner.visible = True`, the `await` yields the loop, the browser receives the update, and the spinner renders.

**Warning signs:** Spinner appears and disappears instantly (less than one frame).

### Pitfall 2: Closure Over Loop Variable / Widget Not in Scope

**What goes wrong:** `spinner` and `upload_widget` defined inside `upload_page()` are not accessible inside `_handle_upload()` (a module-level function).

**Why it happens:** `_handle_upload` is currently module-level, taking `e` only. It cannot close over page-local variables.

**How to avoid:** Two options:
1. Move `_handle_upload` to be defined as a local `async def` inside `upload_page()` — it can then close over `spinner`, `progress`, `upload_widget`.
2. Pass the widgets as outer-scope state using `functools.partial` or a closure wrapper. Option 1 is cleaner.

**Warning signs:** `NameError: name 'spinner' is not defined` inside `_handle_upload`.

### Pitfall 3: `ui.notification` Not Closing on Error Path

**What goes wrong:** The persistent `ui.notification` used for LLM classification stays on screen if an exception is raised and the close/update logic is skipped.

**Why it happens:** Exception bypasses the update code.

**How to avoid:** Always wrap in try/except/finally or explicitly handle all branches. Set `timeout=None` only while operation is running; set a finite timeout after update.

### Pitfall 4: Double-Submit Race on Upload

**What goes wrong:** User drops a second file before the first finishes processing. Two `_handle_upload` coroutines run concurrently, both try to write to session state, last one wins.

**Why it happens:** NiceGUI's upload widget does not have built-in debounce.

**How to avoid:** `upload_widget.disable()` at start of handler, `upload_widget.enable()` in finally. The disabled widget prevents the second upload event.

### Pitfall 5: `run.io_bound` + `app.storage` Access

**What goes wrong:** Code inside `run.io_bound` tries to call `app.storage.tab.get(...)` → `RuntimeError` (no NiceGUI context in thread).

**Why it happens:** `app.storage.tab` is context-local to the NiceGUI WebSocket connection, not thread-safe.

**How to avoid:** Read from storage BEFORE calling `run.io_bound`, pass raw data as arguments. Write back to storage AFTER `await run.io_bound(...)` returns.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### Showing / Hiding a Spinner

```python
# Source: NiceGUI docs ui.spinner + Discussion #816
spinner = ui.spinner(size="xl")
spinner.visible = False   # hidden initially

# In async handler:
spinner.visible = True
try:
    result = await run.io_bound(blocking_fn, arg)
finally:
    spinner.visible = False
```

### Canonical ui.notify() Call Matrix

```python
# Source: NiceGUI docs ui.notify — four types in use in this project
ui.notify(t("..."), type="positive")   # success
ui.notify(t("..."), type="negative")   # error
ui.notify(t("..."), type="warning")    # non-fatal warning
ui.notify(t("..."), type="info")       # informational

# Optional parameters (use sparingly for UX consistency)
ui.notify(t("..."), type="negative", close_button=True, timeout=0)   # persistent error
ui.notify(t("..."), type="positive", timeout=3000)                    # 3s auto-dismiss
```

### Persistent Notification Update (LLM Pattern)

```python
# Source: NiceGUI docs ui.notification
notif = ui.notification(t("llm.classifying"), spinner=True, timeout=None, type="info")
# ... await long_operation() ...
notif.message = t("llm.classified_notify", count=n)
notif.type = "positive"
notif.spinner = False
notif.timeout = 3  # auto-dismiss after 3s now that it's done
```

### run.io_bound for Sync Pipeline

```python
# Source: NiceGUI Discussion #2018
from nicegui import run

# In async handler:
df = await run.io_bound(ingest_file, tmp_path)
registry = RuleRegistry(build_default_rules())
df = await run.io_bound(classify_dataframe, df, registry)
# app.storage only accessible AFTER the await:
save_session_data(df, get_project_name())
```

### Button Lock Pattern

```python
# Source: NiceGUI Discussion #1864
async def _on_download_guarded() -> None:
    pdf_btn.disable()
    try:
        _on_download(summary, project_name)
    finally:
        pdf_btn.enable()

pdf_btn = ui.button(t("report.download_pdf"), on_click=_on_download_guarded, icon="download")
```

### Improved No-Data State

```python
# Replace plain label + link with card + button (UX-04)
with ui.card().classes("p-8 gap-4 items-center text-center mx-auto max-w-md"):
    ui.icon("cloud_upload", size="4rem").classes("text-blue-300")
    ui.label(t("review.no_data")).classes("text-xl text-gray-500")
    ui.button(
        t("report.go_to_upload"),
        on_click=lambda: ui.navigate.to("/upload"),
        icon="arrow_forward",
    ).classes("bg-blue-700 text-white")
```

---

## Current Codebase Gaps (Baseline Assessment)

| Page | Gap | Requirement |
|------|-----|-------------|
| `upload.py` | No spinner/progress during `_handle_upload` (silent for 2-10s) | UX-01 |
| `upload.py` | `except Exception as exc: ui.notify(f"Unexpected error: {exc}", ...)` leaks raw exception | UX-02 |
| `upload.py` | `_handle_upload` is module-level — cannot close over page-local widgets | UX-01 (implementation detail) |
| `upload.py` | No next-step CTA after success (relies on auto-navigate only) | UX-04 |
| `review.py` | No-data state uses plain `ui.label` + `ui.link` — not prominent | UX-04 |
| `review.py` | `ui.navigate.to("/report")` on "Generate Report" button — no loading state | UX-01 |
| `report.py` | Download buttons have no loading/disabled state — double-click possible | UX-01 |
| `report.py` | Logo upload errors use `str(exc)` — may expose internal messages | UX-02 |
| `report.py` | No-data state uses plain label + link | UX-04 |
| All pages | `"info"` type used for LLM notification but not consistently defined | UX-03 |

---

## i18n Keys to Add

New keys needed in both `en.yaml` and `fr.yaml`:

```yaml
# en.yaml additions
error:
  unexpected: "An unexpected error occurred. Please try again."
  llm_failed: "AI classification encountered an error. Rule-based results are used."

upload:
  processing: "Processing file..."
  go_to_review: "View Results"

llm:
  error: "AI classification failed — rule-based results kept."

review:
  go_to_report: "Generate Report"

report:
  generating_pdf: "Generating PDF..."
  generating_excel: "Generating Excel..."
```

```yaml
# fr.yaml mirrors
error:
  unexpected: "Une erreur inattendue s'est produite. Veuillez réessayer."
  llm_failed: "La classification IA a rencontré une erreur. Les résultats basés sur les règles sont utilisés."

upload:
  processing: "Traitement du fichier en cours..."
  go_to_review: "Voir les résultats"

llm:
  error: "La classification IA a échoué — résultats basés sur les règles conservés."

review:
  go_to_report: "Générer le rapport"

report:
  generating_pdf: "Génération du PDF..."
  generating_excel: "Génération du fichier Excel..."
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `ui.link()` for no-data navigation | `ui.button()` with icon + card | More prominent, clearly actionable |
| `f"Unexpected error: {exc}"` | `t("error.unexpected")` | No internal detail leakage |
| `ui.notify("llm.classifying")` then separate result notify | `ui.notification` with in-place update | Single persistent toast, less notification noise |
| Module-level `_handle_upload` | Local async def inside `upload_page()` | Enables closure over page-scoped widgets |

**Deprecated/outdated in this codebase:**
- `f"Unexpected error: {exc}"` — replace with i18n key in Phase 12
- Bare `ui.link()` for no-data CTAs — replace with `ui.button()` cards

---

## Open Questions

1. **Should `ingest_file` + `classify_dataframe` be wrapped in `run.io_bound`?**
   - What we know: Both are synchronous and can take 1-5s on large files. `run.io_bound` would let the spinner render during processing.
   - What's unclear: Whether these functions use any thread-unsafe globals (registry build might).
   - Recommendation: Check `build_default_rules()` and `classify_dataframe()` for global state before wrapping. If safe, wrap. If not, accept the event loop block but document it.

2. **Active navigation highlighting in header**
   - What we know: `layout.py` uses plain `ui.link()` for all nav items with no active state.
   - What's unclear: Whether the planner should include this as part of UX-04 or defer it.
   - Recommendation: Include if it can be done in <30 min (check `ui.link` or add `.classes("underline")` via Python conditional on current path). Otherwise defer.

3. **Report page — "Generate Report" timing**
   - What we know: `_on_download` calls `generate_report_pdf` synchronously inside a lambda — not awaitable.
   - What's unclear: Whether the plan should convert this to async with `run.io_bound` or just disable the button.
   - Recommendation: At minimum disable the button. Converting to async is optional UX polish and low-risk.

---

## Sources

### Primary (HIGH confidence)
- [NiceGUI ui.spinner docs](https://nicegui.io/documentation/spinner) — spinner element
- [NiceGUI ui.linear_progress docs](https://nicegui.io/documentation/linear_progress) — linear progress bar
- [NiceGUI ui.notify docs](https://nicegui.io/documentation/notify) — toast notifications
- [NiceGUI ui.notification docs](https://nicegui.io/documentation/notification) — persistent updatable notifications
- Codebase direct read: `upload.py`, `review.py`, `report.py`, `layout.py`, `errors.py`, `en.yaml`, `fr.yaml` — baseline gaps identified directly

### Secondary (MEDIUM confidence)
- [NiceGUI Discussion #2729](https://github.com/zauberzeug/nicegui/discussions/2729) — spinner during background task pattern
- [NiceGUI Discussion #816](https://github.com/zauberzeug/nicegui/discussions/816) — spinner in event handler
- [NiceGUI Discussion #2018](https://github.com/zauberzeug/nicegui/discussions/2018) — run.io_bound usage pattern
- [NiceGUI Discussion #1864](https://github.com/zauberzeug/nicegui/discussions/1864) — button auto-disable during async click
- [NiceGUI Discussion #560](https://github.com/zauberzeug/nicegui/discussions/560) — enable/disable buttons

### Tertiary (LOW confidence)
- WebSearch synthesis: `ui.notification` attribute update API (`notif.message`, `notif.type`, `notif.spinner`) — needs verification against live NiceGUI source if planner uses it.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — NiceGUI built-ins, no new deps, verified against docs
- Architecture: HIGH — directly read all 3 page files; gaps are clear and specific
- Pitfalls: HIGH — closure issue and event-loop-blocking are verified common patterns in NiceGUI community
- i18n keys: HIGH — direct read of en.yaml/fr.yaml confirmed missing keys
- `ui.notification` attribute update API: MEDIUM — found in docs but exact attribute names (`notif.spinner`, `notif.timeout`) should be spot-checked before task writing

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (NiceGUI stable; 30-day window)
