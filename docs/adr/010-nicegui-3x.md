# ADR-010: Target NiceGUI 3.x (not 2.x)

**Status:** Accepted
**Date:** 2026-02-19

## Context

NiceGUI 3.0 was released in October 2025 with breaking changes from 2.x. The project must commit to one major version line.

## Decision

Target NiceGUI 3.x exclusively.

## Rationale

- NiceGUI 2.x is unmaintained following the 3.0 release
- Tailwind CSS 4 support is only available in 3.x
- New upload event API (FileUpload object) is cleaner than the 2.x approach
- 3.x removes the auto-index client, encouraging explicit route definitions

## Alternatives Considered

- **NiceGUI 2.x:** Unmaintained, no security fixes, no Tailwind 4

## Consequences

- Must use `ui.navigate.to()` instead of the removed `ui.open()`
- `rowSelection` requires dict syntax, not string
- FileUpload event handler signature differs from 2.x
- New contributors must read 3.x docs, not older tutorials
