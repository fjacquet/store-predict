"""Tests for the RVTools guest-level capacity basis.

On vSAN, ``vInfo.Provisioned MiB`` includes FTT/mirror overhead and misses
guest-mounted volumes (e.g. Kubernetes persistent volumes). The parser therefore
recomputes capacity from the guest view:

    provisioned = max(Σ vPartition.Capacity, vmdk_logical)   # both FTT-free
    in_use      = Σ vPartition.Consumed (when guest data exists)

where ``vmdk_logical`` is ``vInfo.Total disk capacity MiB`` or Σ ``vDisk.Capacity MiB``.
These tests use synthetic xlsx fixtures (real openpyxl files, no mocks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from store_predict.pipeline.parsers.rvtools import RvtoolsCapacityInfo, parse_rvtools

if TYPE_CHECKING:
    from pathlib import Path


def _write_rvtools(
    path: Path,
    vinfo: pd.DataFrame,
    vdisk: pd.DataFrame | None = None,
    vpartition: pd.DataFrame | None = None,
    vdatastore: pd.DataFrame | None = None,
) -> Path:
    """Write a minimal multi-sheet RVTools .xlsx fixture."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        vinfo.to_excel(writer, sheet_name="vInfo", index=False)
        if vdisk is not None:
            vdisk.to_excel(writer, sheet_name="vDisk", index=False)
        if vpartition is not None:
            vpartition.to_excel(writer, sheet_name="vPartition", index=False)
        if vdatastore is not None:
            vdatastore.to_excel(writer, sheet_name="vDatastore", index=False)
    return path


def _vsan_path(name: str) -> str:
    return f"[vsanDS] {name}/{name}.vmx"


@pytest.fixture
def scenarios_xlsx(tmp_path: Path) -> Path:
    """Newer-RVTools fixture (has 'Total disk capacity MiB') with five VM shapes.

    Sizes in MiB. All VMs live on a vSAN datastore so vInfo.Provisioned is the
    FTT-inflated figure that must be discarded in favour of the guest view.
    """
    vinfo = pd.DataFrame(
        {
            "VM": ["normal", "container", "raw", "notools", "fallback"],
            "Powerstate": ["poweredOn"] * 5,
            "Template": [False] * 5,
            "OS according to the VMware Tools": ["Ubuntu Linux"] * 5,
            # FTT-inflated / placeholder datastore figures the basis must override:
            "Provisioned MiB": [200_000, 20_000, 160_000, 50_000, 30_000],
            "In Use MiB": [120_000, 20_000, 80_000, 45_000, 15_000],
            "Total disk capacity MiB": [100_000, 10_000, 80_000, 40_000, 0],
            "Path": [_vsan_path(n) for n in ["normal", "container", "raw", "notools", "fallback"]],
            "VM UUID": ["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5"],
            "Datacenter": ["DC1"] * 5,
            "Cluster": ["C1"] * 5,
        }
    )
    vdisk = pd.DataFrame(
        {
            "VM": ["normal", "container", "raw", "notools"],
            "VM UUID": ["uuid-1", "uuid-2", "uuid-3", "uuid-4"],
            "Capacity MiB": [100_000, 10_000, 80_000, 40_000],
            # note: "fallback" has no vDisk rows
        }
    )
    vpartition = pd.DataFrame(
        {
            "VM": ["normal", "container", "raw"],
            "VM UUID": ["uuid-1", "uuid-2", "uuid-3"],
            # container's guest filesystems (mounted PVs) dwarf its tiny VMDK;
            # raw's guest filesystem sees less than the VMDK (raw/unformatted space).
            "Capacity MiB": [95_000, 500_000, 30_000],
            "Consumed MiB": [60_000, 300_000, 25_000],
            # note: "notools" and "fallback" have no vPartition rows
        }
    )
    vdatastore = pd.DataFrame({"Name": ["vsanDS", "vmfsDS"], "Type": ["vsan", "VMFS"]})
    return _write_rvtools(tmp_path / "scenarios.xlsx", vinfo, vdisk, vpartition, vdatastore)


class TestGuestCapacityBasis:
    """Per-VM provisioned/in_use under the guest-level basis."""

    def test_normal_vm_deinflated_to_logical(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        row = df[df["vm_name"] == "normal"].iloc[0]
        # max(guest_cap 95000, vmdk_logical 100000) — NOT the inflated 200000
        assert row["provisioned_mib"] == pytest.approx(100_000)
        assert row["in_use_mib"] == pytest.approx(60_000)

    def test_container_vm_uses_guest_mounts(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        row = df[df["vm_name"] == "container"].iloc[0]
        # guest capacity (mounted PVs) >> tiny VMDK
        assert row["provisioned_mib"] == pytest.approx(500_000)
        assert row["in_use_mib"] == pytest.approx(300_000)

    def test_raw_device_vm_uses_vmdk_logical(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        row = df[df["vm_name"] == "raw"].iloc[0]
        # vmdk_logical (80000) > guest filesystem capacity (30000)
        assert row["provisioned_mib"] == pytest.approx(80_000)
        assert row["in_use_mib"] == pytest.approx(25_000)

    def test_no_tools_vm_uses_vmdk_logical_and_caps_in_use(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        row = df[df["vm_name"] == "notools"].iloc[0]
        # no guest data, but Total disk capacity present -> use it (not vInfo 50000)
        assert row["provisioned_mib"] == pytest.approx(40_000)
        # vInfo In Use (45000) capped at provisioned (40000)
        assert row["in_use_mib"] == pytest.approx(40_000)

    def test_fallback_vm_keeps_vinfo_value(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        row = df[df["vm_name"] == "fallback"].iloc[0]
        # no guest data AND no disk capacity -> fall back to raw vInfo
        assert row["provisioned_mib"] == pytest.approx(30_000)
        assert row["in_use_mib"] == pytest.approx(15_000)

    def test_in_use_never_exceeds_provisioned(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        assert (df["in_use_mib"] <= df["provisioned_mib"] + 1e-6).all()

    def test_capacity_info_counts(self, scenarios_xlsx: Path) -> None:
        df = parse_rvtools(scenarios_xlsx)
        info = df.attrs["rvtools_capacity_info"]
        assert isinstance(info, RvtoolsCapacityInfo)
        assert info.total_vms == 5
        assert info.fallback_count == 1  # only "fallback"
        assert info.vsan_vm_count == 5  # all on vsanDS
        # the recompute materially changed the provisioned total (direction depends
        # on the mix: FTT inflation pushes it down, captured mounts push it up)
        assert info.changed
        assert info.pre_provisioned_mib == pytest.approx(460_000)


class TestOlderLayoutFallback:
    """Older RVTools without 'Total disk capacity MiB' -> sum vDisk.Capacity."""

    def test_uses_vdisk_capacity_sum(self, tmp_path: Path) -> None:
        vinfo = pd.DataFrame(
            {
                "VM": ["multi"],
                "Powerstate": ["poweredOn"],
                "Template": [False],
                "OS according to the VMware Tools": ["Windows Server"],
                "Provisioned MB": [120_000],  # FTT-inflated, older "MB" header
                "In Use MB": [70_000],
                "Path": [_vsan_path("multi")],
                "VM UUID": ["uuid-m"],
            }
        )
        vdisk = pd.DataFrame(
            {
                "VM": ["multi", "multi"],
                "VM UUID": ["uuid-m", "uuid-m"],
                "Capacity MB": [40_000, 20_000],  # logical sum = 60000
            }
        )
        vpartition = pd.DataFrame(
            {
                "VM": ["multi"],
                "VM UUID": ["uuid-m"],
                "Capacity MB": [55_000],
                "Consumed MB": [35_000],
            }
        )
        path = _write_rvtools(tmp_path / "older.xlsx", vinfo, vdisk, vpartition)
        df = parse_rvtools(path)
        row = df[df["vm_name"] == "multi"].iloc[0]
        # max(guest 55000, vDisk-sum 60000) = 60000 (not inflated 120000)
        assert row["provisioned_mib"] == pytest.approx(60_000)
        assert row["in_use_mib"] == pytest.approx(35_000)


class TestMissingSecondarySheets:
    """vInfo-only exports must not crash and degrade gracefully."""

    def test_vinfo_only_uses_total_disk_capacity(self, tmp_path: Path) -> None:
        vinfo = pd.DataFrame(
            {
                "VM": ["solo"],
                "Powerstate": ["poweredOn"],
                "Template": [False],
                "OS according to the VMware Tools": ["Ubuntu Linux"],
                "Provisioned MiB": [80_000],
                "In Use MiB": [50_000],
                "Total disk capacity MiB": [40_000],
                "VM UUID": ["uuid-s"],
            }
        )
        df = parse_rvtools(_write_rvtools(tmp_path / "solo.xlsx", vinfo))
        row = df[df["vm_name"] == "solo"].iloc[0]
        # no vPartition/vDisk -> provisioned from Total disk capacity; in_use from vInfo capped
        assert row["provisioned_mib"] == pytest.approx(40_000)
        assert row["in_use_mib"] == pytest.approx(40_000)

    def test_vinfo_only_no_disk_capacity_falls_back_to_vinfo(self, tmp_path: Path) -> None:
        vinfo = pd.DataFrame(
            {
                "VM": ["bare"],
                "Powerstate": ["poweredOn"],
                "Template": [False],
                "OS according to the VMware Tools": ["Ubuntu Linux"],
                "Provisioned MiB": [12_345],
                "In Use MiB": [6_000],
                "VM UUID": ["uuid-b"],
            }
        )
        df = parse_rvtools(_write_rvtools(tmp_path / "bare.xlsx", vinfo))
        row = df[df["vm_name"] == "bare"].iloc[0]
        assert row["provisioned_mib"] == pytest.approx(12_345)
        assert row["in_use_mib"] == pytest.approx(6_000)
