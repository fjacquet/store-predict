# Phase 12: UX Polish - Research

**Researched:** 2026-02-20
**Domain:** NiceGUI UI patterns — loading indicators, error handling, notification consistency, navigation flow
**Confidence:** HIGH

## Summary

Phase 12 polishes the three existing pages (upload, review, report) without changing functional logic. The main gaps are: no visual feedback during the upload pipeline (several seconds of silence); raw exception text leaking through the bare `except Exception` handler; inconsistent `ui.notify()` type values; and weak "no data" states on the review and report pages. All fixes use existing NiceGUI built-ins — no new dependencies are needed.

## Key Findings

### Spinner + Disable Pattern for Upload

Show a spinner and disable the upload widget while `_handle_upload` runs. Hide/enable in `finally` to guarantee cleanup on both success and error paths.

```python
# In upload_page():
spinner = ui.spinner(size="xl").props("color=primary")
spinner.visible = False
upload_widget = ui.upload(on_upload=_handle_upload, auto_upload=True)

async def _handle_upload(e):
    upload_widget.disable()
    spinner.visible = True
    try:
        # ... pipeline ...
        ui.notify(t("upload.loaded_notify", count=n), type="positive")
        ui.navigate.to("/review")
    except IngestionError as exc:
        ui.notify(str(exc), type="negative")
    except Exception:
        ui.notify(t("error.unexpected"), type="negative")
    finally:
        spinner.visible = False
        upload_widget.enable()
```

Use `.disable()` / `.enable()` methods — the official NiceGUI API. Avoid `.props("disabled")` which uses the Quasar prop name directly and is less readable.

### Persistent Notification for LLM Batch

Use `ui.notification` (the persistent variant) only for the LLM classification step — it is the sole operation where updating the message in place is meaningful. All other feedback uses `ui.notify()` (one-shot toasts).

```python
notif = ui.notification(t("llm.classifying"), spinner=True, timeout=None, type="info")
# ... after LLM completes ...
notif.message = t("llm.classified_notify", count=llm_count)
notif.type = "positive"
notif.spinner = False
```

`ui.notification` supports attribute assignment for in-place updates. Set `timeout=None` to prevent auto-dismiss mid-operation.

### run.io_bound for Sync Pipeline Calls

`ingest_file()` and `classify_dataframe()` are synchronous and take 1–3 seconds on large files. Wrapping them in `run.io_bound` releases the event loop so the spinner actually renders.

```python
from nicegui import run
df = await run.io_bound(ingest_file, tmp_path)
```

### Canonical notify() Types

Lock down `ui.notify()` to the four canonical Quasar types. Do not mix `"info"` and `"positive"` for similar events across pages.

| Situation | type |
|-----------|------|
| Success | `"positive"` |
| User input error | `"negative"` |
| Degraded result (LLM skipped) | `"warning"` |
| Neutral information | `"info"` |

### No-Data State as Card with CTA

Replace plain `ui.label` + `ui.link` no-data states with a card containing an icon and a styled button. This makes the "what to do next" obvious without relying solely on the user knowing the URL structure.

```python
with ui.card().classes("p-8 items-center gap-4 text-center"):
    ui.icon("cloud_upload", size="4rem").classes("text-blue-400")
    ui.label(t("review.no_data")).classes("text-xl text-gray-500")
    ui.button(
        t("report.go_to_upload"),
        on_click=lambda: ui.navigate.to("/upload"),
        icon="arrow_forward",
    ).classes("bg-blue-700 text-white")
```

### Short Delay Before Navigate

A brief `await asyncio.sleep(0.3)` before `ui.navigate.to("/review")` lets the success toast render before the page transitions. Without it, the notification may appear on the next page.

## Anti-Patterns

- **Leaking raw exception text to users:** The bare `except Exception as exc: ui.notify(f"Unexpected error: {exc}")` pattern exposes internal details. Replace with a generic i18n key (`t("error.unexpected")`) and log the full exception server-side.
- **Using `ui.notification` for simple one-shot feedback:** `ui.notification` is a persistent element that must be explicitly closed. For anything that does not need in-place updates, use `ui.notify()` (the toast variant).
- **Calling `ingest_file()` synchronously inside an async handler:** The event loop blocks during the call, so the spinner never renders. Always use `await run.io_bound(...)` for sync pipeline calls over ~100ms.

## Dependencies

No new dependencies. All loading, notification, and navigation patterns use existing NiceGUI built-ins. New i18n keys for `error.unexpected`, `upload.processing`, and `review.no_data` must be added to both `en.yaml` and `fr.yaml`.
