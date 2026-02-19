# ADR-035: PostgreSQL/MySQL Rules Before Generic SQL

**Status:** Accepted
**Date:** 2026-02-19

## Context

The strings "PGSQL" and "MYSQL" both contain "SQL" as a substring. With first-match-wins ordering (ADR-012), the classification of a PostgreSQL or MySQL VM depends on which rule appears first.

## Decision

Assign PostgreSQL the priority 101 and MySQL the priority 102. The generic SQL (Microsoft SQL) rule is assigned priority 103. All other database rules follow at higher priority numbers.

## Rationale

- Without this ordering, `PGSQL001` would match the generic SQL rule and be classified as Microsoft SQL Server, which is wrong
- The principle generalises: specific patterns always receive lower priority numbers than the generic pattern they would otherwise be subsumed by

## Alternatives Considered

- **Negative lookahead in the SQL pattern:** Possible but fragile; requires updating the generic rule every time a new specific SQL variant is added

## Consequences

- The priority numbering convention (specific before generic within a tier) must be followed when adding new database rules
- This ADR documents the rationale so maintainers do not swap priority numbers when reorganising the rule list
