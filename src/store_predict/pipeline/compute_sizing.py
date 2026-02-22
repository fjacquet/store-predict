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
    "ComputeSizingResult",
    "HostConfig",
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
    # vMSC (stretch cluster)
    vmsc_available: bool
    vmsc_sites: tuple[str, ...]
    vmsc_hosts_per_site: int
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
        vmsc_hosts_per_site=0,
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

    Returns:
        ComputeSizingResult with all host counts and metadata.
    """
    if df is None or df.empty:
        return _empty_result(host_config, overcommit_ratio)

    # Clamp overcommit ratio before any computation
    ratio = _clamp_ratio(overcommit_ratio)

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
            vmsc_hosts_per_site=0,
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
            vmsc_hosts_per_site=0,
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
    vmsc_hosts = _hosts_n1(total_vcpus, host_pcores, ratio) if (vmsc_enabled and vmsc_avail) else 0

    # Active/Passive DR — secondary site = ceil(primary / 2), minimum 1
    ap_primary = hosts
    ap_secondary = max(1, math.ceil(hosts / 2))

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
        vmsc_hosts_per_site=vmsc_hosts,
        ap_primary_hosts=ap_primary,
        ap_secondary_hosts=ap_secondary,
        host_config=host_config,
        overcommit_ratio=ratio,
    )
