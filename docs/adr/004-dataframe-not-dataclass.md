# ADR-004: DataFrame as Pipeline Data Format

**Status:** Accepted
**Date:** 2026-02-18

## Context

The pipeline processes VM data through ingestion, classification, and calculation stages. Two options: pass DataFrames or VMRecord dataclass instances.

## Decision

Use pandas DataFrame as the primary data format throughout the pipeline.

## Rationale

- DataFrames are natural for batch operations (5000+ VMs)
- Vectorized operations are faster than row-by-row dataclass conversion
- pandas integrates well with openpyxl (read) and NiceGUI AG Grid (display)
- Classification adds columns to DataFrame without schema changes

## Consequences

- VMRecord dataclass exists but is used for typed access where needed, not as pipeline currency
- Type safety is weaker than dataclass (column names are strings)
- Must maintain canonical column schema consistency across all parsers
