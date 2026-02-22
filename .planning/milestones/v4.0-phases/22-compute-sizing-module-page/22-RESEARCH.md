# Phase 22: Compute Sizing Module & Page - Research

**Researched:** 2026-02-22
**Domain:** ESXi compute sizing arithmetic, NiceGUI reactive UI, pure pipeline module pattern
**Confidence:** HIGH

## Summary

Phase 22 adds the `/compute` page to StorePredict. The page derives total active vCPU and RAM from the
already-parsed `num_cpus` and `memory_mib` canonical columns, then recommends ESXi host counts using
standard N+1 HA formula, with optional vMSC (stretch cluster) and Active/Passive DR modes and Dell
PowerEdge hardware presets.

No new dependencies are required. All compute data (`num_cpus`, `memory_mib`, `datacenter`,
`is_powered_on`, `is_template`) is already in `CANONICAL_COLUMNS`, populated by both RVTools and
LiveOptics parsers. The math is pure Python stdlib (`math.ceil`). The module follows the
`layout_engine.py` frozen-dataclass pattern exactly. The page follows the `concerns.py` pattern for
structure and `layout_page.py` for reactive session-backed inputs.

**Primary recommendation:** Implement `compute_sizing.py` as a pure pipeline module with a frozen
`HostConfig` + `ComputeSizingResult` dataclass pair, and `compute.py` as a NiceGUI page with
session-backed reactive inputs — exactly mirroring the `health_checks.py` + `concerns.py` precedent
established in Phase 21.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | User sees total active vCPU and RAM aggregates on /compute, with powered-off VMs and templates excluded and their count displayed | `num_cpus` and `memory_mib` confirmed in CANONICAL_COLUMNS; `is_powered_on` and `is_template` columns present; filter then aggregate |
| COMP-02 | User sees recommended ESXi host count for N+1 HA with a configurable vCPU overcommit ratio they can adjust | `ceil(total_vcpus / (host_vcpus * ratio)) + 1` formula; `ui.number` for overcommit input |
| COMP-03 | User can toggle vMSC (stretch cluster) mode and sees per-site host counts, or a clear warning when no datacenter column data is available | Split DataFrame on `datacenter` column; guard with distinct-values check; warn when < 2 distinct datacenters |
| COMP-04 | User can toggle Active/Passive DR mode and sees separate primary and secondary site host counts | Primary = all active VMs; secondary = 50% of primary host count (passive standby) |
| COMP-05 | User can select a Dell PowerEdge preset (R760/R860/R960) or enter custom host specs and sees host count update reactively | `ui.select` for preset; `ui.number` for custom cores/sockets/RAM; session-backed reactive update |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `math` | stdlib | `ceil()` for host count rounding | Pure stdlib, no dependency |
| `dataclasses` | stdlib | Frozen `HostConfig`, `ComputeSizingResult` | Consistent with `LayoutProposal`, `HealthFinding` pattern |
| `pandas` | 2.2 (installed) | DataFrame filtering (`is_powered_on`, `is_template`) and aggregation (`sum`) | Already the project's data layer |
| `nicegui` | 3.x (installed) | `ui.page`, `ui.number`, `ui.select`, `ui.switch`, `ui.card`, `ui.column` | Project UI framework |
| `python-i18n` | installed | `t()` for all user-visible strings | Mandatory — FR primary locale |

### No New Dependencies

No additions to `pyproject.toml` are required. All libraries are already installed.

**Installation:** None needed.

---

## Column Availability

### Confirmed Available in CANONICAL_COLUMNS

| Column | Type | RVTools | LiveOptics | Notes |
|--------|------|---------|------------|-------|
| `num_cpus` | int | Yes — aliases: `CPUs`, `Num CPUs`, `vCPUs` | Yes — aliases: `Virtual CPU`, `vCPU`, `CPUs` | Fills to 0 if missing |
| `memory_mib` | float | Yes — aliases: `Memory`, `Memory MB`, `Memory MiB` | Yes — aliases: `Provisioned Memory (MiB)`, `Memory (MiB)`, `Memory MB` | Fills to 0.0 if missing |
| `datacenter` | str | Yes — alias: `Datacenter` | Yes — alias: `Datacenter` | Fills to `""` if column absent |
| `is_powered_on` | bool | Yes — derived from `Powerstate` | Yes — derived from `Power State` | Defaults to `True` if absent |
| `is_template` | bool | Yes — alias: `Template` | Yes — alias: `Template` | Defaults to `False` if absent |

**Confidence:** HIGH — verified directly in `columns.py`, `rvtools.py`, and `liveoptics.py`.

### Important Notes on `memory_mib` Units

RVTools exports the `Memory` column in MB (not MiB). The parser alias maps `"Memory MB"` and `"Memory MiB"` to the same canonical column. In practice RVTools uses MB — the value is numerically identical for VM sizing purposes (the difference is ~4.8% which is within pre-sales tolerance). Do NOT convert; use the value as-is.

### `datacenter` Column Availability

The `datacenter` column is optional in both parsers. When the RVTools export does not include a
`Datacenter` column, the parser fills the entire column with `""`. The vMSC mode toggle must check
that `datacenter` has at least 2 distinct non-empty values before computing per-site results; otherwise
it must display a warning card.

---

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/
├── pipeline/
│   └── compute_sizing.py        # NEW — pure pipeline module (no UI imports)
└── ui/
    └── pages/
        └── compute.py           # NEW — /compute page
```

### Pattern: Pure Pipeline Module (follows layout_engine.py / health_checks.py)

**What:** Frozen dataclass result + pure function entry point. Zero UI imports.

**When to use:** Any new computation added to the pipeline layer.

```python
# Source: src/store_predict/pipeline/layout_models.py and health_checks.py pattern

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "HostConfig",
    "ComputeSizingResult",
    "compute_sizing",
    "DELL_POWEREDGE_PRESETS",
]

@dataclass(frozen=True)
class HostConfig:
    """Physical host specification for ESXi sizing."""
    name: str           # Display label, e.g. "R760 (2x32c)"
    cores_per_socket: int
    sockets: int
    ram_gib: int        # Total host RAM in GiB

    @property
    def total_cores(self) -> int:
        return self.cores_per_socket * self.sockets

@dataclass(frozen=True)
class ComputeSizingResult:
    """Output of compute_sizing() — all host counts for a single host config."""
    host_config: HostConfig
    overcommit_ratio: float
    total_active_vcpus: int
    total_active_ram_gib: float
    excluded_vm_count: int          # powered-off + templates
    # N+1 HA (standard)
    hosts_n1: int
    # vMSC per-site host count (None if datacenter data unavailable)
    hosts_vmsc_per_site: int | None
    vmsc_sites: list[str]           # distinct datacenter values used
    vmsc_warning: str               # "" or i18n key explaining why vMSC unavailable
    # Active/Passive DR
    hosts_ap_primary: int
    hosts_ap_secondary: int         # ceil(primary / 2) — 50% passive standby
```

### Dell PowerEdge Presets (verified against Dell datasheets, MEDIUM confidence)

```python
# Source: Dell PowerEdge 16G technical guides + spec sheets (see Sources section)
# Cores listed are physical cores per socket (not threads/HT).
# RAM values are typical mid-range configs; actual customer configs vary.

DELL_POWEREDGE_PRESETS: list[HostConfig] = [
    # Intel Xeon Scalable (5th Gen) — 2-socket
    HostConfig(name="R760 (2x28c / 512 GiB)",   cores_per_socket=28, sockets=2, ram_gib=512),
    HostConfig(name="R760 (2x32c / 512 GiB)",   cores_per_socket=32, sockets=2, ram_gib=512),
    # Intel Xeon 6 P-core (6th Gen) — 2-socket
    HostConfig(name="R770 (2x48c / 1024 GiB)",  cores_per_socket=48, sockets=2, ram_gib=1024),
    HostConfig(name="R770 (2x64c / 1536 GiB)",  cores_per_socket=64, sockets=2, ram_gib=1536),
    # Intel Xeon Scalable — 4-socket
    HostConfig(name="R860 (4x32c / 1024 GiB)",  cores_per_socket=32, sockets=4, ram_gib=1024),
    HostConfig(name="R960 (4x32c / 1536 GiB)",  cores_per_socket=32, sockets=4, ram_gib=1536),
    # AMD EPYC 9005 (Genoa-X / 2-socket)
    HostConfig(name="R7725 (2x96c / 1536 GiB)", cores_per_socket=96, sockets=2, ram_gib=1536),
    # AMD EPYC 9005 AI/GPU server (XE7745 — also usable as dense vSphere host)
    HostConfig(name="XE7745 (2x64c / 1152 GiB)", cores_per_socket=64, sockets=2, ram_gib=1152),
    HostConfig(name="Custom",                    cores_per_socket=28, sockets=2, ram_gib=512),
]

# NOTE on R7275 vs R7725: "R7275" is not a Dell product. The AMD EPYC 9005 2-socket
# server is the PowerEdge R7725 (announced Nov 2024, up to 192 cores/socket, 6TB RAM).
```

**Hardware specs summary (MEDIUM confidence — from Dell spec sheets and reseller listings):**

| Model | Sockets | Max Cores/Socket | Max RAM | CPU Arch | Notes |
|-------|---------|-----------------|---------|----------|-------|
| R760  | 2 | 56 (5th Gen Xeon) / 64 (6th Gen) | 8 TB  | Intel Xeon Scalable | 2U general-purpose |
| R770  | 2 | 86 P-core / 144 E-core (Xeon 6) | 8 TB  | Intel Xeon 6 | 2U, new 2025 platform |
| R860  | 4 | 60 (5th Gen) | 16 TB | Intel Xeon Scalable | 2U four-socket scale-up |
| R960  | 4 | 60 (5th Gen) | 16 TB | Intel Xeon Scalable | 4U scale-up for large DBs |
| R7725 | 2 | 192 (EPYC 9005) | 6 TB  | AMD EPYC | 2U, launched Nov 2024; user mistakenly called "R7275" |
| XE7745| 2 | 192 (EPYC 9005) | 3 TB  | AMD EPYC | 4U AI/GPU server; also used as dense vSphere host |

Typical pre-sales configs use 28–96 physical cores per socket. The tool offers presets for common
configs; user can enter custom specs for any configuration not listed. **R770** uses Intel Xeon 6
P-core for traditional virtualization workloads. **XE7745** is primarily an AI/GPU server but is
included as a preset because some customers use it for dense VM hosting.

### Compute Sizing Formula

**N+1 HA (standard, all use cases):**

```python
# Source: VMware Architecture Toolkit — vCPU-to-pCPU ratio guidance
# Broadcom TechDocs VCF — Sizing Compute Resources for ESXi

import math

def _hosts_n1(total_vcpus: int, host_pcores: int, overcommit_ratio: float) -> int:
    """ESXi host count for N+1 HA.

    N hosts carry the workload; +1 host for HA failover.
    Uses physical cores (not HT threads) per VMware sizing guidance.
    """
    if total_vcpus <= 0 or host_pcores <= 0 or overcommit_ratio <= 0:
        return 0
    capacity_per_host = host_pcores * overcommit_ratio
    n_hosts = math.ceil(total_vcpus / capacity_per_host)
    return n_hosts + 1  # +1 for HA
```

**vMSC per-site count:**

```python
def _hosts_vmsc_per_site(total_vcpus: int, host_pcores: int, overcommit_ratio: float) -> int:
    """Each vMSC site must sustain the full workload (50% admission control per site).

    So each site needs enough hosts for ALL VMs (not half), plus N+1.
    Result is the same as standard N+1 per site — the constraint is
    that EACH site must independently handle 100% of VMs.
    """
    return _hosts_n1(total_vcpus, host_pcores, overcommit_ratio)
```

**Active/Passive DR:**

```python
def _hosts_ap_secondary(primary_hosts: int) -> int:
    """Secondary (passive) site hosts = 50% of primary, minimum 1."""
    return max(1, math.ceil(primary_hosts / 2))
```

**RAM guard (secondary sizing check):**

```python
def _hosts_by_ram(total_ram_gib: float, host_ram_gib: int) -> int:
    """Hosts needed to hold total VM RAM (no overcommit for RAM)."""
    if total_ram_gib <= 0 or host_ram_gib <= 0:
        return 0
    return math.ceil(total_ram_gib / host_ram_gib) + 1  # +1 for HA
```

The final host count is `max(hosts_by_vcpu, hosts_by_ram)` — whichever dimension is the binding
constraint. This is standard pre-sales practice: do both checks, show whichever drives the count.

### vMSC (Stretch Cluster) Logic

**Datacenter validation:**

```python
def _vmsc_sites(df: pd.DataFrame) -> list[str]:
    """Return list of distinct non-empty datacenter values."""
    if "datacenter" not in df.columns:
        return []
    return [v for v in df["datacenter"].dropna().unique() if str(v).strip()]

def _vmsc_available(sites: list[str]) -> bool:
    return len(sites) >= 2
```

**Per-site sizing:** When `datacenter` has 2+ distinct values, split the filtered DataFrame by
datacenter. Each site's host count = `_hosts_n1(site_vcpus, host_pcores, ratio)`. Display a table
with one row per site.

**Warning condition:** If `len(sites) < 2`, show an info card with i18n key
`compute.vmsc_no_dc_data`. Do not hide the toggle; show a disabled-looking result panel explaining
the data limitation.

### Active/Passive DR Logic

Primary site = all active VMs (same as standard N+1 result).
Secondary site = `ceil(primary_hosts / 2)` hosts — the passive standby is sized at 50% capacity.

Display as two columns: "Primary Site" and "Secondary Site (passive)".

### Page Reactivity Pattern (from layout_page.py)

Session-backed inputs, re-render on change. No "Calculate" button — all inputs are reactive.

```python
# Pattern: session-backed reactive input
# Source: src/store_predict/ui/pages/layout_page.py lines 26-44

def _load_compute_config() -> dict[str, object]:
    """Read compute config from tab session, using defaults."""
    return {
        "preset_name": app.storage.tab.get("compute_preset", "R760 (2x28c / 512 GiB)"),
        "overcommit_ratio": float(app.storage.tab.get("compute_overcommit", 4.0)),
        "vmsc_enabled": bool(app.storage.tab.get("compute_vmsc", False)),
        "ap_enabled": bool(app.storage.tab.get("compute_ap", False)),
        "custom_cores_per_socket": int(app.storage.tab.get("compute_custom_cps", 28)),
        "custom_sockets": int(app.storage.tab.get("compute_custom_sockets", 2)),
        "custom_ram_gib": int(app.storage.tab.get("compute_custom_ram", 512)),
    }
```

NiceGUI reactivity: use `ui.refreshable` to wrap the results panel. Call
`results_panel.refresh()` from each input's `on_change` callback after saving to session.

```python
@ui.refreshable
def _results_panel(df: pd.DataFrame, config: dict) -> None:
    result = compute_sizing(df, ...)
    # render result cards
```

### Anti-Patterns to Avoid

- **Re-running ingestion pipeline in compute page:** Always start with `load_session_data()` — never re-read files.
- **Using `CalculationSummary.total_cpus` for compute:** `CalculationSummary` aggregates ALL VMs (including powered-off). Always aggregate from the DataFrame directly with the powered-off/template filter applied.
- **Using HT threads for vCPU sizing:** VMware official guidance says to use physical cores (pCPU) as the sizing unit. HT logical threads are NOT equivalent to pCPUs for VM density sizing.
- **Storing `ComputeSizingResult` in session:** Compute results are derived on-demand from session data each page visit. Never cache derived results in `app.storage.tab` — only store user configuration inputs (overcommit ratio, preset choice, toggles).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ceiling division | Custom rounding | `math.ceil()` | stdlib, correct for all positive values |
| Immutable result containers | Mutable dicts | `@dataclass(frozen=True)` | Consistent with all existing pipeline models |
| Session storage | Custom session class | `app.storage.tab` get/set | NiceGUI built-in, already used everywhere |
| Reactive UI refresh | Manual DOM manipulation | `@ui.refreshable` decorator | NiceGUI pattern; avoids re-routing |

---

## Common Pitfalls

### Pitfall 1: Division by Zero in Host Count Formula

**What goes wrong:** If `total_vcpus == 0` (all VMs powered off, or no CPU data), `math.ceil(0 / N) = 0` — returns 0, which is mathematically correct but confusing in the UI.
**Why it happens:** User uploads a file with only powered-off VMs, or LiveOptics export has no CPU column.
**How to avoid:** Guard `compute_sizing()` for `total_active_vcpus == 0` and return a result with `hosts_n1 = 0` plus a flag `no_compute_data: bool = True`. The page renders a warning card instead of a host count table.
**Warning signs:** Zero aggregates with a non-zero VM count in the input.

### Pitfall 2: Overcommit Ratio Bounds

**What goes wrong:** User enters `0` or a very large value for the overcommit ratio — division by zero or nonsensically small host count.
**Why it happens:** `ui.number` has no server-side validation by default.
**How to avoid:** Clamp overcommit ratio to `[1.0, 10.0]` in `compute_sizing()`. Use `ui.number(min=1.0, max=10.0, step=0.5)` in the UI. Default is `4.0` (industry standard for mixed workloads).

### Pitfall 3: CalculationSummary Includes Powered-Off VMs

**What goes wrong:** `CalculationSummary.total_cpus` aggregates ALL VMs including powered-off and templates. If the page uses this value, it over-sizes host count.
**Why it happens:** `calculate()` was designed for storage sizing where all provisioned capacity matters.
**How to avoid:** In `compute_sizing()`, always receive the raw DataFrame and apply the filter:

```python
active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]
```

Compute aggregates from `active`, not from the full DataFrame. Report `excluded_vm_count = len(df) - len(active)`.

### Pitfall 4: memory_mib Session Round-Trip as Float

**What goes wrong:** After `load_session_data()` → `pd.DataFrame(records)`, the `memory_mib` column may come back as `object` dtype containing `None` values (from NaN serialization). Summing it directly raises TypeError.
**Why it happens:** `save_session_data()` converts `float('nan')` to `None` for JSON compatibility.
**How to avoid:** Always coerce when reading from session:

```python
total_ram_mib = pd.to_numeric(active["memory_mib"], errors="coerce").fillna(0.0).sum()
total_ram_gib = total_ram_mib / 1024.0
```

### Pitfall 5: vMSC with Single-Site Datacenter Column

**What goes wrong:** Customer has a `Datacenter` column with all VMs in the same datacenter. The vMSC toggle shows a result table but both "sites" are the same.
**Why it happens:** RVTools exports often have a `Datacenter` column even for single-site environments.
**How to avoid:** Check `len(distinct_non_empty_datacenters) >= 2` before computing per-site results. If only one datacenter, render the info warning regardless of toggle state.

### Pitfall 6: HT Threads vs Physical Cores

**What goes wrong:** Using the advertised "thread count" (hyperthreading) instead of physical core count inflates the effective pCPU pool by ~2x, causing under-sizing by the same factor.
**Why it happens:** Server specs often prominently list thread count. Dell R760 with 2x32c = 64 cores / 128 threads.
**How to avoid:** Preset `cores_per_socket` values represent PHYSICAL cores only. Document this in preset labels and tooltip. Default overcommit ratio of 4:1 already accounts for conservative physical core sizing.

### Pitfall 7: i18n Key Parity Gap

**What goes wrong:** French keys are missing for new compute section, causing `python-i18n` to silently return the raw key string as the UI label.
**Why it happens:** Adding keys to `en.yaml` and forgetting `fr.yaml` is easy.
**How to avoid:** The existing project has a test for i18n key parity. Add all `compute.*` and `tooltip.compute_*` keys to BOTH files in the same commit.

---

## Code Examples

### Full compute_sizing() signature

```python
# Source: pattern from src/store_predict/pipeline/health_checks.py

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

def compute_sizing(
    df: pd.DataFrame | None,
    host_config: HostConfig,
    overcommit_ratio: float = 4.0,
    vmsc_enabled: bool = False,
    ap_enabled: bool = False,
) -> ComputeSizingResult:
    """Compute ESXi host counts from session DataFrame.

    Filters to active non-template VMs before aggregating.
    Returns ComputeSizingResult with zero counts and no_compute_data=True
    if df is None/empty or all VMs are excluded.
    """
    if df is None or df.empty:
        return _empty_result(host_config, overcommit_ratio)

    # Filter to active, non-template VMs
    active = df[
        (df.get("is_powered_on", pd.Series([True] * len(df))) == True)
        & (df.get("is_template", pd.Series([False] * len(df))) == False)
    ]
    excluded_count = len(df) - len(active)

    total_vcpus = int(pd.to_numeric(active["num_cpus"], errors="coerce").fillna(0).sum())
    total_ram_mib = float(pd.to_numeric(active["memory_mib"], errors="coerce").fillna(0).sum())
    total_ram_gib = total_ram_mib / 1024.0

    # Clamp overcommit
    ratio = max(1.0, min(10.0, overcommit_ratio))
    host_pcores = host_config.total_cores

    hosts_by_vcpu = _hosts_n1(total_vcpus, host_pcores, ratio)
    hosts_by_ram  = _hosts_by_ram(total_ram_gib, host_config.ram_gib)
    hosts_n1      = max(hosts_by_vcpu, hosts_by_ram)

    # vMSC
    sites = _vmsc_sites(active)
    vmsc_warning = "" if _vmsc_available(sites) else "compute.vmsc_no_dc_data"
    hosts_vmsc_per_site = None
    if vmsc_enabled and _vmsc_available(sites):
        # Per site: each site must run all VMs
        hosts_vmsc_per_site = _hosts_n1(total_vcpus, host_pcores, ratio)

    # Active/Passive DR
    hosts_ap_primary   = hosts_n1
    hosts_ap_secondary = _hosts_ap_secondary(hosts_ap_primary)

    return ComputeSizingResult(
        host_config=host_config,
        overcommit_ratio=ratio,
        total_active_vcpus=total_vcpus,
        total_active_ram_gib=total_ram_gib,
        excluded_vm_count=excluded_count,
        hosts_n1=hosts_n1,
        hosts_vmsc_per_site=hosts_vmsc_per_site,
        vmsc_sites=sites,
        vmsc_warning=vmsc_warning,
        hosts_ap_primary=hosts_ap_primary,
        hosts_ap_secondary=hosts_ap_secondary,
    )
```

### Page structure (follows concerns.py pattern)

```python
# Source: src/store_predict/ui/pages/concerns.py

from nicegui import app, ui
from store_predict.i18n import t
from store_predict.pipeline.compute_sizing import (
    DELL_POWEREDGE_PRESETS, HostConfig, compute_sizing
)
from store_predict.ui.layout import layout
from store_predict.ui.state import load_session_data

@ui.page("/compute")
async def compute_page() -> None:
    await ui.context.client.connected()
    df = load_session_data()

    if df is None or df.empty:
        with layout("StorePredict - " + t("compute.title")), \
             ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"), \
             ui.card().classes("p-8 gap-4 items-center text-center"):
            ui.icon("memory", size="3rem").classes("text-gray-400")
            ui.label(t("compute.no_data")).classes("text-xl text-gray-500")
            ui.button(t("report.go_to_upload"),
                      on_click=lambda: ui.navigate.to("/upload"),
                      icon="arrow_forward").classes("bg-blue-700 text-white")
        return

    # ... settings panel + refreshable results panel
```

---

## i18n Key Structure

Add the following keys to BOTH `en.yaml` and `fr.yaml`. All keys under the `compute:` namespace.

### en.yaml additions

```yaml
layout:
  # Add to existing layout nav section:
  compute: Compute Sizing

compute:
  title: "Compute Sizing"
  no_data: "No data uploaded yet. Upload a file to see compute sizing recommendations."
  active_vcpus: "Active vCPUs"
  active_ram: "Active RAM (GiB)"
  excluded_vms: "%{count} powered-off or template VM(s) excluded"
  host_preset: "Host Configuration"
  custom_preset: "Custom"
  cores_per_socket: "Cores / Socket"
  sockets: "Sockets"
  ram_gib: "RAM (GiB)"
  overcommit_ratio: "vCPU Overcommit Ratio"
  overcommit_hint: "vCPUs per physical core. 4:1 is standard for mixed workloads."
  results_heading: "Host Count Recommendations"
  ha_mode: "HA Mode"
  hosts_n1: "N+1 HA"
  hosts_n1_detail: "Standard: N hosts + 1 for failover"
  vmsc_toggle: "vMSC Stretch Cluster"
  vmsc_site_heading: "Hosts per Site (vMSC)"
  vmsc_no_dc_data: "Datacenter column is empty or has only one distinct value — cannot compute per-site counts. Export must include a Datacenter column with at least 2 distinct values."
  ap_toggle: "Active/Passive DR"
  ap_primary: "Primary Site"
  ap_secondary: "Secondary Site (passive)"
  ap_secondary_detail: "50% of primary — passive standby"
  binding_constraint: "Binding constraint"
  constraint_vcpu: "vCPU"
  constraint_ram: "RAM"

tooltip:
  # Add to existing tooltip section:
  compute_preset: "Select a Dell PowerEdge server model or enter custom specs"
  compute_overcommit: "Number of vCPUs per physical core. Higher = more VMs per host but more contention."
  compute_vmsc: "VMware vSphere Metro Storage Cluster — active/active stretch across two sites"
  compute_ap: "Active/Passive DR — secondary site sized at 50% for cold standby"
```

### fr.yaml additions

```yaml
layout:
  compute: "Dimensionnement calcul"

compute:
  title: "Dimensionnement calcul"
  no_data: "Aucune donnée. Téléchargez un fichier pour voir les recommandations de dimensionnement."
  active_vcpus: "vCPUs actifs"
  active_ram: "RAM active (Gio)"
  excluded_vms: "%{count} VM(s) éteinte(s) ou gabarit(s) exclue(s)"
  host_preset: "Configuration de l'hôte"
  custom_preset: "Personnalisé"
  cores_per_socket: "Cœurs / socket"
  sockets: "Sockets"
  ram_gib: "RAM (Gio)"
  overcommit_ratio: "Ratio de surcharge vCPU"
  overcommit_hint: "vCPUs par cœur physique. 4:1 est la norme pour les charges mixtes."
  results_heading: "Recommandations de nombre d'hôtes"
  ha_mode: "Mode HA"
  hosts_n1: "N+1 HA"
  hosts_n1_detail: "Standard : N hôtes + 1 pour le basculement"
  vmsc_toggle: "Cluster étiré vMSC"
  vmsc_site_heading: "Hôtes par site (vMSC)"
  vmsc_no_dc_data: "La colonne Datacenter est vide ou n'a qu'une seule valeur distincte — impossible de calculer les comptes par site. L'export doit inclure une colonne Datacenter avec au moins 2 valeurs distinctes."
  ap_toggle: "DR Actif/Passif"
  ap_primary: "Site principal"
  ap_secondary: "Site secondaire (passif)"
  ap_secondary_detail: "50% du principal — veille froide"
  binding_constraint: "Contrainte dimensionnante"
  constraint_vcpu: "vCPU"
  constraint_ram: "RAM"

tooltip:
  compute_preset: "Sélectionnez un modèle Dell PowerEdge ou entrez des spécifications personnalisées"
  compute_overcommit: "Nombre de vCPUs par cœur physique. Plus élevé = plus de VMs par hôte mais plus de contention."
  compute_vmsc: "VMware vSphere Metro Storage Cluster — actif/actif étiré sur deux sites"
  compute_ap: "DR Actif/Passif — site secondaire dimensionné à 50% pour la veille froide"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Thread-count (HT) for vCPU sizing | Physical core count per VMware Architecture Toolkit | Correct: 2x more conservative, defensible to customers |
| Fixed 4:1 overcommit | Configurable ratio (1–10) with 4.0 default | User adjusts for workload sensitivity |
| Manual host count spreadsheet | In-tool reactive recommendation | Pre-sales productivity gain |

**Deprecated guidance:**

- VMware vCPU sizing with HT threads: Broadcom 2024 guidance recommends physical cores only for capacity planning. Many older blog posts still use thread count — do not follow them.

---

## Open Questions

1. **vMSC minimum host count**
   - What we know: Broadcom docs require minimum 3+3 hosts per site + witness for vSAN stretched; 2+2 for compute-only.
   - What's unclear: Should the tool enforce a minimum of 3 hosts per site for vMSC output?
   - Recommendation: For v4.0, do not enforce a minimum — return the formula result and note in a tooltip that vMSC typically requires minimum 3 hosts/site.

2. **RAM overcommit**
   - What we know: ESXi allows memory ballooning/swapping, so RAM can technically be overcommitted.
   - What's unclear: Should the tool support RAM overcommit ratio input?
   - Recommendation: For v4.0, no RAM overcommit (ratio = 1.0 fixed). RAM overcommit is not recommended for production workloads and adds complexity. Keep it simple: size RAM at 1:1.

3. **Per-site vMSC VM split**
   - What we know: vMSC with vSAN Stretched requires equal VM distribution across sites; non-vSAN vMSC is more flexible.
   - What's unclear: Should the tool split VMs by datacenter column for per-site vCPU calculation, or apply the full workload to each site?
   - Recommendation: Apply full workload to each site (conservative) — each site must independently handle 100% of VMs. This is the safe pre-sales assumption. Splitting by datacenter requires reliable datacenter assignment per VM which is not guaranteed in RVTools exports.

---

## Recommended Plan Split

Phase 22 maps to exactly 3 PLAN.md files as specified in the roadmap:

### 22-01-PLAN.md — `pipeline/compute_sizing.py` (Pure pipeline module)

**Scope:**

- `HostConfig` dataclass (frozen)
- `ComputeSizingResult` dataclass (frozen, includes all HA mode outputs)
- `DELL_POWEREDGE_PRESETS` list (4 presets + Custom)
- `compute_sizing(df, host_config, overcommit_ratio, vmsc_enabled, ap_enabled)` function
- All helper functions: `_hosts_n1`, `_hosts_by_ram`, `_vmsc_sites`, `_vmsc_available`, `_hosts_ap_secondary`, `_empty_result`

**Tests:** `tests/test_compute_sizing.py` — synthetic DataFrames, edge cases:

- Empty DataFrame
- All VMs powered off → zero result with `excluded_vm_count = N`
- Zero `num_cpus` data (LiveOptics export without CPU column)
- Single-datacenter vMSC → `vmsc_warning` populated, `hosts_vmsc_per_site = None`
- Two-datacenter vMSC → per-site count returned
- RAM binding constraint > vCPU binding constraint → max wins
- Overcommit ratio clamped at bounds (0 → 1.0, 11 → 10.0)
- Custom host config with arbitrary specs

### 22-02-PLAN.md — `ui/pages/compute.py` (/compute page)

**Scope:**

- `@ui.page("/compute")` route
- Settings panel: `ui.select` for preset, `ui.number` for overcommit ratio (reactive), vMSC toggle (`ui.switch`), AP toggle (`ui.switch`), custom host spec inputs (shown only when "Custom" preset selected)
- Aggregate display: cards for active vCPU total, active RAM total, excluded VM count
- Results panel (`@ui.refreshable`): N+1 host count card, vMSC per-site table (or warning), Active/Passive table
- Binding constraint indicator (show which dimension — vCPU or RAM — drove the host count)
- No-data guard: redirect card pointing to /upload
- Route import in `main.py`

**No separate tests for the page** — NiceGUI pages are integration-tested; unit tests in 22-01 cover the logic.

### 22-03-PLAN.md — i18n keys, navigation link, and test coverage

**Scope:**

- Add `compute:` namespace to `en.yaml` and `fr.yaml` (all keys listed above)
- Add `layout.compute` nav key to both locale files
- Add `/compute` link to `src/store_predict/ui/layout.py` nav bar
- `tests/test_i18n.py` addition: assert all `compute.*` keys present in both locales
- `tests/test_compute_sizing.py` already covered in 22-01 — this plan adds any missing test coverage for edge cases discovered during 22-02 implementation

---

## Sources

### Primary (HIGH confidence)

- `src/store_predict/pipeline/parsers/columns.py` — CANONICAL_COLUMNS verified: `num_cpus`, `memory_mib`, `datacenter`, `is_powered_on`, `is_template` all present
- `src/store_predict/pipeline/parsers/rvtools.py` — `num_cpus` and `memory_mib` parsing confirmed; both filled to 0 if column absent
- `src/store_predict/pipeline/parsers/liveoptics.py` — `num_cpus` and `memory_mib` parsing confirmed; both filled to 0 if column absent
- `src/store_predict/pipeline/calculation.py` — `CalculationSummary.total_cpus` and `total_memory_mib` fields confirmed; these cover ALL VMs (must filter separately in compute_sizing)
- `src/store_predict/pipeline/health_checks.py` + `layout_engine.py` — frozen dataclass pattern confirmed
- `src/store_predict/ui/pages/concerns.py` — page pattern (no-data guard, `load_session_data()`, `layout()` context manager) confirmed
- `src/store_predict/ui/pages/layout_page.py` — `@ui.refreshable` reactive pattern, session-backed settings confirmed
- `src/store_predict/ui/layout.py` — nav link pattern confirmed (add one `ui.link()` call)
- `src/store_predict/main.py` — route registration pattern confirmed (one import statement)
- `.planning/research/SUMMARY.md` — project-level research confirming no new dependencies needed, confirmed compute columns already in schema

### Secondary (MEDIUM confidence)

- [Dell PowerEdge R760 spec sheet (PDF)](https://www.delltechnologies.com/asset/da-dk/products/servers/technical-support/poweredge-r760-spec-sheet.pdf) — 2-socket, up to 56 cores/socket (4th Gen) or 64 cores/socket (5th Gen) confirmed
- [Dell PowerEdge R860 spec sheet (PDF)](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r860-spec-sheet.pdf) — 4-socket, up to 60 cores/socket confirmed
- [Dell PowerEdge R960 spec sheet (PDF)](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r960-spec-sheet.pdf) — 4-socket, up to 60 cores/socket confirmed
- [VMware Architecture Toolkit — pCPU sizing guidance](https://download3.vmware.com/vcat/) — physical cores, not HT threads, for VM density sizing
- [Broadcom TechDocs VCF — Sizing Compute Resources for ESXi](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/) — N+1 HA formula confirmed as industry standard

### Tertiary (LOW confidence)

- Various reseller listings (xByte, Skywardtel, SANStorageWorks) — corroborate Dell spec sheet core counts
- Community blog posts on vCPU overcommit ratios (4:1 default) — widely cited; validate with customer workload profile

---

## Metadata

**Confidence breakdown:**

- Column availability: HIGH — verified directly in live source files
- Compute formula (N+1 HA): HIGH — standard industry formula, verified in Broadcom TechDocs
- Dell PowerEdge specs: MEDIUM — from Dell spec sheets (reseller corroborated); exact customer config will vary
- vMSC per-site logic: MEDIUM — 100%-per-site approach is conservative and safe; alternative split-by-datacenter approach is more complex
- Active/Passive 50% ratio: MEDIUM — widely used pre-sales convention; not an official VMware standard
- i18n key structure: HIGH — follows established project pattern

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain; Dell server specs rarely change)
