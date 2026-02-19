# ADR-015: Canonical DataFrame Schema (9 Columns)

**Status:** Accepted
**Date:** 2026-02-19

## Context

RVTools and LiveOptics exports use different column names and layouts. Downstream pipeline stages must not contain format-specific logic.

## Decision

All parsers produce a DataFrame with exactly these columns: `vm_name`, `os_name`, `provisioned_mib`, `in_use_mib`, `datacenter`, `cluster`, `is_template`, `is_powered_on`, `source_format`.

## Rationale

- Downstream stages (classification, calculation, UI) are format-agnostic
- Adding a new source format only requires a new parser; nothing else changes
- Column types are fixed: strings, floats, booleans

## Alternatives Considered

- **Return VMRecord dataclass objects:** VMRecord was created but not used for pipeline data; DataFrames are more efficient for 5000+ row operations and integrate directly with AG Grid

## Consequences

- Parsers bear the full responsibility for mapping source columns to canonical names
- Any field unavailable in a source format is filled with a defined default (empty string or False)
- Schema changes require updating all parsers simultaneously
