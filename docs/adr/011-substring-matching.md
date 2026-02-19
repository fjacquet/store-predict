# ADR-011: Substring Matching for VM Classification (not Word Boundary)

**Status:** Accepted
**Date:** 2026-02-19

## Context

VM naming in corporate environments often embeds technology keywords inside longer strings. Classification must detect these embedded keywords reliably.

## Decision

Use `re.search()` without `\b` word boundaries for pattern matching against VM names. The SAP rule is the only exception (see ADR-034).

## Rationale

- Corporate naming embeds keywords: `CADSRVSQL001` contains SQL, `CITADM` contains CIT
- Word boundaries would silently miss these legitimate matches
- False positives are manageable — users can override misclassifications in the UI

## Alternatives Considered

- **Word boundary regex (`\bSQL\b`):** Misses embedded keywords, causing silent under-classification

## Consequences

- Some ambiguous names may match multiple categories (handled by priority ordering, ADR-012)
- Users are expected to review the auto-classification results
- SAP is a named exception due to the `GISAPP` false-positive risk (ADR-034)
