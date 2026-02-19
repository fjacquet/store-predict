# ADR-018: openpyxl read_only Mode for Format Detection

**Status:** Accepted
**Date:** 2026-02-19

## Context

Uploaded files can be either RVTools or LiveOptics format. The detection logic must identify the format quickly without loading full worksheet data.

## Decision

Open the xlsx workbook with `openpyxl.load_workbook(path, read_only=True)` and inspect sheet names only, then close it before handing off to the appropriate parser.

## Rationale

- Sheet name inspection is sufficient to distinguish RVTools (has `vInfo`) from LiveOptics (has `VMs`)
- `read_only=True` avoids loading cell data, making detection near-instantaneous regardless of file size
- Keeps format detection as a fast, cheap pre-step before the heavier parse

## Alternatives Considered

- **Read with pandas:** Loads the full sheet into memory just to check its name; wasteful
- **Magic byte inspection on sheet names:** Not possible; sheet names are inside the ZIP archive metadata, requiring at least partial parse

## Consequences

- Format detection must be revisited if new source formats share sheet names with existing ones
- The workbook is opened and closed twice total: once for detection, once for parsing
