# ADR-027: PDF In-Memory via BytesIO (No Temp Files)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The generated PDF must be delivered to the user's browser. It can be written to a temp file on disk or kept in memory.

## Decision

Generate the PDF into a `BytesIO` buffer and serve it via `ui.download(bytes)`. No temp files are created.

## Rationale

- Eliminates temp file cleanup logic and the risk of orphaned files
- No race conditions between file creation and file serving
- `BytesIO` is garbage-collected automatically when the function returns
- NiceGUI's `ui.download()` accepts bytes directly

## Alternatives Considered

- **Write to /tmp and serve via static endpoint:** Requires a cleanup strategy (TTL, delete-on-download); introduces race conditions in concurrent sessions

## Consequences

- PDF generation must complete before the download starts (no streaming)
- Memory usage scales with PDF size; for a one-page sizing report this is negligible
- No persistent copy of the generated PDF exists server-side after download
