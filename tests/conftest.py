"""Shared test fixtures."""

from collections.abc import Callable
from pathlib import Path

import pytest

from store_predict.config import DRR_CSV_PATH
from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services.drr_table import DRRTable

_SAMPLES_DIR = Path(__file__).parent.parent / "samples"


@pytest.fixture
def sample_drr_path() -> Path:
    """Path to DRR.csv — uses package data (always available)."""
    return DRR_CSV_PATH


@pytest.fixture
def drr_table(sample_drr_path: Path) -> DRRTable:
    """DRRTable loaded from the real DRR.csv."""
    return DRRTable.from_csv(sample_drr_path)


@pytest.fixture
def rvtools_path() -> Path:
    """Path to the real RVTools xlsx sample file (customer data, local only)."""
    p = _SAMPLES_DIR / "rvtools.xlsx"
    if not p.exists():
        pytest.skip("samples/rvtools.xlsx not available (customer data)")
    return p


@pytest.fixture
def liveoptics_xlsx_path() -> Path:
    """Path to the real LiveOptics xlsx sample file (customer data, local only)."""
    p = _SAMPLES_DIR / "live-optics.xlsx"
    if not p.exists():
        pytest.skip("samples/live-optics.xlsx not available (customer data)")
    return p


@pytest.fixture
def liveoptics_csv_path() -> Path:
    """Path to the LiveOptics CSV test fixture."""
    return Path(__file__).parent / "fixtures" / "liveoptics_sample.csv"


@pytest.fixture
def make_summary() -> Callable[[], CalculationSummary]:
    """Factory fixture that returns a callable producing a minimal CalculationSummary.

    Returns a zero-argument factory so tests can call ``make_summary()`` to
    get a fresh CalculationSummary with realistic data. Uses real objects only
    (no mocks), consistent with project conventions.
    """

    def _factory() -> CalculationSummary:
        vm_calcs = [
            VMCalculation(
                vm_name=f"VM-{i}",
                workload_category="Database/Microsoft SQL",
                provisioned_mib=10240.0,
                in_use_mib=5120.0,
                drr=5.0,
                required_mib=2048.0,
            )
            for i in range(3)
        ]
        groups = [
            WorkloadGroupResult(
                category="Database/Microsoft SQL",
                vm_count=3,
                total_provisioned_mib=30720.0,
                total_in_use_mib=15360.0,
                avg_drr=5.0,
                total_required_mib=6144.0,
            )
        ]
        return CalculationSummary(
            vm_calculations=vm_calcs,
            workload_groups=groups,
            total_vms=3,
            total_provisioned_mib=30720.0,
            total_in_use_mib=15360.0,
            total_required_mib=6144.0,
            weighted_avg_drr=5.0,
            avg_vm_size_mib=10240.0,
            avg_vm_cpus=4.0,
            avg_vm_memory_mib=8192.0,
            total_cpus=12,
            total_memory_mib=24576.0,
            largest_vm_name="VM-0",
            largest_vm_provisioned_mib=10240.0,
            has_performance_data=False,
        )

    return _factory
