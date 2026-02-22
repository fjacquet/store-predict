# Phase 22 Research: Compute Sizing Module & Page

**Phase:** 22
**Date:** 2026-02-22
**Status:** Complete

## Problem

Pre-sales engineers need to answer "how many ESXi hosts does this customer
need?" from the same RVTools/LiveOptics export they already uploaded. The
answer must account for HA failover (N+1), optional stretch-cluster (vMSC),
and optional Active/Passive DR sizing — all with a configurable vCPU overcommit
ratio and a choice of real Dell PowerEdge server models.

## Key Findings

### All Required Columns Already in CANONICAL_COLUMNS

`num_cpus`, `memory_mib`, and `datacenter` were confirmed present in
`CANONICAL_COLUMNS` before implementation began. No parser changes were needed
for Phase 22.

### N+1 HA Formula

VMware Architecture Toolkit guidance: size `N` hosts to carry the full workload,
then add `+1` for failover.

```
hosts_n1 = ceil(total_vcpus / (host_pcores × overcommit_ratio)) + 1
hosts_n1 = max(hosts_by_vcpu, hosts_by_ram)   # binding constraint
```

Physical cores (not HT threads) are used for the denominator. RAM sizing uses
no overcommit (production workloads).

### vMSC Requires 2+ Distinct Datacenter Values

vMSC (vSphere Metro Storage Cluster) requires VMs spread across at least two
fault domains. The `datacenter` column from RVTools (vInfo tab) provides this
signal. `_vmsc_sites()` returns distinct non-empty datacenter strings; fewer
than 2 means `vmsc_available=False` and a warning card is shown.

### A/P DR — Always Computed

Active/Passive DR host counts are always computed in `ComputeSizingResult`
(`ap_primary_hosts`, `ap_secondary_hosts`). The UI controls whether to display
them via the A/P toggle. An earlier implementation gated computation behind an
`ap_enabled` parameter, but this broke tests and was reverted — the parameter
was removed entirely. The UI's toggle only affects display, not computation.

### Presets: CSV Over Hardcoded

Original design had 9 hardcoded `HostConfig` entries. Research revealed the
CPU landscape changes faster than the code release cycle:

- **Intel Xeon 6 P-core** (Granite Rapids): R770 supports up to 86c/socket
  (6786P), or 128c with 6900P AP-die chips; DDR5-6400 with 12-channel memory
- **AMD EPYC 9005 Turin**: R7725 supports up to 192c/socket (Zen5c via 9955),
  or 128c classic Zen5 (9755), or 96c (9655); XE7745 is the GPU/AI variant

Decision: move presets to `src/store_predict/data/compute_presets.csv` (17
entries in the initial file) with a `load_presets()` loader. See ADR-062.

### Pyright TypedDict Pattern

`_load_compute_config()` returned `dict[str, object]`, which caused Pyright
`reportArgumentType` errors when values were passed to `ui.number(value=...)`.
Fix: replace with `_ComputeConfig(TypedDict)` so each field has an exact type.
See ADR-063.

### R7275 Does Not Exist

User requested "R7275" as a preset. Web search confirmed this model does not
exist. The correct AMD EPYC 9005 2-socket server is the **PowerEdge R7725**
(announced November 2024). All references use R7725.

## Dell PowerEdge Preset Summary

| Model | CPU Family | Cores/Socket | Sockets | RAM GiB |
|-------|-----------|--------------|---------|---------|
| R760 | Xeon 5th Gen | 28 / 32 / 48 | 2 | 512–1024 |
| R770 | Xeon 6 P-core | 48 / 64 / 86 | 2 | 1024–2048 |
| R860 | Xeon 5th Gen | 32 / 48 | 4 | 2048–3072 |
| R960 | Xeon 5th Gen | 32 / 56 | 4 | 3072–6144 |
| R7725 | EPYC 9005 Turin | 64 / 96 / 128 / 192 | 2 | 1536–4608 |
| XE7745 | EPYC 9005 Turin | 64 / 96 | 2 | 1152–2304 |
| Custom | — | user-defined | user-defined | user-defined |
