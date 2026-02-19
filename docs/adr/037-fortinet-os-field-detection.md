# ADR-037: FortiNet Detection via OS Field

**Status:** Accepted
**Date:** 2026-02-19

## Context

FortiNet security appliances (FortiGate, FortiAnalyzer, FortiManager) are virtualised in VMware environments. Their VM names often follow internal naming conventions that do not contain "FORTI" (e.g., "CIGES-FAZ" for a FortiAnalyzer instance).

## Decision

The FortiNet classification rule matches "FORTI" in either the VM name OR the OS field. The two conditions are evaluated with OR logic.

## Rationale

- VMware Tools reports the OS as "FortiOS" or similar for FortiNet appliances even when the VM name is opaque
- OR logic ensures that either signal alone is sufficient for a match
- Without OS field matching, many FortiNet appliances would fall through to the Unknown Reducible default

## Alternatives Considered

- **VM name patterns only:** Misses appliances with internal naming conventions; requires customers to maintain descriptive names that they may not control

## Consequences

- The classification rule requires inspecting two columns per VM instead of one
- The OR logic pattern (vm_name_patterns OR os_patterns) becomes the template for other appliance types that use similar naming conventions
