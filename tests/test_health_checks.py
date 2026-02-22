"""Tests for pipeline/health_checks.py -- all check functions and sentinel guards."""

from __future__ import annotations

import pandas as pd

from store_predict.pipeline.health_checks import (
    HealthCheckResult,
    HealthFinding,
    Severity,
    run_health_checks,
)

# ---------------------------------------------------------------------------
# Test data builder
# ---------------------------------------------------------------------------


def _make_active_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal canonical DataFrame with one active, non-template VM.

    All fields have healthy defaults. Override any field to trigger a check.
    """
    defaults: dict[str, list[object]] = {
        "vm_name": ["test-vm-01"],
        "os_name": ["Windows Server 2022"],
        "workload_category": ["Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"],
        "provisioned_mib": [102400.0],
        "in_use_mib": [51200.0],
        "num_cpus": [4],
        "memory_mib": [8192.0],
        "datacenter": ["DC1"],
        "cluster": ["Cluster-01"],
        "is_powered_on": [True],
        "is_template": [False],
        "hw_version": [19],
        "tools_status": ["toolsOk"],
        "peak_iops": [500.0],
        "avg_iops": [300.0],
        "source_format": ["rvtools"],
        "row_index": [0],
    }
    for key, val in overrides.items():
        defaults[key] = val  # type: ignore[assignment]
    return pd.DataFrame(defaults)


def _get_ids(result: HealthCheckResult) -> set[str]:
    """Extract set of check_ids from a HealthCheckResult."""
    return {f.check_id for f in result.findings}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_none_input_returns_no_data(self) -> None:
        result = run_health_checks(None)
        assert result.has_data is False
        assert result.findings == ()
        assert result.total_vms_checked == 0

    def test_empty_dataframe_returns_no_data(self) -> None:
        result = run_health_checks(pd.DataFrame())
        assert result.has_data is False

    def test_healthy_vm_no_findings(self) -> None:
        """Default _make_active_df values should produce no findings."""
        df = _make_active_df()
        result = run_health_checks(df)
        ids = _get_ids(result)
        # The healthy default VM should not trigger any findings
        assert "data_quality.zero_provisioned" not in ids
        assert "data_quality.missing_os" not in ids
        assert "best_practice.very_old_hw_version" not in ids
        assert "best_practice.tools_not_installed" not in ids

    def test_result_has_data_when_vms_present(self) -> None:
        df = _make_active_df()
        result = run_health_checks(df)
        assert result.has_data is True
        assert result.total_vms_checked == 1

    def test_count_properties_correct(self) -> None:
        df = _make_active_df(provisioned_mib=[0.0], os_name=[""])
        result = run_health_checks(df)
        assert result.warning_count >= 2  # zero_provisioned + missing_os

    def test_result_is_health_check_result(self) -> None:
        df = _make_active_df()
        result = run_health_checks(df)
        assert isinstance(result, HealthCheckResult)

    def test_findings_is_tuple(self) -> None:
        df = _make_active_df()
        result = run_health_checks(df)
        assert isinstance(result.findings, tuple)


# ---------------------------------------------------------------------------
# Data quality checks (HLT-01)
# ---------------------------------------------------------------------------


class TestDataQualityChecks:
    def test_missing_os_triggers_warning(self) -> None:
        df = _make_active_df(os_name=[""])
        result = run_health_checks(df)
        assert "data_quality.missing_os" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_os")
        assert finding.severity == Severity.WARNING
        assert finding.affected_count == 1

    def test_present_os_no_finding(self) -> None:
        df = _make_active_df(os_name=["Ubuntu 22.04"])
        assert "data_quality.missing_os" not in _get_ids(run_health_checks(df))

    def test_whitespace_only_os_triggers_warning(self) -> None:
        """OS name with only whitespace should be treated as missing."""
        df = _make_active_df(os_name=["   "])
        assert "data_quality.missing_os" in _get_ids(run_health_checks(df))

    def test_zero_provisioned_triggers_warning(self) -> None:
        df = _make_active_df(provisioned_mib=[0.0])
        result = run_health_checks(df)
        assert "data_quality.zero_provisioned" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "data_quality.zero_provisioned")
        assert finding.severity == Severity.WARNING

    def test_nonzero_provisioned_no_finding(self) -> None:
        df = _make_active_df(provisioned_mib=[1024.0])
        assert "data_quality.zero_provisioned" not in _get_ids(run_health_checks(df))

    def test_zero_cpus_triggers_info(self) -> None:
        df = _make_active_df(num_cpus=[0])
        result = run_health_checks(df)
        assert "data_quality.missing_cpu" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_cpu")
        assert finding.severity == Severity.INFO

    def test_nonzero_cpus_no_finding(self) -> None:
        df = _make_active_df(num_cpus=[4])
        assert "data_quality.missing_cpu" not in _get_ids(run_health_checks(df))

    def test_zero_ram_triggers_info(self) -> None:
        df = _make_active_df(memory_mib=[0.0])
        result = run_health_checks(df)
        assert "data_quality.missing_ram" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_ram")
        assert finding.severity == Severity.INFO

    def test_nonzero_ram_no_finding(self) -> None:
        df = _make_active_df(memory_mib=[8192.0])
        assert "data_quality.missing_ram" not in _get_ids(run_health_checks(df))

    def test_high_powered_off_ratio_triggers_info(self) -> None:
        """40% powered-off (2/5) should trigger the ratio finding."""
        rows = []
        for i in range(3):
            rows.append(_make_active_df(vm_name=[f"vm-on-{i}"], is_powered_on=[True], is_template=[False]))
        for i in range(2):
            rows.append(_make_active_df(vm_name=[f"vm-off-{i}"], is_powered_on=[False], is_template=[False]))
        df = pd.concat(rows, ignore_index=True)
        result = run_health_checks(df)
        assert "data_quality.high_powered_off_ratio" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "data_quality.high_powered_off_ratio")
        assert finding.severity == Severity.INFO

    def test_low_powered_off_ratio_no_finding(self) -> None:
        """10% powered-off (1/10) should not trigger."""
        rows = [_make_active_df(vm_name=[f"vm-on-{i}"], is_powered_on=[True]) for i in range(9)]
        rows.append(_make_active_df(vm_name=["vm-off-0"], is_powered_on=[False]))
        df = pd.concat(rows, ignore_index=True)
        assert "data_quality.high_powered_off_ratio" not in _get_ids(run_health_checks(df))

    def test_powered_off_vms_excluded_from_active_checks(self) -> None:
        """Powered-off VM with zero provisioned should not trigger zero_provisioned."""
        df = _make_active_df(provisioned_mib=[0.0], is_powered_on=[False])
        assert "data_quality.zero_provisioned" not in _get_ids(run_health_checks(df))

    def test_template_vms_excluded_from_active_checks(self) -> None:
        """Template VM with zero provisioned should not trigger zero_provisioned."""
        df = _make_active_df(provisioned_mib=[0.0], is_template=[True])
        assert "data_quality.zero_provisioned" not in _get_ids(run_health_checks(df))


# ---------------------------------------------------------------------------
# Sizing risk checks (HLT-02)
# ---------------------------------------------------------------------------


class TestSizingRiskChecks:
    def test_high_unknown_ratio_triggers_warning(self) -> None:
        """5 Unknown out of 6 total active = 83% > 25% threshold."""
        rows = [
            _make_active_df(
                vm_name=[f"unknown-vm-{i}"],
                workload_category=["Unknown (Reducible)/Unknown (Reducible)"],
            )
            for i in range(5)
        ]
        rows.append(_make_active_df(vm_name=["known-vm-0"]))
        df = pd.concat(rows, ignore_index=True)
        result = run_health_checks(df)
        assert "sizing_risk.high_unknown_ratio" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "sizing_risk.high_unknown_ratio")
        assert finding.severity == Severity.WARNING

    def test_low_unknown_ratio_no_finding(self) -> None:
        """1 Unknown out of 10 total = 10% < 25% threshold."""
        rows = [_make_active_df(vm_name=[f"known-{i}"]) for i in range(9)]
        rows.append(
            _make_active_df(
                vm_name=["unknown-0"],
                workload_category=["Unknown (Reducible)/Unknown (Reducible)"],
            )
        )
        df = pd.concat(rows, ignore_index=True)
        assert "sizing_risk.high_unknown_ratio" not in _get_ids(run_health_checks(df))

    def test_large_unknown_vm_triggers_warning(self) -> None:
        """Unknown VM with provisioned >= 1 TiB (1048576 MiB) should trigger."""
        df = _make_active_df(
            workload_category=["Unknown (Reducible)/Unknown (Reducible)"],
            provisioned_mib=[1048576.0],  # exactly 1 TiB
        )
        result = run_health_checks(df)
        assert "sizing_risk.large_unknown_vms" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "sizing_risk.large_unknown_vms")
        assert finding.severity == Severity.WARNING

    def test_small_unknown_vm_no_finding(self) -> None:
        """Unknown VM with provisioned < 1 TiB should not trigger large_unknown."""
        df = _make_active_df(
            workload_category=["Unknown (Reducible)/Unknown (Reducible)"],
            provisioned_mib=[102400.0],  # 100 GiB, well below 1 TiB
        )
        assert "sizing_risk.large_unknown_vms" not in _get_ids(run_health_checks(df))

    def test_known_large_vm_no_finding(self) -> None:
        """Large VM with known workload category should not trigger large_unknown."""
        df = _make_active_df(
            workload_category=["Database/Microsoft SQL"],
            provisioned_mib=[2097152.0],  # 2 TiB
        )
        assert "sizing_risk.large_unknown_vms" not in _get_ids(run_health_checks(df))

    def test_iops_budget_exceeded_triggers_warning(self) -> None:
        """VM with peak_iops > 100_000 should trigger iops_budget_exceeded."""
        df = _make_active_df(peak_iops=[150000.0])
        result = run_health_checks(df)
        assert "sizing_risk.iops_budget_exceeded" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "sizing_risk.iops_budget_exceeded")
        assert finding.severity == Severity.WARNING

    def test_zero_iops_not_flagged(self) -> None:
        """VMs with peak_iops == 0 (no data) should not trigger iops finding."""
        df = _make_active_df(peak_iops=[0.0])
        assert "sizing_risk.iops_budget_exceeded" not in _get_ids(run_health_checks(df))

    def test_normal_iops_not_flagged(self) -> None:
        df = _make_active_df(peak_iops=[5000.0])
        assert "sizing_risk.iops_budget_exceeded" not in _get_ids(run_health_checks(df))

    def test_iops_at_exactly_budget_not_flagged(self) -> None:
        """peak_iops exactly at budget (100_000) should NOT trigger (must be strictly greater)."""
        df = _make_active_df(peak_iops=[100000.0])
        assert "sizing_risk.iops_budget_exceeded" not in _get_ids(run_health_checks(df))


# ---------------------------------------------------------------------------
# VMware best practice checks (HLT-03)
# ---------------------------------------------------------------------------


class TestBestPracticeChecks:
    def test_no_cluster_triggers_warning(self) -> None:
        df = _make_active_df(cluster=[""])
        result = run_health_checks(df)
        assert "best_practice.no_cluster" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "best_practice.no_cluster")
        assert finding.severity == Severity.WARNING

    def test_with_cluster_no_finding(self) -> None:
        df = _make_active_df(cluster=["Cluster-01"])
        assert "best_practice.no_cluster" not in _get_ids(run_health_checks(df))

    def test_very_old_hw_version_triggers_critical(self) -> None:
        """HW version 11 (ESXi 6.0) is below vHW 14 -- Critical."""
        df = _make_active_df(hw_version=[11])
        result = run_health_checks(df)
        assert "best_practice.very_old_hw_version" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "best_practice.very_old_hw_version")
        assert finding.severity == Severity.CRITICAL

    def test_old_hw_version_triggers_warning(self) -> None:
        """HW version 14 (ESXi 6.7) is below vHW 17 but >= vHW 14 -- Warning."""
        df = _make_active_df(hw_version=[14])
        result = run_health_checks(df)
        assert "best_practice.old_hw_version" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "best_practice.old_hw_version")
        assert finding.severity == Severity.WARNING

    def test_hw_version_16_triggers_warning(self) -> None:
        """HW version 16 (ESXi 7.0 GA) is still below vHW 17 -- Warning."""
        df = _make_active_df(hw_version=[16])
        result = run_health_checks(df)
        assert "best_practice.old_hw_version" in _get_ids(result)

    def test_current_hw_version_no_finding(self) -> None:
        """HW version 19 (ESXi 7.0U2+) should not trigger any HW finding."""
        df = _make_active_df(hw_version=[19])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.old_hw_version" not in ids
        assert "best_practice.very_old_hw_version" not in ids

    def test_hw_version_zero_sentinel_skipped(self) -> None:
        """hw_version=0 means data not available -- must NOT trigger any HW findings."""
        df = _make_active_df(hw_version=[0], source_format=["liveoptics"])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.old_hw_version" not in ids
        assert "best_practice.very_old_hw_version" not in ids

    def test_hw_version_zero_all_vms_sentinel_skipped(self) -> None:
        """All VMs with hw_version=0 (entire LiveOptics export) must produce no HW findings."""
        rows = [_make_active_df(vm_name=[f"vm-{i}"], hw_version=[0], source_format=["liveoptics"]) for i in range(5)]
        df = pd.concat(rows, ignore_index=True)
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.old_hw_version" not in ids
        assert "best_practice.very_old_hw_version" not in ids

    def test_powered_off_vms_not_flagged_for_hw(self) -> None:
        """Powered-off VMs must not be included in hardware version check."""
        df = _make_active_df(hw_version=[11], is_powered_on=[False])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.very_old_hw_version" not in ids

    def test_template_vms_not_flagged_for_hw(self) -> None:
        """Template VMs must not be included in hardware version check."""
        df = _make_active_df(hw_version=[11], is_template=[True])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.very_old_hw_version" not in ids

    def test_tools_not_installed_triggers_critical(self) -> None:
        df = _make_active_df(tools_status=["toolsNotInstalled"])
        result = run_health_checks(df)
        assert "best_practice.tools_not_installed" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "best_practice.tools_not_installed")
        assert finding.severity == Severity.CRITICAL

    def test_tools_not_running_triggers_warning(self) -> None:
        df = _make_active_df(tools_status=["toolsNotRunning"])
        result = run_health_checks(df)
        assert "best_practice.tools_not_running" in _get_ids(result)
        finding = next(f for f in result.findings if f.check_id == "best_practice.tools_not_running")
        assert finding.severity == Severity.WARNING

    def test_tools_ok_no_finding(self) -> None:
        df = _make_active_df(tools_status=["toolsOk"])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.tools_not_installed" not in ids
        assert "best_practice.tools_not_running" not in ids

    def test_tools_old_no_finding(self) -> None:
        """toolsOld is not flagged -- only notInstalled/notRunning are concerns."""
        df = _make_active_df(tools_status=["toolsOld"])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.tools_not_installed" not in ids
        assert "best_practice.tools_not_running" not in ids

    def test_empty_tools_status_skipped(self) -> None:
        """Empty tools_status (LiveOptics or RVTools without column) must not trigger tools findings."""
        df = _make_active_df(tools_status=[""], source_format=["liveoptics"])
        ids = _get_ids(run_health_checks(df))
        assert "best_practice.tools_not_installed" not in ids
        assert "best_practice.tools_not_running" not in ids

    def test_very_old_hw_suppresses_old_hw_finding(self) -> None:
        """When very_old_hw_version fires, old_hw_version must NOT also fire."""
        df = _make_active_df(hw_version=[11])
        ids = _get_ids(run_health_checks(df))
        # very_old fires, old does NOT (avoids duplicate)
        assert "best_practice.very_old_hw_version" in ids
        assert "best_practice.old_hw_version" not in ids


# ---------------------------------------------------------------------------
# affected_vms sampling
# ---------------------------------------------------------------------------


class TestAffectedVms:
    def test_affected_vms_capped_at_five(self) -> None:
        """findings.affected_vms must contain at most 5 VM names."""
        rows = [_make_active_df(vm_name=[f"vm-missing-os-{i}"], os_name=[""]) for i in range(10)]
        df = pd.concat(rows, ignore_index=True)
        result = run_health_checks(df)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_os")
        assert len(finding.affected_vms) <= 5
        assert finding.affected_count == 10  # full count reported

    def test_affected_vms_is_tuple(self) -> None:
        """affected_vms must be a tuple (HealthFinding is frozen dataclass)."""
        df = _make_active_df(os_name=[""])
        result = run_health_checks(df)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_os")
        assert isinstance(finding.affected_vms, tuple)

    def test_affected_count_matches_actual_bad_vms(self) -> None:
        """affected_count must match the actual number of affected VMs."""
        rows = [_make_active_df(vm_name=[f"vm-no-cpu-{i}"], num_cpus=[0]) for i in range(3)]
        df = pd.concat(rows, ignore_index=True)
        result = run_health_checks(df)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_cpu")
        assert finding.affected_count == 3

    def test_health_finding_is_frozen_dataclass(self) -> None:
        """HealthFinding must be immutable (frozen dataclass)."""
        df = _make_active_df(os_name=[""])
        result = run_health_checks(df)
        finding = next(f for f in result.findings if f.check_id == "data_quality.missing_os")
        assert isinstance(finding, HealthFinding)
        # frozen dataclass should raise on attribute assignment
        import pytest

        with pytest.raises((AttributeError, TypeError)):
            finding.affected_count = 999  # type: ignore[misc]
