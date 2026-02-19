"""Tests for enhanced calculation features: VM statistics and performance totals.

Uses real objects, no mocks.
"""

from __future__ import annotations

import pytest

from store_predict.pipeline.calculation import calculate


def _row(
    vm_name: str = "VM-1",
    workload_category: str = "Database/Microsoft SQL",
    provisioned_mib: float = 10000.0,
    in_use_mib: float = 5000.0,
    drr: float = 5.0,
    **kwargs: object,
) -> dict:
    """Build a row dict matching session-state format."""
    base = {
        "vm_name": vm_name,
        "workload_category": workload_category,
        "provisioned_mib": provisioned_mib,
        "in_use_mib": in_use_mib,
        "drr": drr,
    }
    base.update(kwargs)
    return base


class TestCalculationVMStats:
    """Tests for VM statistics in CalculationSummary."""

    def test_calculation_has_vm_stats(self) -> None:
        """Calculate returns correct avg_vm_size_mib and largest VM info."""
        rows = [
            _row(vm_name="Small-VM", provisioned_mib=1000.0),
            _row(vm_name="Medium-VM", provisioned_mib=5000.0),
            _row(vm_name="Large-VM", provisioned_mib=15000.0),
        ]
        summary = calculate(rows)

        total_prov = 1000.0 + 5000.0 + 15000.0
        assert summary.total_vms == 3
        assert summary.avg_vm_size_mib == pytest.approx(total_prov / 3, rel=1e-6)
        assert summary.largest_vm_name == "Large-VM"
        assert summary.largest_vm_provisioned_mib == pytest.approx(15000.0)


class TestCalculationPerformance:
    """Tests for performance totals in CalculationSummary."""

    def test_calculation_with_performance_data(self) -> None:
        """Calculate with performance fields sets has_performance_data and totals."""
        rows = [
            _row(
                vm_name="Perf-VM-1",
                peak_iops=500.0,
                avg_iops=200.0,
                peak_throughput_mbs=100.0,
                iops_8k_equivalent=250.0,
            ),
            _row(
                vm_name="Perf-VM-2",
                peak_iops=300.0,
                avg_iops=150.0,
                peak_throughput_mbs=80.0,
                iops_8k_equivalent=180.0,
            ),
        ]
        summary = calculate(rows)

        assert summary.has_performance_data is True
        assert summary.total_peak_iops == pytest.approx(800.0)
        assert summary.total_avg_iops == pytest.approx(350.0)
        assert summary.peak_throughput_mbs == pytest.approx(100.0)  # max, not sum
        assert summary.total_iops_8k_equivalent == pytest.approx(430.0)

    def test_calculation_without_performance_data(self) -> None:
        """Calculate without performance fields sets has_performance_data=False."""
        rows = [_row(vm_name="No-Perf-VM")]
        summary = calculate(rows)

        assert summary.has_performance_data is False
        assert summary.total_peak_iops == pytest.approx(0.0)
        assert summary.total_avg_iops == pytest.approx(0.0)

    def test_calculation_empty_data(self) -> None:
        """Empty row_data produces sensible defaults for all new fields."""
        summary = calculate([])

        assert summary.total_vms == 0
        assert summary.avg_vm_size_mib == pytest.approx(0.0)
        assert summary.largest_vm_name == ""
        assert summary.largest_vm_provisioned_mib == pytest.approx(0.0)
        assert summary.has_performance_data is False
        assert summary.total_peak_iops == pytest.approx(0.0)
        assert summary.peak_throughput_mbs == pytest.approx(0.0)
