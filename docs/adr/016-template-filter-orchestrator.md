# ADR-016: Template VM Filtering at Orchestrator Level

**Status:** Accepted
**Date:** 2026-02-19

## Context

RVTools exports include template VMs that should be excluded from sizing. The question is where this filtering policy belongs.

## Decision

Filter template VMs inside `ingest_file()` (the orchestrator), not inside individual parsers.

## Rationale

- Parsers are pure data transformers; they should not encode business policy
- Centralising the filter means a single code path to audit or change
- The `is_template` column is available in the canonical schema (ADR-015) for the filter to act on

## Alternatives Considered

- **Filter inside each parser:** Duplicates policy across parsers; harder to change consistently
- **Filter in the UI layer:** Business logic leaks into presentation; makes unit testing the filter harder

## Consequences

- Parsers must always populate `is_template` accurately for the filter to work correctly
- The orchestrator test suite must verify template rows are excluded
- Future filtering rules (e.g., powered-off VMs) should also live at orchestrator level
