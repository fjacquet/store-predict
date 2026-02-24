# ADR-067: SESSION_ZIP_SENTINEL to distinguish session archives from LiveOptics zips

**Date:** 2026-02-24
**Status:** Accepted

## Context

StorePredict already accepts LiveOptics `.zip` archives on the Upload page
(since v1.1). When a user re-uploads a StorePredict session archive (also a
`.zip`), the upload handler must distinguish between the two without forcing
users to use a different file extension.

A naive approach would check the filename or MIME type, but both are under
user control and can be renamed. A structural check on the zip contents is
more reliable.

## Decision

Define `SESSION_ZIP_SENTINEL = "session.json"` as a constant in
`pipeline/session_archive.py`. Every StorePredict session archive contains
this file at the zip root. The `is_session_zip(content: bytes) -> bool`
helper function checks for its presence without parsing the JSON.

In `upload.py`, the session zip detection runs **before** the LiveOptics zip
extraction branch:

```python
if is_session_zip(content):
    _handle_session_restore(content)
    return
# ... existing LiveOptics zip extraction path unchanged
```

LiveOptics archives never contain a `session.json` file, so there is no risk
of false positives. The sentinel check is O(1) (zip directory scan only, no
file extraction).

## Rationale

- **Structural over naming:** Checking zip contents is robust against file
  renames and user errors.
- **Zero false positives:** LiveOptics archives contain xlsx/csv/xml files;
  `session.json` is a StorePredict-specific name that would never appear in a
  vendor export.
- **Order matters:** Checking session zip first means the LiveOptics path is
  reached only for genuine LiveOptics archives. The existing extraction code
  is unchanged, eliminating regression risk.
- **`is_session_zip` never raises:** Catches all exceptions internally and
  returns `False` on any error, making the upload handler safe against
  malformed zip content.

## Consequences

- **Positive:** Session restore and LiveOptics zip extraction coexist on the
  same Upload page without UX changes.
- **Positive:** The sentinel is part of the documented archive schema, so
  third-party tools can detect StorePredict archives reliably.
- **Negative:** If a future LiveOptics export format happens to include a file
  named `session.json`, it would be misidentified as a StorePredict archive
  (extremely unlikely; monitor if LiveOptics format changes).
