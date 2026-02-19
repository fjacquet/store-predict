# ADR-013: Weighted Average DRR (not Simple Mean)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The summary report must show an overall DRR for the entire VM fleet. Two options exist: arithmetic mean of individual DRRs, or capacity-weighted harmonic mean.

## Decision

Compute overall DRR as `total_provisioned / total_required`, not as the arithmetic mean of individual VM DRRs.

## Rationale

- A 1 GiB VM and a 100 TiB VM should not contribute equally to the fleet average
- The formula matches how storage arrays actually behave across a mixed workload
- Consistent with how the required capacity total is computed row-by-row

## Alternatives Considered

- **Simple arithmetic mean:** Mathematically incorrect for capacity sizing; a single tiny VM with DRR=1 would drag down the average unfairly

## Consequences

- Headline DRR can differ significantly from the arithmetic mean in skewed fleets
- Pre-sales customers must understand the metric is a weighted result
- Calculation is deterministic and reproducible from the per-VM numbers
