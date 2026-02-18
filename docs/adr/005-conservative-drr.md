# ADR-005: Most Conservative DRR for Multi-Workload VMs

**Status:** Accepted
**Date:** 2026-02-18

## Context

A VM can have multiple workload types (e.g., SQL Server + File Server). Each workload type has a different DRR. Which ratio should be used for sizing?

## Decision

Use the **lowest (most conservative) DRR** among all selected workload types.

## Rationale

- Pre-sales needs defensible sizing numbers
- Over-estimating data reduction leads to under-sized arrays
- Under-estimating data reduction is safe (customer gets more headroom)
- Conservative approach builds customer trust

## Consequences

- Sizing may recommend larger arrays than actually needed
- Users can override to a specific workload if they know the dominant pattern
