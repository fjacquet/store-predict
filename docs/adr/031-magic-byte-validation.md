# ADR-031: Server-Side File Validation with Magic Bytes

**Status:** Accepted
**Date:** 2026-02-19

## Context

Users upload files that the server will parse. Accepting arbitrary file content without validation is a security risk and a source of confusing parse errors.

## Decision

Validate uploaded files server-side with two checks before processing: extension check and magic byte check. XLSX files must begin with the ZIP header (`PK\x03\x04`); CSV files must be UTF-8 decodable. Files failing either check are rejected before any temp file write.

## Rationale

- Extension alone can be spoofed; magic bytes verify the actual file format
- XLSX is a ZIP archive; the PK header check is a reliable minimum-cost assertion
- UTF-8 decodability for CSV catches binary uploads masquerading as text
- Rejection before temp file write limits attack surface

## Alternatives Considered

- **python-magic library:** Requires libmagic system dependency; complicates Docker image; stdlib checks are sufficient for two known formats

## Consequences

- Files with correct extension but wrong format produce a clear rejection message rather than a confusing parse error
- Only XLSX and CSV formats are accepted; all other uploads are rejected regardless of content
