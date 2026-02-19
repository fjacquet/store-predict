# ADR-036: Citrix VMs Default to Full Clone (DRR=8)

**Status:** Accepted
**Date:** 2026-02-19

## Context

Citrix VDI deployments use different provisioning technologies (Full Clone, Linked Clone, Instant Clone) with significantly different storage DRR values. VM names alone do not reliably indicate which technology is in use.

## Decision

VMs matching CIT, CITRIX, or MCS patterns are classified as VDI/Full Clone (DRR=8) by default.

## Rationale

- Full Clone is the most beneficial DRR for pre-sales sizing; it maximises the headline reduction ratio
- The user is expected to review and override to Linked Clone or Instant Clone if the customer's deployment uses those technologies
- DRR=8 is not the most conservative choice; see Consequences

## Alternatives Considered

- **Default to Linked Clone (DRR=2):** More conservative and defensible but undersells the technology; pre-sales engineers preferred showing best-case as a starting point with explicit user override

## Consequences

- If a user does not review Citrix VM classifications, the sizing report will show optimistic numbers
- The review step in the UI is essential for accurate results; this decision increases the importance of user review
- Training material should highlight the Citrix classification as a common override point
