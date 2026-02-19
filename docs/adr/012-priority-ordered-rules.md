# ADR-012: Priority-Ordered Rule Registry with First-Match-Wins

**Status:** Accepted
**Date:** 2026-02-19

## Context

Multiple classification rules can match a single VM name. The system needs a deterministic, predictable resolution strategy.

## Decision

Evaluate `ClassificationRule` entries in ascending priority order. The first match wins; remaining rules are not evaluated.

## Rationale

- Deterministic: same input always produces same output
- Priority tiers encode business intent explicitly: Database (100-199) > Application (200-299) > Infrastructure (300-399) > Logging (400-499) > Boot from SAN (500-599) > OS Fallback (900-949) > Default (999)
- Specific rules at low numbers beat generic rules at high numbers

## Alternatives Considered

- **No ordering:** Ambiguous — rule set order becomes an implicit, invisible dependency
- **Weighted scoring:** Complex to tune, harder to explain to pre-sales users

## Consequences

- Adding a new rule requires choosing a priority number deliberately
- PostgreSQL/MySQL rules must precede generic SQL (priority 101-102 vs 103) — see ADR-035
- Rule list must be kept sorted by priority for readability
