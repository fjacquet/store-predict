"""Compute ESXi host counts from session DataFrame.

Pure pipeline module with zero UI imports. Entry point: compute_sizing(df, host_config).
Filters to active non-template VMs before aggregating. Returns has_data=False if df is
None/empty or all VMs are excluded/have zero CPU+RAM data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from store_predict.config import COMPUTE_PRESETS_CSV_PATH

__all__ = [
    "DELL_POWEREDGE_PRESETS",
    "ClusterSizingRow",
    "ComputeSizingResult",
    "HostConfig",
    "compute_cluster_breakdown",
    "compute_sizing",
]


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HostConfig:
    """Physical host specification for ESXi sizing.

    cores_per_socket and sockets represent physical cores only (not HT threads).
    VMware Architecture Toolkit guidance: use physical cores for VM density sizing.
    """

    name: str
    cores_per_socket: int
    sockets: int
    ram_gib: int

    @property
    def total_cores(self) -> int:
        """Total physical core count across all sockets."""
        return self.cores_per_socket * self.sockets

    @property
    def total_ram_mib(self) -> float:
        """Total host RAM in MiB."""
        return float(self.ram_gib * 1024)


@dataclass(frozen=True)
class ClusterSizingRow:
    """Per-cluster sizing result for the compute breakdown table."""

    cluster_name: str
    vm_count: int
    total_vcpus: int
    total_ram_gib: float
    hosts_needed: int


@dataclass(frozen=True)
class ComputeSizingResult:
    """Output of compute_sizing() — all host counts for a single host config.

    All host counts use N+1 HA formula: N hosts carry the workload + 1 for failover.
    hosts_n1 = max(hosts_by_vcpu, hosts_by_ram) — whichever dimension binds.
    """

    has_data: bool
    total_active_vcpus: int
    total_active_ram_gib: float
    excluded_vm_count: int
    # N+1 HA breakdown
    hosts_by_vcpu: int
    hosts_by_ram: int
    hosts_n1: int
    # vMSC (stretch cluster) — per-site counts replace the old vmsc_hosts_per_site scalar
    vmsc_available: bool
    vmsc_sites: tuple[str, ...]
    vmsc_site_a_hosts: int
    vmsc_site_b_hosts: int
    # Active/Passive DR
    ap_primary_hosts: int
    ap_secondary_hosts: int
    # Config used
    host_config: HostConfig
    overcommit_ratio: float


# ---------------------------------------------------------------------------
# Preset loader
# ---------------------------------------------------------------------------


def load_presets(path: Path = COMPUTE_PRESETS_CSV_PATH) -> list[HostConfig]:
    """Load HostConfig presets from a semicolon-delimited CSV file.

    CSV format (header row required):
        name;server_model;cpu_family;cpu_name;cores_per_socket;sockets;ram_gib

    The 'Custom' row (if present) is loaded as-is; the UI treats it as a
    placeholder that the user customizes via numeric inputs.
    Falls back to a minimal built-in list if the file is missing or unreadable.
    """
    try:
        df = pd.read_csv(
            path,
            sep=";",
            dtype=str,
            usecols=["name", "cores_per_socket", "sockets", "ram_gib"],
        )
    except Exception:
        # Fallback: single Custom entry so the UI never crashes
        return [HostConfig(name="Custom", cores_per_socket=28, sockets=2, ram_gib=512)]

    df = df.dropna(subset=["name"])
    df["name"] = df["name"].str.strip()
    df["cores_per_socket"] = pd.to_numeric(df["cores_per_socket"], errors="coerce").fillna(28)
    df["sockets"] = pd.to_numeric(df["sockets"], errors="coerce").fillna(2)
    df["ram_gib"] = pd.to_numeric(df["ram_gib"], errors="coerce").fillna(512)

    return [
        HostConfig(
            name=str(row["name"]),
            cores_per_socket=int(row["cores_per_socket"]),
            sockets=int(row["sockets"]),
            ram_gib=int(row["ram_gib"]),
        )
        for _, row in df.iterrows()
    ]


# Loaded once at import time from the bundled CSV.
# Re-call load_presets(custom_path) to use a user-supplied file.
DELL_POWEREDGE_PRESETS: list[HostConfig] = load_presets()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _clamp_ratio(ratio: float) -> float:
    """Clamp overcommit ratio to [0.5, 20.0]."""
    return max(0.5, min(20.0, ratio))


def _hosts_n1(total_vcpus: int, host_pcores: int, ratio: float) -> int:
    """ESXi host count for N+1 HA (vCPU-driven).

    N hosts carry the workload; +1 host for HA failover.
    Uses physical cores (not HT threads) per VMware sizing guidance.

    Returns 0 if any argument is <= 0 (guard against division by zero).
    """
    if total_vcpus <= 0 or host_pcores <= 0 or ratio <= 0:
        return 0
    capacity = max(1, host_pcores) * max(0.5, ratio)
    return math.ceil(total_vcpus / capacity) + 1


def _hosts_by_ram(total_ram_gib: float, host_ram_gib: int) -> int:
    """Hosts needed to hold total VM RAM (no RAM overcommit for production workloads).

    Returns 0 if either argument is <= 0.
    """
    if total_ram_gib <= 0 or host_ram_gib <= 0:
        return 0
    return math.ceil(total_ram_gib / max(1, host_ram_gib)) + 1


def _vmsc_sites(df: pd.DataFrame) -> list[str]:
    """Return list of distinct non-empty datacenter values from the DataFrame."""
    if "datacenter" not in df.columns:
        return []
    return [v for v in df["datacenter"].dropna().unique() if str(v).strip()]


def _empty_result(host_config: HostConfig, overcommit_ratio: float) -> ComputeSizingResult:
    """Return a zero-count result with has_data=False."""
    return ComputeSizingResult(
        has_data=False,
        total_active_vcpus=0,
        total_active_ram_gib=0.0,
        excluded_vm_count=0,
        hosts_by_vcpu=0,
        hosts_by_ram=0,
        hosts_n1=0,
        vmsc_available=False,
        vmsc_sites=(),
        vmsc_site_a_hosts=0,
        vmsc_site_b_hosts=0,
        ap_primary_hosts=0,
        ap_secondary_hosts=0,
        host_config=host_config,
        overcommit_ratio=_clamp_ratio(overcommit_ratio),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def compute_sizing(
    df: pd.DataFrame | None,
    host_config: HostConfig,
    overcommit_ratio: float = 4.0,
    vmsc_enabled: bool = False,
    vmsc_split_ratio: float = 0.5,
    ap_active_ratio: float = 1.0,
) -> ComputeSizingResult:
    """Compute ESXi host counts from session DataFrame.

    Filters to active non-template VMs before aggregating.
    Returns has_data=False if df is None/empty or all VMs are excluded/have zero CPU+RAM data.

    A/P (Active/Passive DR) counts are always computed and available in the result;
    the UI decides whether to display them based on user preference.

    Args:
        df: Canonical DataFrame from load_session_data(), or None if no data uploaded.
            Must include is_powered_on, is_template, num_cpus, memory_mib columns.
            Optionally includes datacenter column for vMSC mode.
        host_config: Physical host specification to size against.
        overcommit_ratio: vCPU-to-pCPU overcommit. Clamped to [0.5, 20.0]. Default: 4.0.
        vmsc_enabled: Whether to compute per-site vMSC counts (requires 2+ datacenters).
        vmsc_split_ratio: Fraction of VMs/load on Site A (Site B gets 1 - vmsc_split_ratio).
            Clamped internally to [0.01, 0.99]. Default: 0.5 (50/50 symmetric split).
            Only used when vmsc_enabled=True and 2+ datacenters are present.
        ap_active_ratio: Fraction of VMs running active on the primary AP site.
            Clamped internally to [0.01, 1.0]. Default: 1.0 (100% active on primary).
            ap_secondary is always sized at 50% of computed primary (cold standby convention).

    Returns:
        ComputeSizingResult with all host counts and metadata.
    """
    if df is None or df.empty:
        return _empty_result(host_config, overcommit_ratio)

    # Clamp overcommit ratio before any computation
    ratio = _clamp_ratio(overcommit_ratio)

    # Clamp split ratios
    clamped_vmsc_split = max(0.01, min(0.99, vmsc_split_ratio))
    clamped_ap_active = max(0.01, min(1.0, ap_active_ratio))

    # Filter to active, non-template VMs
    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]  # noqa: E712
    excluded_count = len(df) - len(active)

    if active.empty:
        # Return empty result but with actual excluded_vm_count
        return ComputeSizingResult(
            has_data=False,
            total_active_vcpus=0,
            total_active_ram_gib=0.0,
            excluded_vm_count=excluded_count,
            hosts_by_vcpu=0,
            hosts_by_ram=0,
            hosts_n1=0,
            vmsc_available=False,
            vmsc_sites=(),
            vmsc_site_a_hosts=0,
            vmsc_site_b_hosts=0,
            ap_primary_hosts=0,
            ap_secondary_hosts=0,
            host_config=host_config,
            overcommit_ratio=ratio,
        )

    # Aggregate CPU and RAM — coerce to numeric to handle None/object dtype from session round-trips
    total_vcpus = int(pd.to_numeric(active["num_cpus"], errors="coerce").fillna(0).sum())
    total_ram_mib = float(pd.to_numeric(active["memory_mib"], errors="coerce").fillna(0).sum())
    total_ram_gib = total_ram_mib / 1024.0

    # Guard: no meaningful compute data
    if total_vcpus == 0 and total_ram_gib == 0.0:
        return ComputeSizingResult(
            has_data=False,
            total_active_vcpus=0,
            total_active_ram_gib=0.0,
            excluded_vm_count=excluded_count,
            hosts_by_vcpu=0,
            hosts_by_ram=0,
            hosts_n1=0,
            vmsc_available=False,
            vmsc_sites=(),
            vmsc_site_a_hosts=0,
            vmsc_site_b_hosts=0,
            ap_primary_hosts=0,
            ap_secondary_hosts=0,
            host_config=host_config,
            overcommit_ratio=ratio,
        )

    # Compute host counts — take max of vCPU-driven and RAM-driven constraints
    host_pcores = host_config.total_cores
    hv = _hosts_n1(total_vcpus, host_pcores, ratio)
    hr = _hosts_by_ram(total_ram_gib, host_config.ram_gib)
    hosts = max(hv, hr)

    # vMSC (stretch cluster) — requires 2+ distinct non-empty datacenter values
    sites = _vmsc_sites(active)
    vmsc_avail = len(sites) >= 2
    if vmsc_enabled and vmsc_avail:
        # Per-site sizing using configurable split ratio
        site_a_vcpus = round(total_vcpus * clamped_vmsc_split)
        site_b_vcpus = total_vcpus - site_a_vcpus
        site_a_ram_gib = total_ram_gib * clamped_vmsc_split
        site_b_ram_gib = total_ram_gib - site_a_ram_gib
        vmsc_site_a = max(
            _hosts_n1(site_a_vcpus, host_pcores, ratio),
            _hosts_by_ram(site_a_ram_gib, host_config.ram_gib),
        )
        vmsc_site_b = max(
            _hosts_n1(site_b_vcpus, host_pcores, ratio),
            _hosts_by_ram(site_b_ram_gib, host_config.ram_gib),
        )
    else:
        vmsc_site_a = 0
        vmsc_site_b = 0

    # Active/Passive DR — primary sized by ap_active_ratio; secondary = ceil(primary / 2)
    active_vcpus_primary = round(total_vcpus * clamped_ap_active)
    active_ram_gib_primary = total_ram_gib * clamped_ap_active
    ap_primary = max(
        _hosts_n1(active_vcpus_primary, host_pcores, ratio),
        _hosts_by_ram(active_ram_gib_primary, host_config.ram_gib),
    )
    ap_secondary = max(1, math.ceil(ap_primary / 2))

    return ComputeSizingResult(
        has_data=True,
        total_active_vcpus=total_vcpus,
        total_active_ram_gib=total_ram_gib,
        excluded_vm_count=excluded_count,
        hosts_by_vcpu=hv,
        hosts_by_ram=hr,
        hosts_n1=hosts,
        vmsc_available=vmsc_avail,
        vmsc_sites=tuple(sites),
        vmsc_site_a_hosts=vmsc_site_a,
        vmsc_site_b_hosts=vmsc_site_b,
        ap_primary_hosts=ap_primary,
        ap_secondary_hosts=ap_secondary,
        host_config=host_config,
        overcommit_ratio=ratio,
    )


def compute_cluster_breakdown(
    df: pd.DataFrame | None,
    host_config: HostConfig,
    overcommit_ratio: float = 4.0,
) -> list[ClusterSizingRow]:
    """Compute per-cluster ESXi host sizing from session DataFrame.

    Groups active non-template VMs by cluster and computes hosts_needed per cluster
    using the same N+1 HA formula as compute_sizing().

    VMs with empty or null cluster are grouped under the sentinel "__no_cluster__".
    Results are sorted alphabetically by cluster_name (via groupby sort=True).

    Args:
        df: Canonical DataFrame from load_session_data(), or None if no data uploaded.
            Must include is_powered_on, is_template, num_cpus, memory_mib, cluster columns.
        host_config: Physical host specification to size against.
        overcommit_ratio: vCPU-to-pCPU overcommit. Clamped to [0.5, 20.0]. Default: 4.0.

    Returns:
        List of ClusterSizingRow, one per distinct cluster, sorted alphabetically.
        Returns [] if df is None, empty, or all VMs are excluded.
    """
    if df is None or df.empty:
        return []

    # Filter to active, non-template VMs
    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]  # noqa: E712

    if active.empty:
        return []

    ratio = _clamp_ratio(overcommit_ratio)

    # Normalize cluster column: fill None, strip whitespace, replace empty with sentinel
    df_work = active.copy()
    cluster_col = df_work["cluster"].fillna("").astype(str).str.strip()
    df_work = df_work.copy()
    df_work["cluster_norm"] = cluster_col.replace("", "__no_cluster__")

    rows: list[ClusterSizingRow] = []
    for cluster_name, group in df_work.groupby("cluster_norm", sort=True):
        total_vcpus = int(pd.to_numeric(group["num_cpus"], errors="coerce").fillna(0).sum())
        total_ram_mib = float(pd.to_numeric(group["memory_mib"], errors="coerce").fillna(0).sum())
        total_ram_gib = total_ram_mib / 1024.0

        hv = _hosts_n1(total_vcpus, host_config.total_cores, ratio)
        hr = _hosts_by_ram(total_ram_gib, host_config.ram_gib)
        hosts_needed = max(hv, hr)

        rows.append(
            ClusterSizingRow(
                cluster_name=str(cluster_name),
                vm_count=len(group),
                total_vcpus=total_vcpus,
                total_ram_gib=total_ram_gib,
                hosts_needed=hosts_needed,
            )
        )

    return rows
