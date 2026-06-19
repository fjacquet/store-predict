# ADR-088: RVTools capacity computed from the guest-level view (FTT-free, mount-aware)

**Status:** Accepted
**Date:** 2026-05-26
**Milestone:** main — vSAN sizing fidelity

## Context

StorePredict sizes PowerStore via `Required Capacity = Provisioned / DRR`, taking
`provisioned_mib` (and the displayed `in_use_mib`) directly from RVTools
`vInfo.Provisioned MiB` / `vInfo.In Use MiB`. Those are vCenter **datastore-level**
figures. On **vSAN** they are wrong in two opposite ways:

1. **FTT/mirror inflation.** vSAN reports provisioned/used including the resilience
   overhead (≈2× for FTT=1 RAID-1, 1.33× RAID-5, 1.5× RAID-6). PowerStore applies its
   own data protection, so carrying the source mirror into the target over-sizes it.
2. **Missing guest-mounted volumes.** Container/Kubernetes persistent volumes (vSAN
   CNS/FCD) and other in-guest mounts are not VMDKs, so they do not appear in the VM's
   `vInfo`/`vDisk` footprint — under-sizing those VMs.

Evidence from a real export (`ClusterVS2`, 803 VMs, vSAN FTT=1; the source behind a Dell
Live Optics "VS2" deck):

| Basis | Total | Note |
|---|---|---|
| `vInfo.Provisioned` (previous behaviour) | 950 TiB | FTT-inflated; per-VM wrong both ways |
| `Total disk capacity` (VMDK logical only) | 346 TiB | misses guest-mounted PVs |
| **`max(vPartition Capacity, VMDK logical)`** | **974 TiB** | FTT-free **and** mount-aware |
| `vPartition Consumed` (guest used) | 526 TiB | new `in_use` |
| Live Optics deck | 967 / 528 | — |

Per VM the previous basis was wrong in both directions and only *coincidentally* netted
out (`fs-p62`: 74.5 TiB vs. true 28.7; `worker20`: 0.49 TiB vs. true 38). RVTools exports
**no** FTT/storage-policy column in any version, so the inflation factor cannot be
derived — but the FTT-free guest figures are available directly. LiveOptics already
reports the guest-level (front-end) view, which is why it needed no correction.

## Decision

Recompute RVTools `provisioned_mib` / `in_use_mib` from the guest-level view, per VM, in
`_apply_guest_capacity_basis()` (in `parsers/rvtools.py`), mirroring the existing
LiveOptics multi-sheet pattern:

```
vmdk_logical = vInfo "Total disk capacity MiB"  (newer)  else  Σ vDisk "Capacity MiB"
provisioned_mib = max(Σ vPartition.Capacity, vmdk_logical)   # both FTT-free
in_use_mib      = Σ vPartition.Consumed  (when guest data exists, capped at provisioned)
```

`max(guest capacity, VMDK logical)` captures mounted PVs (guest view) while still covering
raw/unformatted disks the guest filesystem misses (VMDK logical). When a VM has neither
guest data nor disk capacity, it falls back to the raw `vInfo` value. Joins prefer
`VM UUID`, falling back to `VM` name. The recompute is uniform for all RVTools VMs (no vSAN
branching): it de-inflates vSAN VMs, captures container mounts, and leaves traditional /
non-vSAN VMs essentially unchanged (`samples/rvtools.xlsx`: 4.07 → 3.94 TiB).

This basis reproduces the Live Optics deck within **0.8%** (provisioned) and **0.3%**
(in_use) on `ClusterVS2`, and is correct per-VM.

## Consequences

**Positive:**
- Defensible, per-VM-correct sizing on vSAN — no FTT over-sizing, no container under-sizing.
- Consistent with how LiveOptics (and the Dell Live Optics deck) report capacity.
- Deterministic; no guessed FTT divisor. Validated against a real customer deck.
- An upload-time `info` notification (i18n key `upload.vsan_capacity_basis`) surfaces the
  adjusted vs. raw totals, vSAN VM count, and fallback count; an INFO log records the same.

**Negative / caveats:**
- `vPartition` (guest filesystem) can include externally-mounted NFS/iSCSI volumes that may
  not migrate to PowerStore → slight over-count. This is the same front-end basis Live Optics
  uses, so it stays consistent with the deck and is acceptable for pre-sales.
- VMs without VMware Tools / guest data (≈2/803 here, 9/999 in a mixed export) fall back to
  the raw `vInfo` value, which on vSAN is still FTT-inflated — surfaced via the fallback count.

**Neutral / out of scope:**
- The customer-facing PDF/Excel report runs on the session-reconstructed DataFrame (where the
  `df.attrs` diagnostic is no longer present), so a data-driven report footnote is deferred to
  a follow-up that threads `RvtoolsCapacityInfo` through session state.
- No FTT/RAID divisor input or storage-policy parsing (not in the export; unnecessary here).
- No LiveOptics changes (already guest-level).
