# ADR-019: Shared _build_liveoptics_df Helper (DRY)

**Status:** Accepted
**Date:** 2026-02-19

## Context

LiveOptics data arrives as either `.xlsx` or `.csv`. Both formats contain the same columns and require identical DataFrame construction after the raw file is loaded.

## Decision

Both `parse_liveoptics_xlsx` and `parse_liveoptics_csv` delegate DataFrame construction to a shared private helper `_build_liveoptics_df`. The two public functions differ only in how they read the raw file (`pd.read_excel` vs `pd.read_csv`).

## Rationale

- Column mapping, renaming, and type coercion logic exists in exactly one place
- A bug fix or column alias addition applies to both formats automatically
- Makes the parsers trivially thin wrappers around the shared helper

## Alternatives Considered

- **Duplicate DataFrame construction code:** Any future column mapping change must be applied twice; drift between implementations is likely

## Consequences

- The helper is private (prefixed `_`) and considered an implementation detail of the parsers module
- Tests for xlsx and csv formats share fixture data and assert identical output schema
