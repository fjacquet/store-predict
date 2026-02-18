# ADR-003: Column Alias Dictionaries, Not Fuzzy Matching

**Status:** Accepted
**Date:** 2026-02-18

## Context

FR-1.7 requires handling column name variations between RVTools and LiveOptics file formats. Column names differ slightly between versions (e.g., "Provisioned MB" vs "Provisioned MiB").

## Decision

Use alias dictionaries mapping canonical names to known variations. No fuzzy matching library.

## Rationale

- The variation set is small and well-known (finite list of RVTools/LiveOptics versions)
- A dictionary lookup is deterministic — no false matches
- Zero additional dependencies (no fuzzywuzzy, rapidfuzz)
- 10-line solution vs adding an NLP library

## Consequences

- New column name variations require adding entries to the alias dictionary
- No automatic handling of truly unknown column names
- Explicit error messages when columns are not found
