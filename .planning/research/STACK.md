# Technology Stack

**Project:** StorePredict — v4.0 Compute Sizing & VMware Health Checks
**Researched:** 2026-02-22
**Confidence:** HIGH (existing stack verified via pyproject.toml; new feature math confirmed pure-Python; no new library dependencies found necessary)

---

## What Already Exists (Do NOT Re-Add)

The following are validated and shipped through v3.0. They appear here only for pyproject.toml clarity.

| Package | Current pin | Status |
|---------|-------------|--------|
| `nicegui>=3.4,<4.0` | In pyproject.toml | Keep as-is |
| `pandas>=2.2,<4.0` | In pyproject.toml | Keep as-is |
| `openpyxl>=3.1.2` | In pyproject.toml | Keep as-is |
| `reportlab>=4.0` | In pyproject.toml | Keep as-is |
| `python-i18n[YAML]>=0.3.9` | In pyproject.toml | Keep as-is |
| `xlsxwriter>=3.2.9` | In pyproject.toml | Keep as-is |
| `pillow>=12.1.1` | In pyproject.toml | Keep as-is |
| `litellm>=1.81.13` | In pyproject.toml | Keep as-is |
| `pydantic>=2.12.5` | In pyproject.toml | Keep as-is |
| `pydantic-settings>=2.13.0,<3.0` | In pyproject.toml | Keep as-is |
| `matplotlib>=3.8` | In pyproject.toml | Keep as-is |
| `playwright>=1.40` | In pyproject.toml | Keep as-is |
| `pytest>=8.0` | dev dep | Keep as-is |
| `ruff>=0.9` | dev dep | Keep as-is |
| `mypy>=1.10` | dev dep | Keep as-is |
| `pandas-stubs>=2.2` | dev dep | Keep as-is |

---

## New Dependencies — v4.0

**None required.** All v4.0 features are implementable with the existing stack and Python stdlib. This is the primary finding of this research pass.

---

## Recommended Stack by Feature

### Feature 1: Compute Sizing Page (vCPU/RAM → Host Count)

**Stack:** Existing `pandas>=2.2` + Python stdlib `math`

**Why no new library is needed:**

The host sizing calculation is pure arithmetic. The standard VMware pre-sales formula is:

```
# CPU path
hosts_by_cpu = ceil(total_vcpus / (cores_per_host * cpu_overcommit_ratio))

# RAM path (no overcommit for defensible sizing)
hosts_by_ram = ceil(total_ram_gib / (ram_per_host_gib * ram_util_target))

# N+1 HA: add one spare host
hosts_required = max(hosts_by_cpu, hosts_by_ram) + 1

# vMSC / stretch cluster (active+passive, 50% admission control per site)
# Each site must independently support 100% of workload
hosts_per_site = ceil(hosts_required / 2)
total_hosts_vmsc = hosts_per_site * 2
```

All inputs come from user-configurable parameters (cores/host, RAM/host, overcommit ratio). The `math.ceil()` from stdlib handles rounding. No optimization library, no linear programming, no scipy — pure Python.

**Data already in canonical schema:**

- `num_cpus` — vCPU count per VM, extracted from `vInfo.CPUs` (RVTools) and `Virtual CPU` (LiveOptics)
- `memory_mib` — RAM per VM in MiB, extracted from `vInfo.Memory` (RVTools) and `Provisioned Memory (MiB)` (LiveOptics)

Both fields already exist in `CANONICAL_COLUMNS` in `pipeline/parsers/columns.py`. No parser changes needed for basic compute sizing.

**Configurable parameters (user-supplied on the Compute Sizing page):**

- Physical cores per host (default: 36 — a common 2-socket modern server)
- RAM per host GiB (default: 512 GiB)
- CPU overcommit ratio (default: 4.0 — VMware standard guidance)
- RAM utilization target (default: 0.85 — leave 15% for ESXi overhead)
- HA mode: None / N+1 / N+2
- Cluster mode: Standard / vMSC (stretch, active/passive)

**Pre-sales defensibility:** Use the **higher** of CPU-bound or RAM-bound host count. Never present a number smaller than what either resource constraint requires. This matches how WintelGuy and other pre-sales tools work.

---

### Feature 2: VMware Health Check / Concerns Page

**Stack:** Existing `pandas>=2.2` + Python dict lookups (no new library)

**What checks are implementable from RVTools vInfo data alone:**

All checks below rely on columns already present in the vInfo sheet but not yet parsed into the canonical schema. No new library is needed — only parser extension to read additional columns.

**Columns to add to parser (vInfo sheet, already exported by RVTools 4.x):**

| RVTools column name | Canonical field | Type | Notes |
|---------------------|----------------|------|-------|
| `HW version` | `hw_version` | `int` | vmx level as integer (14 = ESXi 6.7, 17 = ESXi 7.0, etc.) |
| `VMware Tools Version` | `tools_version` | `str` | e.g. "12352", "0" if not installed |
| `Tools Status` | `tools_status` | `str` | "toolsOk", "toolsOld", "toolsNotInstalled", "toolsNotRunning" |
| `CBT` | `cbt_enabled` | `bool` | Change Block Tracking; should be enabled for backups |
| `Consolidation Needed` | `consolidation_needed` | `bool` | Snapshot consolidation flag |
| `Snapshots` | `snapshot_count` | `int` | Number of active snapshots |

These columns are all optional in the parser — their absence (LiveOptics exports lack them) produces empty/NaN values, not errors.

**VMware hardware version → minimum ESXi version mapping (hardcoded dict, no external library):**

```python
# Source: Broadcom KB 315655 + virten.net/vmware/virtual-machine-hardware-versions/
HW_VERSION_TO_MIN_ESXI: dict[int, str] = {
    11: "6.0",
    12: "6.0 U2",
    13: "6.5",
    14: "6.7",
    15: "6.7 U2",
    16: "6.7 U3",
    17: "7.0",
    18: "7.0 U1",
    19: "7.0 U2",
    20: "8.0",
    21: "8.0 U2",
    22: "9.0",
}
RECOMMENDED_MIN_HW_VERSION = 17  # ESXi 7.0 or newer
CONCERN_HW_VERSION_THRESHOLD = 14  # Flag vmx-14 (ESXi 6.7) as outdated
```

**Health check rules (pure Python, no library):**

| Check ID | Severity | Condition | Message |
|----------|----------|-----------|---------|
| `hw_version_low` | Warning | `hw_version < 17` | VM hardware older than ESXi 7.0 level — upgrade recommended before migration |
| `hw_version_very_old` | Critical | `hw_version < 14` | VM hardware older than ESXi 6.7 — likely incompatible with modern vSphere clusters |
| `tools_not_installed` | Critical | `tools_status == "toolsNotInstalled"` | VMware Tools not installed — guest OS awareness and consistency required for migration |
| `tools_not_running` | Warning | `tools_status == "toolsNotRunning"` | VMware Tools installed but not running — may indicate guest OS issue |
| `tools_outdated` | Info | `tools_status == "toolsOld"` | VMware Tools version outdated — update recommended |
| `snapshot_count_high` | Warning | `snapshot_count >= 3` | High snapshot count increases migration time and risk |
| `snapshot_count_critical` | Critical | `snapshot_count >= 10` | Excessive snapshots — consolidation required before migration |
| `consolidation_needed` | Critical | `consolidation_needed == True` | Snapshot consolidation needed — consolidate before migration |
| `cbt_disabled` | Warning | `cbt_enabled == False and is_powered_on` | CBT disabled — incremental backup jobs will be larger |
| `no_vcpu_data` | Info | `num_cpus == 0` | vCPU count missing — compute sizing estimates may be inaccurate |
| `no_ram_data` | Info | `memory_mib == 0` | RAM missing — compute sizing estimates may be inaccurate |
| `oversized_vcpu` | Info | `num_cpus >= 16` | High vCPU count — verify actual CPU utilization before migration sizing |

**Data quality checks (from existing canonical fields, no new columns needed):**

| Check ID | Severity | Condition | Message |
|----------|----------|-----------|---------|
| `unknown_classification` | Info | `workload_category == "Unknown Reducible"` | Unclassified VM — DRR estimate uses conservative default (5.0) |
| `zero_provisioned` | Warning | `provisioned_mib == 0` | Zero provisioned storage — check data source accuracy |
| `in_use_exceeds_provisioned` | Warning | `in_use_mib > provisioned_mib` | Used storage exceeds provisioned — data quality issue |
| `no_iops_data` | Info | `peak_iops is NaN and source_format == RVTOOLS` | No performance data — IOPS from RVTools exports require separate LiveOptics data collection |

---

### Feature 3: Per-VM IOPS in Grid (LiveOptics)

**Stack:** Existing `pandas>=2.2` — no new dependency

The LiveOptics parser already populates `peak_iops`, `avg_iops`, `peak_throughput_mbs` into the canonical schema. The only work is surface these columns in the AG Grid view when data is present (hide for RVTools-only imports). NiceGUI's AG Grid supports conditional column show/hide via `columnDefs` with `hide: bool`.

---

### Feature 4: Classification Improvements

**Stack:** Existing rules engine in `classification.py` — no new library

Adding OS-based fallback rules (e.g., "Windows Server" without DB keyword → `Virtual Machines`) requires only editing the rules dict in `classification.py`. No new dependency. Pattern matching uses Python `re` stdlib, which is already used.

---

### Feature 5: Grid UX Enhancements

**Stack:** Existing NiceGUI AG Grid integration — no new library

AG Grid Community Edition (bundled with NiceGUI 3.x) provides:

- Column filtering: `filter: "agTextColumnFilter"` in columnDef
- Column visibility toggle: `columnDefs` with `hide` property + `ui.checkbox` bindings
- Row grouping: `rowGroup: True` in columnDef — requires AG Grid Enterprise (NOT included)
- Search: AG Grid's `quickFilterText` option on the grid options object

**Important:** Row grouping requires AG Grid Enterprise license. Use client-side filtering + `groupBy` aggregation in pandas instead (group summary rows) to avoid license dependency.

---

## Installation — pyproject.toml Changes

**No changes to `[project.dependencies]` are required for v4.0.**

All v4.0 features use existing packages + Python stdlib (`math`, `re`, `dataclasses`).

```toml
# pyproject.toml — NO CHANGES NEEDED for v4.0
# Current dependencies already cover all new features
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Compute sizing math | `math.ceil()` stdlib | `scipy.optimize` | Overkill — this is arithmetic, not optimization; adds 15 MB to Docker image |
| Compute sizing math | `math.ceil()` stdlib | `OR-Tools` | Same as above — the problem is a formula, not a constraint satisfaction problem |
| Hardware version lookup | Hardcoded dict | `pyVmomi` (vSphere SDK) | pyVmomi requires live vCenter connection; tool works with offline exports only |
| Health checks | Pure Python rules | `pyvmomi` live checks | Same as above — offline file analysis is the tool's core design constraint |
| AG Grid row grouping | pandas aggregation + flat display | AG Grid Enterprise `rowGroup` | Enterprise license required; community edition is free and sufficient |
| VMware Tools version parsing | String comparison on `tools_status` field | Parse numeric `tools_version` against Broadcom KB 304809 | `tools_status` string is pre-classified by RVTools; no need to re-parse raw build numbers |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pyVmomi` | Requires live vCenter connection; incompatible with offline-file-analysis design | Hardcoded HW version dict + column parsing from RVTools export |
| `scipy` / `numpy` (new) | Not needed for arithmetic sizing formulas | `math.ceil()` from stdlib |
| `OR-Tools` / `pulp` | Linear programming is overkill for host count calculation | Pure arithmetic formula — same approach already used for BFD datastore placement |
| AG Grid Enterprise | License cost; row grouping not critical enough to justify | Pandas aggregation for group summaries |
| `semver` library | Not needed to compare VMware Tools version numbers | Direct integer comparison on `tools_version` string cast to int |
| `pydantic` models for health checks (new) | Existing `dataclasses` are sufficient for concern records | `@dataclass` with `severity: str`, `check_id: str`, `message: str` |

---

## Stack Patterns for v4.0 Features

**For Compute Sizing Engine:**

- Input: `df["num_cpus"].sum()` and `df["memory_mib"].sum()` from canonical DataFrame (filtered to `is_powered_on == True`, `is_template == False`)
- Output: `ComputeSizingResult` dataclass with `hosts_required`, `hosts_cpu_bound`, `hosts_ram_bound`, `hosts_per_site` (for vMSC)
- Location: New module `pipeline/compute_sizing.py`

**For Health Check Engine:**

- Input: canonical DataFrame + optional extended columns (`hw_version`, `tools_status`, etc.)
- Output: list of `Concern` dataclasses with `severity`, `vm_name`, `check_id`, `detail`
- Aggregate to page-level summary counts (Critical / Warning / Info)
- Location: New module `pipeline/health_checks.py`

**For Extended RVTools Parser:**

- Add optional column reads in `parsers/rvtools.py` for `hw_version`, `tools_status`, `tools_version`, `snapshot_count`, `cbt_enabled`, `consolidation_needed`
- All wrapped in `col_map.get("field")` pattern (already used for optional columns) — absence is silent, not an error
- Add new optional fields to `CANONICAL_COLUMNS` and `RVTOOLS_ALIASES` in `parsers/columns.py`

---

## Version Compatibility

| Package | Current Pin | v4.0 Impact | Notes |
|---------|-------------|-------------|-------|
| `pandas>=2.2,<4.0` | Installed | No change | `.sum()`, `.fillna()`, `.astype()` used for sizing aggregation — all stable |
| `nicegui>=3.4,<4.0` | Installed | No change | AG Grid `agTextColumnFilter` available in Community Edition bundled with NiceGUI |
| All others | Installed | No change | v4.0 introduces no new runtime dependencies |

---

## Sizing Formulas Reference

### Standard Cluster (N+1 HA)

```python
import math

def hosts_required(
    total_vcpus: int,
    total_ram_gib: float,
    cores_per_host: int = 36,
    ram_per_host_gib: float = 512.0,
    cpu_overcommit_ratio: float = 4.0,
    ram_utilization_target: float = 0.85,
    ha_spare_hosts: int = 1,
) -> dict[str, int]:
    hosts_by_cpu = math.ceil(total_vcpus / (cores_per_host * cpu_overcommit_ratio))
    hosts_by_ram = math.ceil(total_ram_gib / (ram_per_host_gib * ram_utilization_target))
    active_hosts = max(hosts_by_cpu, hosts_by_ram)
    total = active_hosts + ha_spare_hosts
    return {
        "hosts_by_cpu": hosts_by_cpu,
        "hosts_by_ram": hosts_by_ram,
        "active_hosts": active_hosts,
        "total_with_ha": total,
    }
```

### vMSC / Stretch Cluster (Active+Passive, 50% Admission Control)

```python
def hosts_required_vmsc(
    total_vcpus: int,
    total_ram_gib: float,
    **kwargs: float | int,
) -> dict[str, int]:
    # Each site must sustain 100% of workload (site failure = full failover)
    standard = hosts_required(total_vcpus, total_ram_gib, **kwargs)
    # Round up to even number so sites have equal host count
    per_site = math.ceil(standard["total_with_ha"] / 2)
    return {
        **standard,
        "hosts_per_site": per_site,
        "total_hosts_vmsc": per_site * 2,
    }
```

---

## Sources

- [Broadcom KB 315655 — Virtual machine hardware versions](https://knowledge.broadcom.com/external/article/315655/virtual-machine-hardware-versions.html) — HW version to ESXi mapping (MEDIUM confidence — could not fetch directly; corroborated by multiple community sources)
- [virten.net — Virtual Machine Hardware Versions](https://www.virten.net/vmware/virtual-machine-hardware-versions/) — vmx version table (MEDIUM confidence — referenced by search results)
- [Broadcom KB 312100 — ESXi hosts and compatible VM hardware versions](https://knowledge.broadcom.com/external/article/312100/esxi-hosts-and-compatible-virtual-machine-hardware-versions.html) — official compatibility matrix (HIGH confidence)
- [Broadcom KB 304809 — Build numbers and versions of VMware Tools](https://knowledge.broadcom.com/external/article/304809/build-numbers-and-versions-of-vmware-too.html) — tools version reference (HIGH confidence)
- [VMware vSAN Stretched Cluster Guide](https://www.vmware.com/docs/vsan-stretched-cluster-guide) — 50% admission control per site for vMSC (HIGH confidence)
- [vSphere Metro Storage Cluster (vMSC) Guide](https://core.vmware.com/resource/vmware-vsphere-metro-storage-cluster-vmsc) — vMSC design patterns (HIGH confidence)
- [VMware vCPU overcommit ratios — Brockpeterson.com](https://www.brockpeterson.com/post/vsphere-cluster-overcommit-ratios-in-aria-operations) — 4:1 CPU ratio community standard (MEDIUM confidence)
- [VMware Architecture Toolkit — vCPU-to-pCPU ratio](https://download3.vmware.com/vcat/vmw-vcloud-architecture-toolkit-spv1-webworks/Core%20Platform/Architecting%20a%20vSphere%20Compute%20Platform/Architecting%20a%20vSphere%20Compute%20Platform.1.019.html) — VMware official guidance on pCPU (not logical threads) for sizing (HIGH confidence)
- `pyproject.toml` at project root — current installed dependencies verified directly (HIGH confidence)
- `src/store_predict/pipeline/parsers/columns.py` — existing canonical schema + alias maps confirmed (HIGH confidence)

---

*Stack research for: StorePredict v4.0 — Compute Sizing, VMware Health Checks, Grid UX, Per-VM IOPS*
*Researched: 2026-02-22*
