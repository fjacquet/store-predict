# ADR-032: Log Sanitization — Never Log DataFrame Contents

**Status:** Accepted
**Date:** 2026-02-19

## Context

StorePredict processes real customer data including VM names, IP addresses, and infrastructure topology. Application logs must not become a secondary data store for this information.

## Decision

Only metadata may be logged: row counts, detected format, timing, and error codes. VM names, OS strings, customer identifiers, and any DataFrame cell contents are never logged.

## Rationale

- Customer data in logs would require log retention, access control, and GDPR compliance work
- Metadata is sufficient for debugging (format detection failures, row counts, parse errors)
- The pattern is explicit and auditable: `logger.info("Ingested %d VMs from %s", len(df), fmt.value)`

## Alternatives Considered

- **Log full DataFrames at DEBUG level:** Convenient for development but leaks PII into log files; hard to ensure DEBUG is disabled in production

## Consequences

- Debugging customer-reported issues requires reproduction with anonymised sample data, not production logs
- New logging statements must be reviewed to ensure no DataFrame columns are interpolated
