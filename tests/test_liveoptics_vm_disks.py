"""Tests for LiveOptics VM Disks aggregation.

LiveOptics' 'VMs' sheet column 'Virtual Disk Size (MiB)' reports only the
primary disk; the parser must sum per-disk capacities from the 'VM Disks'
sheet when present, and fall back to the VMs-sheet value otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from store_predict.pipeline.parsers import (
    parse_liveoptics_vm_disks,
    parse_liveoptics_xlsx,
)


class TestParseLiveopticsVmDisks:
    """Direct tests for parse_liveoptics_vm_disks()."""

    def test_aggregates_sample_file(self, liveoptics_xlsx_path: Path) -> None:
        df = parse_liveoptics_vm_disks(liveoptics_xlsx_path)
        assert not df.empty
        assert list(df.columns) == [
            "mob_id",
            "vm_name",
            "disks_provisioned_mib",
            "disks_in_use_mib",
        ]

    def test_one_row_per_vm(self, liveoptics_xlsx_path: Path) -> None:
        agg = parse_liveoptics_vm_disks(liveoptics_xlsx_path)
        raw = pd.read_excel(liveoptics_xlsx_path, sheet_name="VM Disks", engine="openpyxl")
        raw.columns = raw.columns.str.strip()
        assert len(agg) == raw["MOB ID"].nunique()

    def test_sum_matches_raw(self, liveoptics_xlsx_path: Path) -> None:
        agg = parse_liveoptics_vm_disks(liveoptics_xlsx_path)
        raw = pd.read_excel(liveoptics_xlsx_path, sheet_name="VM Disks", engine="openpyxl")
        raw.columns = raw.columns.str.strip()
        assert agg["disks_provisioned_mib"].sum() == pytest.approx(
            pd.to_numeric(raw["Capacity (MiB)"], errors="coerce").fillna(0).sum(),
            rel=1e-6,
        )

    def test_missing_sheet_returns_empty(self, rvtools_path: Path) -> None:
        df = parse_liveoptics_vm_disks(rvtools_path)
        assert df.empty
        assert list(df.columns) == [
            "mob_id",
            "vm_name",
            "disks_provisioned_mib",
            "disks_in_use_mib",
        ]


class TestParseLiveopticsXlsxOverride:
    """Tests that parse_liveoptics_xlsx() overrides provisioned/in_use with
    summed disk totals when the 'VM Disks' sheet is available."""

    def test_total_provisioned_matches_disk_sum_plus_fallback(self, liveoptics_xlsx_path: Path) -> None:
        """Parser total = sum(disk capacities for VMs with disk rows)
        + sum(VMs-sheet value for VMs without disk rows)."""
        raw_vms = pd.read_excel(liveoptics_xlsx_path, sheet_name="VMs", engine="openpyxl")
        raw_disks = pd.read_excel(liveoptics_xlsx_path, sheet_name="VM Disks", engine="openpyxl")
        raw_vms.columns = raw_vms.columns.str.strip()
        raw_disks.columns = raw_disks.columns.str.strip()

        disk_vm_ids = set(raw_disks["MOB ID"].astype(str))
        vms_ids = raw_vms["MOB ID"].astype(str)
        matched_disk_cap = (
            pd.to_numeric(
                raw_disks[raw_disks["MOB ID"].astype(str).isin(set(vms_ids))]["Capacity (MiB)"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        unmatched_vms_value = (
            pd.to_numeric(
                raw_vms[~vms_ids.isin(disk_vm_ids)]["Virtual Disk Size (MiB)"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        expected = matched_disk_cap + unmatched_vms_value

        parsed = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert parsed["provisioned_mib"].sum() == pytest.approx(expected, rel=1e-6)

    def test_multi_disk_vm_sums_correctly(self, liveoptics_xlsx_path: Path) -> None:
        raw_vms = pd.read_excel(liveoptics_xlsx_path, sheet_name="VMs", engine="openpyxl")
        raw_disks = pd.read_excel(liveoptics_xlsx_path, sheet_name="VM Disks", engine="openpyxl")
        raw_vms.columns = raw_vms.columns.str.strip()
        raw_disks.columns = raw_disks.columns.str.strip()

        # Pick any VM with >= 2 disks
        disks_per_vm = raw_disks.groupby("MOB ID").size()
        multi = disks_per_vm[disks_per_vm >= 2]
        if multi.empty:
            pytest.skip("Sample has no multi-disk VMs")
        target_mob_id = multi.index[0]

        vm_row = raw_vms[raw_vms["MOB ID"] == target_mob_id].iloc[0]
        vm_name = str(vm_row["VM Name"]).strip()
        vms_sheet_value = float(vm_row["Virtual Disk Size (MiB)"])
        expected_sum = float(
            pd.to_numeric(
                raw_disks[raw_disks["MOB ID"] == target_mob_id]["Capacity (MiB)"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        parsed = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        parsed_row = parsed[parsed["vm_name"].astype(str).str.strip() == vm_name].iloc[0]

        assert parsed_row["provisioned_mib"] == pytest.approx(expected_sum, rel=1e-6)
        # Regression assertion: disk-summed value should strictly exceed the
        # VMs-sheet primary-disk value for any VM that has additional disks
        # with positive capacity.
        if expected_sum > vms_sheet_value:
            assert parsed_row["provisioned_mib"] > vms_sheet_value

    def test_preserves_vms_sheet_metadata(self, liveoptics_xlsx_path: Path) -> None:
        """Cluster / OS / cpus / memory must come from VMs sheet, not be blanked
        by the disk override."""
        parsed = parse_liveoptics_xlsx(liveoptics_xlsx_path)
        assert parsed["cluster"].astype(str).str.len().sum() > 0
        assert parsed["os_name"].astype(str).str.len().sum() > 0
        assert (parsed["num_cpus"] > 0).any()
        assert (parsed["memory_mib"] > 0).any()


class TestParseLiveopticsXlsxFallback:
    """When the VM Disks sheet is absent (older exports, minimal fixtures),
    the parser must fall back to VMs-sheet values without raising."""

    def _build_xlsx_without_disks(self, tmp_path: Path) -> Path:
        path = tmp_path / "lo_no_disks.xlsx"
        vms = pd.DataFrame(
            {
                "VM Name": ["vm-a", "vm-b"],
                "VM OS": ["Ubuntu Linux", "Windows Server"],
                "Virtual Disk Size (MiB)": [1024.0, 2048.0],
                "Guest VM Disk Used (MiB)": [512.0, 1024.0],
                "Power State": ["poweredOn", "poweredOn"],
                "Virtual CPU": [2, 4],
                "Provisioned Memory (MiB)": [4096, 8192],
                "Datacenter": ["DC1", "DC1"],
                "Cluster": ["C1", "C1"],
            }
        )
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            vms.to_excel(writer, sheet_name="VMs", index=False)
        return path

    def test_no_vm_disks_sheet_uses_vms_sheet_values(self, tmp_path: Path) -> None:
        path = self._build_xlsx_without_disks(tmp_path)
        df = parse_liveoptics_xlsx(path)
        assert len(df) == 2
        # Values should equal raw VMs-sheet columns unchanged.
        assert sorted(df["provisioned_mib"].tolist()) == [1024.0, 2048.0]
        assert sorted(df["in_use_mib"].tolist()) == [512.0, 1024.0]

    def test_bundled_minimal_fixture_uses_fallback(self) -> None:
        """The checked-in 5-row fixture has no VM Disks sheet — ensure fallback."""
        fixture = Path(__file__).parent / "fixtures" / "live-optics.xlsx"
        df = parse_liveoptics_xlsx(fixture)
        assert len(df) == 5
        # Non-zero provisioned — came from VMs sheet, not from (absent) VM Disks.
        assert df["provisioned_mib"].sum() > 0
