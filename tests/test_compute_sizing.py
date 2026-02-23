"""Tests for pipeline/compute_sizing.py -- all sizing functions and edge cases."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from store_predict.pipeline.compute_sizing import (
    DELL_POWEREDGE_PRESETS,
    ClusterSizingRow,
    ComputeSizingResult,
    HostConfig,
    compute_cluster_breakdown,
    compute_sizing,
)

# ---------------------------------------------------------------------------
# Test data builder
# ---------------------------------------------------------------------------


def _make_active_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal canonical DataFrame with one active, non-template VM.

    All fields have healthy defaults. Override any field to trigger a scenario.
    """
    defaults: dict[str, list[object]] = {
        "vm_name": ["test-vm-01"],
        "num_cpus": [4],
        "memory_mib": [8192.0],
        "datacenter": ["DC1"],
        "is_powered_on": [True],
        "is_template": [False],
    }
    for key, val in overrides.items():
        defaults[key] = val  # type: ignore[assignment]
    return pd.DataFrame(defaults)


# ---------------------------------------------------------------------------
# Helper presets for tests
# ---------------------------------------------------------------------------

_R760 = HostConfig(name="R760 (2x28c / 512 GiB)", cores_per_socket=28, sockets=2, ram_gib=512)
_CUSTOM_SMALL = HostConfig(name="Custom", cores_per_socket=2, sockets=1, ram_gib=16)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_none_df_returns_no_data(self) -> None:
        result = compute_sizing(None, _R760)
        assert result.has_data is False
        assert result.total_active_vcpus == 0
        assert result.total_active_ram_gib == 0.0
        assert result.hosts_n1 == 0
        assert result.hosts_by_vcpu == 0
        assert result.hosts_by_ram == 0

    def test_empty_df_returns_no_data(self) -> None:
        result = compute_sizing(pd.DataFrame(), _R760)
        assert result.has_data is False

    def test_zero_cpu_zero_ram_returns_no_data(self) -> None:
        df = _make_active_df(num_cpus=[0], memory_mib=[0])
        result = compute_sizing(df, _R760)
        assert result.has_data is False

    def test_all_powered_off_returns_no_data(self) -> None:
        df = _make_active_df(is_powered_on=[False])
        result = compute_sizing(df, _R760)
        assert result.has_data is False
        assert result.excluded_vm_count == 1

    def test_template_excluded(self) -> None:
        df = _make_active_df(is_template=[True])
        result = compute_sizing(df, _R760)
        assert result.has_data is False
        assert result.excluded_vm_count == 1

    def test_powered_off_and_template_count(self) -> None:
        """3 VMs: 1 active + 1 powered-off + 1 template -> excluded_vm_count=2."""
        rows = [
            _make_active_df(vm_name=["active-01"], is_powered_on=[True], is_template=[False]),
            _make_active_df(vm_name=["off-01"], is_powered_on=[False], is_template=[False]),
            _make_active_df(vm_name=["tmpl-01"], is_powered_on=[True], is_template=[True]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_sizing(df, _R760)
        assert result.excluded_vm_count == 2


# ---------------------------------------------------------------------------
# TestN1Formula
# ---------------------------------------------------------------------------


class TestN1Formula:
    def test_basic_n1_host_count(self) -> None:
        """100 vCPUs, R760 (56 physical cores), ratio=4.0 -> ceil(100/(56*4))+1 = 2."""
        df = _make_active_df(num_cpus=[100], memory_mib=[1024.0])
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        expected = math.ceil(100 / (56 * 4.0)) + 1
        assert result.hosts_by_vcpu == expected
        assert result.has_data is True

    def test_n1_with_large_workload(self) -> None:
        """1000 vCPUs, R760 (56 cores), ratio=4.0 -> ceil(1000/224)+1 = 6."""
        df = _make_active_df(num_cpus=[1000], memory_mib=[1024.0])
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        expected = math.ceil(1000 / (56 * 4.0)) + 1
        assert result.hosts_by_vcpu == expected

    def test_n1_minimum_one_host_plus_one(self) -> None:
        """1 vCPU, R760, ratio=4.0 -> ceil(1/224)+1 = 2 (1 working + 1 HA)."""
        df = _make_active_df(num_cpus=[1], memory_mib=[1024.0])
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        assert result.hosts_by_vcpu == 2

    def test_hosts_n1_field_equals_max_constraint(self) -> None:
        """hosts_n1 must always equal max(hosts_by_vcpu, hosts_by_ram)."""
        df = _make_active_df(num_cpus=[100], memory_mib=[8192.0])
        result = compute_sizing(df, _R760)
        assert result.hosts_n1 == max(result.hosts_by_vcpu, result.hosts_by_ram)


# ---------------------------------------------------------------------------
# TestRAMConstraint
# ---------------------------------------------------------------------------


class TestRAMConstraint:
    def test_ram_binding_constraint(self) -> None:
        """4 vCPUs (tiny CPU load), 400_000 MiB RAM with R760 (512 GiB RAM) -> RAM binds."""
        # 400_000 MiB = 390.6 GiB -> ceil(390.6/512)+1 = 2
        # 4 vCPUs / (56 * 4) = 0.018 -> ceil=1 -> +1 = 2... but try with more RAM
        # Use 800_000 MiB = 781.25 GiB -> ceil(781.25/512)+1 = 3
        # 4 vCPUs -> ceil(4/224)+1 = 2
        df = _make_active_df(num_cpus=[4], memory_mib=[800_000.0])
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        # RAM hosts: ceil(781.25/512)+1 = ceil(1.526)+1 = 2+1 = 3
        # vCPU hosts: ceil(4/224)+1 = 1+1 = 2
        assert result.hosts_by_ram > result.hosts_by_vcpu
        assert result.hosts_n1 == result.hosts_by_ram

    def test_vcpu_binding_constraint(self) -> None:
        """10000 vCPUs, 1024 MiB RAM with R760 -> vCPU binds."""
        df = _make_active_df(num_cpus=[10000], memory_mib=[1024.0])
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        # vCPU hosts: ceil(10000/224)+1 = 45+1 = 46
        # RAM hosts: ceil(1/512)+1 = 1+1 = 2
        assert result.hosts_by_vcpu > result.hosts_by_ram
        assert result.hosts_n1 == result.hosts_by_vcpu


# ---------------------------------------------------------------------------
# TestOvercommitClamping
# ---------------------------------------------------------------------------


class TestOvercommitClamping:
    def test_overcommit_clamp_below_minimum(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=0.0)
        assert result.overcommit_ratio == 0.5

    def test_overcommit_clamp_above_maximum(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=99.0)
        assert result.overcommit_ratio == 20.0

    def test_overcommit_negative_clamped(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=-5.0)
        assert result.overcommit_ratio == 0.5

    def test_overcommit_within_bounds_unchanged(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=4.0)
        assert result.overcommit_ratio == 4.0

    def test_overcommit_boundary_low(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=0.5)
        assert result.overcommit_ratio == 0.5

    def test_overcommit_boundary_high(self) -> None:
        df = _make_active_df()
        result = compute_sizing(df, _R760, overcommit_ratio=20.0)
        assert result.overcommit_ratio == 20.0


# ---------------------------------------------------------------------------
# TestVMSC
# ---------------------------------------------------------------------------


class TestVMSC:
    def test_vmsc_unavailable_single_datacenter(self) -> None:
        """All VMs in DC1 -> vmsc_available=False, vmsc_site_a_hosts=0, vmsc_site_b_hosts=0."""
        df = _make_active_df(datacenter=["DC1"])
        result = compute_sizing(df, _R760, vmsc_enabled=True)
        assert result.vmsc_available is False
        assert result.vmsc_site_a_hosts == 0
        assert result.vmsc_site_b_hosts == 0

    def test_vmsc_unavailable_empty_datacenter(self) -> None:
        """Empty datacenter string -> vmsc_available=False."""
        df = _make_active_df(datacenter=[""])
        result = compute_sizing(df, _R760, vmsc_enabled=True)
        assert result.vmsc_available is False

    def test_vmsc_unavailable_no_datacenter_column(self) -> None:
        """DataFrame without datacenter column -> vmsc_available=False."""
        df = pd.DataFrame(
            {
                "vm_name": ["vm-01"],
                "num_cpus": [4],
                "memory_mib": [8192.0],
                "is_powered_on": [True],
                "is_template": [False],
            }
        )
        result = compute_sizing(df, _R760, vmsc_enabled=True)
        assert result.vmsc_available is False

    def test_vmsc_available_two_datacenters(self) -> None:
        """Two distinct datacenters -> vmsc_available=True, len(vmsc_sites)==2."""
        rows = [
            _make_active_df(vm_name=["vm-dc1"], datacenter=["DC1"]),
            _make_active_df(vm_name=["vm-dc2"], datacenter=["DC2"]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_sizing(df, _R760)
        assert result.vmsc_available is True
        assert len(result.vmsc_sites) == 2

    def test_vmsc_disabled_no_per_site_count(self) -> None:
        """vmsc_available=True but vmsc_enabled=False -> vmsc_site_a_hosts=vmsc_site_b_hosts=0."""
        rows = [
            _make_active_df(vm_name=["vm-dc1"], datacenter=["DC1"]),
            _make_active_df(vm_name=["vm-dc2"], datacenter=["DC2"]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_sizing(df, _R760, vmsc_enabled=False)
        assert result.vmsc_available is True
        assert result.vmsc_site_a_hosts == 0
        assert result.vmsc_site_b_hosts == 0

    def test_vmsc_enabled_returns_per_site_count(self) -> None:
        """vmsc_available=True + vmsc_enabled=True -> vmsc_site_a_hosts > 0 and vmsc_site_b_hosts > 0."""
        rows = [
            _make_active_df(vm_name=["vm-dc1"], datacenter=["DC1"]),
            _make_active_df(vm_name=["vm-dc2"], datacenter=["DC2"]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_sizing(df, _R760, vmsc_enabled=True)
        assert result.vmsc_available is True
        assert result.vmsc_site_a_hosts > 0
        assert result.vmsc_site_b_hosts > 0


# ---------------------------------------------------------------------------
# TestActivePAssive
# ---------------------------------------------------------------------------


class TestActivePassive:
    def _get_result_with_hosts_n1(self, target_hosts_n1: int) -> ComputeSizingResult:
        """Build a scenario where hosts_n1 is approximately target_hosts_n1.

        Uses a custom small host config to make the arithmetic controllable.
        """
        # With CUSTOM_SMALL: 2 cores/socket * 1 socket = 2 pCPUs, ratio=4.0 -> capacity=8
        # To get hosts_n1 = N: need total_vcpus such that ceil(vcpus/8)+1 = N
        # i.e. vcpus = 8*(N-2) + 1  (to ensure ceil rounds up to N-1)
        # Example: N=10 -> vcpus = 65 -> ceil(65/8)+1 = 9+1 = 10
        # N=9 -> vcpus = 57 -> ceil(57/8)+1 = 8+1 = 9
        # N=1 -> use just 1 vCPU -> ceil(1/8)+1 = 2... use tiny RAM to keep RAM from binding
        vcpus = 1 if target_hosts_n1 == 1 else 8 * (target_hosts_n1 - 2) + 1
        df = _make_active_df(num_cpus=[vcpus], memory_mib=[1.0])  # tiny RAM to avoid RAM binding
        return compute_sizing(df, _CUSTOM_SMALL, overcommit_ratio=4.0)

    def test_ap_secondary_is_half_of_primary(self) -> None:
        """hosts_n1=10 -> ap_secondary_hosts=5."""
        result = self._get_result_with_hosts_n1(10)
        assert result.hosts_n1 == 10
        assert result.ap_secondary_hosts == 5

    def test_ap_secondary_rounds_up(self) -> None:
        """hosts_n1=9 -> ap_secondary_hosts=5 (ceil(9/2)=5)."""
        result = self._get_result_with_hosts_n1(9)
        assert result.hosts_n1 == 9
        assert result.ap_secondary_hosts == math.ceil(9 / 2)

    def test_ap_secondary_minimum_one(self) -> None:
        """hosts_n1=2 (minimum possible) -> ap_secondary_hosts=1 (max(1, ceil(2/2)))."""
        df = _make_active_df(num_cpus=[1], memory_mib=[1.0])
        result = compute_sizing(df, _CUSTOM_SMALL, overcommit_ratio=4.0)
        # ceil(1/8)+1 = 2 hosts_n1
        assert result.ap_secondary_hosts == max(1, math.ceil(result.hosts_n1 / 2))
        assert result.ap_secondary_hosts >= 1

    def test_ap_primary_equals_hosts_n1_when_full_ratio(self) -> None:
        """ap_active_ratio=1.0 (default) -> ap_primary_hosts equals hosts_n1."""
        df = _make_active_df(num_cpus=[100], memory_mib=[8192.0])
        result = compute_sizing(df, _R760, ap_active_ratio=1.0)
        assert result.ap_primary_hosts == result.hosts_n1


# ---------------------------------------------------------------------------
# TestPresets
# ---------------------------------------------------------------------------


class TestPresets:
    def test_all_presets_importable(self) -> None:
        # Count is driven by compute_presets.csv — verify at least the minimum set
        assert len(DELL_POWEREDGE_PRESETS) >= 6
        assert any(p.cores_per_socket > 0 for p in DELL_POWEREDGE_PRESETS)

    def test_r7725_preset_exists_not_r7275(self) -> None:
        names = [p.name for p in DELL_POWEREDGE_PRESETS]
        assert any("R7725" in n for n in names), "R7725 preset not found"
        assert not any("R7275" in n for n in names), "R7275 typo found in presets"

    def test_custom_preset_last(self) -> None:
        assert DELL_POWEREDGE_PRESETS[-1].name == "Custom"

    def test_host_config_total_cores_property(self) -> None:
        hc = HostConfig(name="test", cores_per_socket=28, sockets=2, ram_gib=512)
        assert hc.total_cores == 56

    def test_host_config_total_ram_mib_property(self) -> None:
        hc = HostConfig(name="test", cores_per_socket=28, sockets=2, ram_gib=512)
        assert hc.total_ram_mib == 524288.0

    def test_all_presets_have_positive_specs(self) -> None:
        """All presets must have positive cores, sockets, and RAM."""
        for preset in DELL_POWEREDGE_PRESETS:
            assert preset.cores_per_socket > 0, f"{preset.name}: cores_per_socket must be > 0"
            assert preset.sockets > 0, f"{preset.name}: sockets must be > 0"
            assert preset.ram_gib > 0, f"{preset.name}: ram_gib must be > 0"
            assert preset.total_cores > 0, f"{preset.name}: total_cores must be > 0"

    def test_host_config_is_frozen(self) -> None:
        """HostConfig is a frozen dataclass — attribute assignment must raise."""
        hc = HostConfig(name="test", cores_per_socket=28, sockets=2, ram_gib=512)
        with pytest.raises((AttributeError, TypeError)):
            hc.cores_per_socket = 64  # type: ignore[misc]

    def test_compute_result_is_frozen(self) -> None:
        """ComputeSizingResult is a frozen dataclass — attribute assignment must raise."""
        df = _make_active_df()
        result = compute_sizing(df, _R760)
        with pytest.raises((AttributeError, TypeError)):
            result.hosts_n1 = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestMemoryMibSessionRoundTrip
# ---------------------------------------------------------------------------


class TestMemoryMibSessionRoundTrip:
    def test_none_memory_mib_handled(self) -> None:
        """memory_mib=[None] simulates session round-trip — must not raise, total_ram==0."""
        df = _make_active_df(memory_mib=[None])
        result = compute_sizing(df, _R760)
        assert result.total_active_ram_gib == 0.0

    def test_mixed_none_and_float_memory(self) -> None:
        """memory_mib=[8192.0, None] — must aggregate correctly without error."""
        rows = [
            _make_active_df(vm_name=["vm-01"], memory_mib=[8192.0]),
            _make_active_df(vm_name=["vm-02"], memory_mib=[None]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_sizing(df, _R760)
        # Only 8192.0 MiB should count -> 8.0 GiB
        assert result.total_active_ram_gib == pytest.approx(8.0, rel=1e-6)

    def test_none_num_cpus_handled(self) -> None:
        """num_cpus=[None] simulates session round-trip — must not raise, total_vcpus==0."""
        df = _make_active_df(num_cpus=[None])
        result = compute_sizing(df, _R760)
        assert result.total_active_vcpus == 0


# ---------------------------------------------------------------------------
# TestClusterBreakdown
# ---------------------------------------------------------------------------


class TestClusterBreakdown:
    def test_cluster_breakdown_empty_df_returns_empty(self) -> None:
        """None and empty DataFrame should both return []."""
        assert compute_cluster_breakdown(None, _R760) == []
        assert compute_cluster_breakdown(pd.DataFrame(), _R760) == []

    def test_cluster_breakdown_single_cluster(self) -> None:
        """3 VMs in ClusterA -> one ClusterSizingRow with vm_count=3."""
        rows = [
            _make_active_df(vm_name=[f"vm-{i}"], cluster=["ClusterA"]) for i in range(3)
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_cluster_breakdown(df, _R760)
        assert len(result) == 1
        assert result[0].cluster_name == "ClusterA"
        assert result[0].vm_count == 3

    def test_cluster_breakdown_two_clusters(self) -> None:
        """2 VMs in ClusterA, 1 VM in ClusterB -> 2 rows sorted alphabetically."""
        rows = [
            _make_active_df(vm_name=["vm-a1"], cluster=["ClusterA"]),
            _make_active_df(vm_name=["vm-a2"], cluster=["ClusterA"]),
            _make_active_df(vm_name=["vm-b1"], cluster=["ClusterB"]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_cluster_breakdown(df, _R760)
        assert len(result) == 2
        assert result[0].cluster_name == "ClusterA"
        assert result[1].cluster_name == "ClusterB"
        assert result[0].vm_count == 2
        assert result[1].vm_count == 1

    def test_cluster_breakdown_no_cluster_vms(self) -> None:
        """VMs with empty cluster string -> grouped under __no_cluster__."""
        df = _make_active_df(cluster=[""])
        result = compute_cluster_breakdown(df, _R760)
        assert len(result) == 1
        assert result[0].cluster_name == "__no_cluster__"

    def test_cluster_breakdown_excludes_powered_off(self) -> None:
        """Powered-off VMs must not be counted in breakdown."""
        rows = [
            _make_active_df(vm_name=["active-vm"], cluster=["ClusterA"], is_powered_on=[True]),
            _make_active_df(vm_name=["off-vm"], cluster=["ClusterA"], is_powered_on=[False]),
        ]
        df = pd.concat(rows, ignore_index=True)
        result = compute_cluster_breakdown(df, _R760)
        assert len(result) == 1
        assert result[0].vm_count == 1  # only active VM counted

    def test_cluster_breakdown_hosts_formula(self) -> None:
        """hosts_needed = max(_hosts_n1(...), _hosts_by_ram(...)) for known values."""
        import math

        # 8 vCPUs, 8192 MiB RAM, R760 (56 cores, 512 GiB RAM), ratio=4.0
        # hv = ceil(8 / (56*4)) + 1 = ceil(0.036) + 1 = 1 + 1 = 2
        # hr = ceil(8/512) + 1 = 1 + 1 = 2
        # hosts_needed = max(2, 2) = 2
        df = _make_active_df(num_cpus=[8], memory_mib=[8192.0], cluster=["ClusterA"])
        result = compute_cluster_breakdown(df, _R760)
        assert len(result) == 1
        expected_hv = math.ceil(8 / (56 * 4.0)) + 1
        expected_hr = math.ceil(8.0 / 1024.0 / 512) + 1
        expected_hosts = max(expected_hv, expected_hr)
        assert result[0].hosts_needed == expected_hosts

    def test_cluster_breakdown_returns_cluster_sizing_rows(self) -> None:
        """Return type elements must be ClusterSizingRow instances."""
        df = _make_active_df(cluster=["ClusterA"])
        result = compute_cluster_breakdown(df, _R760)
        assert all(isinstance(r, ClusterSizingRow) for r in result)

    def test_cluster_breakdown_all_powered_off_returns_empty(self) -> None:
        """All powered-off VMs -> empty result (no active rows)."""
        df = _make_active_df(is_powered_on=[False], cluster=["ClusterA"])
        result = compute_cluster_breakdown(df, _R760)
        assert result == []
