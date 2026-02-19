# ADR-042: Web Servers Default to Content Included (DRR=5)

**Status:** Accepted
**Date:** 2026-02-19

## Context

The DRR reference table distinguishes two web server subcategories: "content included" (DRR=5) and "content not included" (DRR=1.5). VM naming does not reliably indicate which subcategory applies.

## Decision

VMs classified as web servers default to the "content included" subcategory (DRR=5).

## Rationale

- DRR=5 is the middle ground between best-case and worst-case for web workloads
- "Content included" (static assets, media files) is a common web server configuration in enterprise environments
- DRR=1.5 for "content not included" (pure reverse proxy, load balancer) would be pessimistic for most real-world web servers
- Users can override to DRR=1.5 for servers they know are content-free

## Alternatives Considered

- **Default to content not included (DRR=1.5):** More conservative but likely to understate the actual reduction ratio for most web servers; requires more user overrides

## Consequences

- Sizing reports may be optimistic for environments with many pure-proxy web servers that users do not override
- The review step is important for accurate results; pre-sales engineers should be trained to ask customers about web server content types
- Consistent with the project's general philosophy: show a reasonable default, require explicit user action to change to a more conservative estimate
