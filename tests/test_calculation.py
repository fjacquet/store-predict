"""Tests for the calculation service (pipeline/calculation.py)."""

from __future__ import annotations

import pytest

from store_predict.pipeline.calculation import (
    calculate,
)


def _row(
    vm_name: str = "VM-1",
    workload_category: str = "Database/Microsoft SQL",
    provisioned_mib: float = 10000.0,
    in_use_mib: float = 5000.0,
    drr: float = 5.0,
) -> dict:
    """Helper to build a row dict matching session-state format."""
    return {
        "vm_name": vm_name,
        "workload_category": workload_category,
        "provisioned_mib": provisioned_mib,
        "in_use_mib": in_use_mib,
        "drr": drr,
    }


class TestSingleVM:
    """Single VM calculation."""

    def test_single_vm_calculation(self) -> None:
        rows = [_row(provisioned_mib=10000, drr=5.0)]
        result = calculate(rows)
        assert result.total_vms == 1
        assert len(result.vm_calculations) == 1
        vm = result.vm_calculations[0]
        assert vm.required_mib == pytest.approx(2000.0)
        assert vm.provisioned_mib == pytest.approx(10000.0)
        assert vm.drr == pytest.approx(5.0)

    def test_single_vm_single_group(self) -> None:
        rows = [_row(workload_category="VDI/Persistent Desktop")]
        result = calculate(rows)
        assert len(result.workload_groups) == 1
        grp = result.workload_groups[0]
        assert grp.category == "VDI/Persistent Desktop"
        assert grp.vm_count == 1


class TestMultipleVMs:
    """Multiple VM totals and weighted averages."""

    def test_multiple_vms_totals(self) -> None:
        rows = [
            _row(vm_name="A", provisioned_mib=10000, in_use_mib=5000, drr=5.0),
            _row(vm_name="B", provisioned_mib=20000, in_use_mib=8000, drr=2.0),
            _row(vm_name="C", provisioned_mib=5000, in_use_mib=3000, drr=10.0),
        ]
        result = calculate(rows)
        assert result.total_vms == 3
        assert result.total_provisioned_mib == pytest.approx(35000.0)
        assert result.total_in_use_mib == pytest.approx(16000.0)
        # required: 2000 + 10000 + 500 = 12500
        assert result.total_required_mib == pytest.approx(12500.0)

    def test_weighted_average_drr(self) -> None:
        rows = [
            _row(vm_name="A", provisioned_mib=10000, drr=5.0),
            _row(vm_name="B", provisioned_mib=20000, drr=2.0),
        ]
        result = calculate(rows)
        # required: 2000 + 10000 = 12000
        # weighted avg = 30000 / 12000 = 2.5
        assert result.weighted_avg_drr == pytest.approx(2.5)


class TestWorkloadGrouping:
    """Grouping VMs by workload category."""

    def test_workload_grouping(self) -> None:
        rows = [
            _row(vm_name="SQL-1", workload_category="Database/Microsoft SQL", provisioned_mib=10000, drr=5.0),
            _row(vm_name="SQL-2", workload_category="Database/Microsoft SQL", provisioned_mib=20000, drr=5.0),
            _row(vm_name="VDI-1", workload_category="VDI/Persistent Desktop", provisioned_mib=5000, drr=2.0),
            _row(vm_name="VDI-2", workload_category="VDI/Persistent Desktop", provisioned_mib=8000, drr=2.0),
        ]
        result = calculate(rows)
        assert len(result.workload_groups) == 2

        groups_by_cat = {g.category: g for g in result.workload_groups}

        sql_grp = groups_by_cat["Database/Microsoft SQL"]
        assert sql_grp.vm_count == 2
        assert sql_grp.total_provisioned_mib == pytest.approx(30000.0)
        assert sql_grp.total_required_mib == pytest.approx(6000.0)

        vdi_grp = groups_by_cat["VDI/Persistent Desktop"]
        assert vdi_grp.vm_count == 2
        assert vdi_grp.total_provisioned_mib == pytest.approx(13000.0)
        assert vdi_grp.total_required_mib == pytest.approx(6500.0)


class TestEdgeCases:
    """Edge cases: zero DRR, negative DRR, empty data, missing fields."""

    def test_drr_zero_guard(self) -> None:
        rows = [_row(drr=0)]
        result = calculate(rows)
        vm = result.vm_calculations[0]
        # max(0, 0.1) = 0.1  ->  10000 / 0.1 = 100000
        assert vm.required_mib == pytest.approx(100000.0)
        assert vm.drr == pytest.approx(0.1)

    def test_drr_negative_guard(self) -> None:
        rows = [_row(drr=-1)]
        result = calculate(rows)
        vm = result.vm_calculations[0]
        # max(-1, 0.1) = 0.1  ->  10000 / 0.1 = 100000
        assert vm.required_mib == pytest.approx(100000.0)
        assert vm.drr == pytest.approx(0.1)

    def test_empty_dataset(self) -> None:
        result = calculate([])
        assert result.total_vms == 0
        assert result.total_provisioned_mib == pytest.approx(0.0)
        assert result.total_in_use_mib == pytest.approx(0.0)
        assert result.total_required_mib == pytest.approx(0.0)
        assert result.weighted_avg_drr == pytest.approx(0.0)
        assert result.vm_calculations == []
        assert result.workload_groups == []

    def test_missing_fields_defaults(self) -> None:
        # Row dict missing all optional keys
        rows = [{"vm_name": "Bare"}]
        result = calculate(rows)
        vm = result.vm_calculations[0]
        assert vm.provisioned_mib == pytest.approx(0.0)
        assert vm.in_use_mib == pytest.approx(0.0)
        assert vm.drr == pytest.approx(5.0)
        assert vm.required_mib == pytest.approx(0.0)  # 0 / 5.0 = 0
        assert vm.workload_category == "Unknown (Reducible)"

    def test_large_dataset(self) -> None:
        rows = [_row(vm_name=f"VM-{i}", provisioned_mib=1000, in_use_mib=500, drr=5.0) for i in range(5000)]
        result = calculate(rows)
        assert result.total_vms == 5000
        assert result.total_provisioned_mib == pytest.approx(5_000_000.0)
        assert result.total_in_use_mib == pytest.approx(2_500_000.0)
        assert result.total_required_mib == pytest.approx(1_000_000.0)


class TestDataclasses:
    """Verify dataclass structure."""

    def test_vm_calculation_is_frozen(self) -> None:
        rows = [_row()]
        result = calculate(rows)
        with pytest.raises(AttributeError):
            result.vm_calculations[0].required_mib = 999  # type: ignore[misc]

    def test_calculation_summary_is_frozen(self) -> None:
        result = calculate([])
        with pytest.raises(AttributeError):
            result.total_vms = 999  # type: ignore[misc]
