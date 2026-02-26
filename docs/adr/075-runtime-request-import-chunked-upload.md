# ADR-075: Runtime Request Import for Chunked Upload Endpoint

## Status

Accepted

## Date

2026-02-26

## Context

The chunked upload endpoint (`/api/upload/{token}`) registered via FastAPI's
`@app.post` decorator stopped working after the module adopted
`from __future__ import annotations` (PEP 563 deferred evaluation).

The `starlette.requests.Request` type was imported inside a `TYPE_CHECKING`
block, which is the standard pattern recommended by ruff's TC002 rule. However,
FastAPI resolves parameter annotations **at runtime** to decide how to inject
dependencies (path params, query params, body, or the raw `Request` object).
With deferred annotations, `Request` became the string `'Request'` at runtime.
Because it could not be resolved, FastAPI treated the parameter as a required
query field and returned **HTTP 422** on every upload request — silently
breaking all file uploads with zero server-side logging.

Additionally, `IngestionError` exceptions raised during post-upload file
processing were caught but never logged, making the failure completely
invisible in server logs and UI.

## Decision

1. **Import `Request` at runtime** with `# noqa: TC002` to suppress the ruff
   rule. This is required for any type used in a FastAPI route signature when
   `from __future__ import annotations` is active.
2. **Log all `IngestionError`** at WARNING level before attempting the
   `ui.notify` call, so server logs always reflect upload failures regardless
   of whether the client receives the notification.
3. **Persistent error notifications** (`timeout=0`) for upload errors, so
   transient toast messages cannot silently auto-dismiss.
4. **Broaden ZIP extraction** to fall back to any `.xlsx` member in the archive
   when the canonical LiveOptics filename pattern is not matched.
5. **Off-by-one guard in chunk assembly** — assemble when `max_end >= total_size`
   in addition to the byte-count check, in case Quasar's `Content-Range` total
   is off by one.

## Consequences

- Upload endpoint returns 200 and correctly assembles files.
- ZIP files containing RVTools exports or non-standard LiveOptics names are
  now accepted.
- Any processing error is visible in both server logs (WARNING) and the UI
  (persistent red notification).
- Developers must remember that FastAPI route parameters annotated with
  framework types (`Request`, `Response`, `WebSocket`) must be runtime imports,
  not `TYPE_CHECKING`-only imports, when `from __future__ import annotations`
  is used.
