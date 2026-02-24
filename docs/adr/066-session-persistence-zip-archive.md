# ADR-066: Session persistence via self-contained zip archive

**Date:** 2026-02-24
**Status:** Accepted

## Context

Pre-sales engineers build sizing sessions that may take 20–30 minutes to
complete (classification review, manual overrides, layout tuning, compute
adjustments). When they need to resume work the next day, share a session
with a colleague, or re-open a session after a browser restart, all state is
lost because StorePredict holds data in `app.storage.tab` (in-memory,
tab-scoped).

Three persistence options were considered:

1. **Browser `localStorage`** — limited to ~5 MB, not portable between machines,
   tied to browser profile, cleared on browser data wipe.
2. **Server-side project library** — requires a database, authentication,
   multi-user data isolation, and a new UI surface for browsing/deleting saved
   sessions. Significant scope increase.
3. **File-based zip archive** — user downloads a `.zip` file and re-uploads it
   later. No server state, fully portable, human-inspectable.

## Decision

Implement a self-contained `.zip` archive as the session persistence format.
A new `save_session_zip()` function in `pipeline/session_archive.py` bundles:

- A `session.json` file at the zip root containing a JSON snapshot of all
  session state (VM list, workload classifications, DRR overrides, layout
  settings, compute settings, project name, selected scope).
- The original uploaded file (RVTools `.xlsx`, LiveOptics `.xlsx`/`.csv`, or
  dual-source merge result) stored at its original filename path.

The `session.json` snapshot uses `schema_version: 1` for forward compatibility.

Restore is handled by re-uploading the `.zip` on the Upload page. The existing
upload handler detects session zips via the `SESSION_ZIP_SENTINEL` (see
ADR-067) before the LiveOptics zip extraction path, calls
`restore_session_zip()`, and updates `app.storage.tab` directly.

## Rationale

- **Portability:** A file on disk is portable between machines, shareable via
  email or Teams, and doesn't require the server to be running.
- **No infrastructure cost:** Zero database, zero auth, zero multi-user
  isolation complexity.
- **Human-inspectable:** Engineers can open the zip and read `session.json`
  to debug unexpected classification results.
- **Minimal code surface:** stdlib `zipfile` + `json`; no new dependencies.
- **Existing UX re-use:** The Upload page is the natural entry point — users
  already know how to upload files there.

## Consequences

- **Positive:** Engineers can share sessions across machines and colleagues.
- **Positive:** Sessions survive browser restarts, tab closes, and server
  restarts.
- **Positive:** File-based storage means no server-side cleanup or quota
  management.
- **Negative:** User is responsible for managing `.zip` files on their
  filesystem (naming, storing, finding).
- **Negative:** Session state is a point-in-time snapshot; no merge or
  incremental update — re-saving overwrites the previous file.
- **Out of scope:** Browser auto-save, named project library, and session
  merge with a fresh upload are explicitly deferred (see REQUIREMENTS.md
  Future section).
