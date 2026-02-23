# ADR-065: Windows Desktop OS fallback → VDI Linked Clone

**Date:** 2026-02-23
**Status:** Accepted

## Context

Analysis of a real 1,483-VM LiveOptics export showed that 92 % of VMs (1,366)
fell through to the `os_fallback` confidence bucket, meaning no VM name pattern
matched and only the OS field was used. Of those, ~904 VMs had a Windows 10,
Windows 11, or Windows 7 guest OS.

The previous rule (priority 905) classified all Windows Desktop OS VMs as
`Virtual Machines / VMware / Hyper-V / KVM - No Database, File nor Email`
with a DRR of 5. While defensible, this misrepresents the actual workload:
desktop OS VMs in a datacenter are overwhelmingly VDI endpoints (Citrix PVS,
VMware Horizon linked clones, Citrix MCS).

## Decision

Change the "Windows Desktop (OS fallback)" rule (priority 905) to classify as:

- **Category:** `VDI`
- **Subcategory:** `Linked Clone / PVS (Citrix)` (DRR = 4)

The OS pattern (`windows 10|windows 11|windows 7`) is unchanged.

Additionally, add a new "VDI Generic" rule (priority 224, name-based) covering
explicit VDI infrastructure keywords: `VDI`, `DESKTOP`, `RDS`, `UAG`,
`LOGINVSI`, `LOGINENTERPRISE`.

## Rationale

- In enterprise VMware environments, Windows 10/11 VMs running in a datacenter
  are almost exclusively VDI linked clones or MCS clones. Physical desktops are
  not inventoried in RVTools or LiveOptics.
- VDI Linked Clone (DRR=4) is a conservative estimate; Full Clone (DRR=8) and
  Instant Clone (DRR=6) are higher. Using the lower value maintains the
  pre-sales defensibility principle (ADR-005).
- This change improves the classification rate from ~8 % rule_match to ~75 %
  on the reference file, making the report far more actionable.

## Consequences

- **Positive:** ~900 Windows Desktop VMs now get a more accurate workload
  category and DRR in typical enterprise files.
- **Positive:** Engineers reviewing VDI-heavy environments see a realistic
  capacity estimate, not a generic "Virtual Machines" bucket.
- **Negative:** Any genuine Windows 10/11 server-role VM (edge case) will be
  mis-classified as VDI; engineers can correct via the review grid.
- **Pattern:** OS-fallback rules should reflect the most probable datacenter
  usage of that OS, not the broadest possible category.
