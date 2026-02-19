# ADR-034: SAP Word Boundary Pattern (Exception to Substring Matching)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The general classification strategy uses substring matching (ADR-011). The string "SAP" is short and appears as a substring in unrelated words (e.g., "GISAPP", "SAPPHIRE") that are not SAP workloads.

## Decision

The SAP classification rule uses `\bSAP\b` word boundary regex plus explicit prefix patterns (`SAP-`, `SAP_`) instead of plain substring matching. This is the only rule that deviates from the general strategy.

## Rationale

- "GISAPP" (a GIS application) contains "SAP" as a substring and would be misclassified without word boundaries
- SAP systems reliably name VMs with "SAP" as a standalone token or with a delimiter prefix/suffix
- The precision trade-off is worth making for this specific keyword; other keywords are less ambiguous

## Alternatives Considered

- **Plain "SAP" substring (consistent with ADR-011):** Produces false positives on common naming patterns; misclassification is not correctable without per-VM review

## Consequences

- A VM named "SAPAPP01" (SAP followed immediately by non-delimiter text) would not match this rule; the prefix patterns `SAP-` and `SAP_` cover the common delimiter cases
- The exception must be documented so future maintainers do not "fix" the word boundary back to substring matching
