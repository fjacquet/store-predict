"""Calculation service: per-VM required capacity, workload group subtotals, and totals.

Pure pipeline module with zero UI imports.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

__all__ = [
    "CalculationSummary",
    "VMCalculation",
    "WorkloadGroupResult",
    "calculate",
]


@dataclass(frozen=True)
class VMCalculation:
    """Per-VM calculation result."""

    vm_name: str
    workload_category: str
    provisioned_mib: float
    in_use_mib: float
    drr: float
    required_mib: float
    peak_iops: float = 0.0
    avg_iops: float = 0.0
    peak_throughput_mbs: float = 0.0
    iops_8k_equivalent: float = 0.0


@dataclass(frozen=True)
class WorkloadGroupResult:
    """Subtotals for one workload category."""

    category: str
    vm_count: int
    total_provisioned_mib: float
    total_in_use_mib: float
    avg_drr: float
    total_required_mib: float


@dataclass(frozen=True)
class CalculationSummary:
    """Grand totals and breakdown for all VMs."""

    vm_calculations: list[VMCalculation]
    workload_groups: list[WorkloadGroupResult]
    total_vms: int
    total_provisioned_mib: float
    total_in_use_mib: float
    total_required_mib: float
    weighted_avg_drr: float
    avg_vm_size_mib: float = 0.0
    avg_vm_cpus: float = 0.0
    avg_vm_memory_mib: float = 0.0
    total_cpus: int = 0
    total_memory_mib: float = 0.0
    largest_vm_name: str = ""
    largest_vm_provisioned_mib: float = 0.0
    total_avg_iops: float = 0.0
    max_vm_peak_iops: float = 0.0
    max_vm_peak_iops_name: str = ""
    peak_throughput_mbs: float = 0.0
    total_iops_8k_equivalent: float = 0.0
    has_performance_data: bool = False


def calculate(row_data: list[dict[str, Any]]) -> CalculationSummary:
    """Calculate required capacity for each VM and produce grouped summaries.

    Args:
        row_data: List of row dicts from session state. Expected keys:
            vm_name, workload_category, provisioned_mib, in_use_mib, drr.

    Returns:
        CalculationSummary with per-VM results, workload groups, and grand totals.
    """
    if not row_data:
        return CalculationSummary(
            vm_calculations=[],
            workload_groups=[],
            total_vms=0,
            total_provisioned_mib=0.0,
            total_in_use_mib=0.0,
            total_required_mib=0.0,
            weighted_avg_drr=0.0,
        )

    def _safe_float(val: object) -> float:
        """Convert value to float, returning 0.0 for None/NaN/non-numeric."""
        if val is None:
            return 0.0
        try:
            f = float(val)
            return 0.0 if math.isnan(f) else f
        except (TypeError, ValueError):
            return 0.0

    # Per-VM calculations
    vm_calcs: list[VMCalculation] = []
    for row in row_data:
        vm_name = str(row.get("vm_name", ""))
        workload_category = str(row.get("workload_category", "Unknown (Reducible)"))
        provisioned_mib = float(row.get("provisioned_mib", 0))
        in_use_mib = float(row.get("in_use_mib", 0))
        drr = max(float(row.get("drr", 5.0)), 0.1)
        required_mib = provisioned_mib / drr

        peak_iops = _safe_float(row.get("peak_iops"))
        avg_iops = _safe_float(row.get("avg_iops"))
        peak_throughput_mbs = _safe_float(row.get("peak_throughput_mbs"))
        iops_8k_equivalent = _safe_float(row.get("iops_8k_equivalent"))

        vm_calcs.append(
            VMCalculation(
                vm_name=vm_name,
                workload_category=workload_category,
                provisioned_mib=provisioned_mib,
                in_use_mib=in_use_mib,
                drr=drr,
                required_mib=required_mib,
                peak_iops=peak_iops,
                avg_iops=avg_iops,
                peak_throughput_mbs=peak_throughput_mbs,
                iops_8k_equivalent=iops_8k_equivalent,
            )
        )

    # Group by workload category
    groups: dict[str, list[VMCalculation]] = defaultdict(list)
    for vm in vm_calcs:
        groups[vm.workload_category].append(vm)

    workload_groups: list[WorkloadGroupResult] = []
    for category in sorted(groups):
        vms = groups[category]
        grp_provisioned = sum(v.provisioned_mib for v in vms)
        grp_in_use = sum(v.in_use_mib for v in vms)
        grp_required = sum(v.required_mib for v in vms)
        grp_avg_drr = grp_provisioned / grp_required if grp_required > 0 else 0.0

        workload_groups.append(
            WorkloadGroupResult(
                category=category,
                vm_count=len(vms),
                total_provisioned_mib=grp_provisioned,
                total_in_use_mib=grp_in_use,
                avg_drr=grp_avg_drr,
                total_required_mib=grp_required,
            )
        )

    # Grand totals
    total_provisioned = sum(v.provisioned_mib for v in vm_calcs)
    total_in_use = sum(v.in_use_mib for v in vm_calcs)
    total_required = sum(v.required_mib for v in vm_calcs)
    weighted_avg_drr = total_provisioned / total_required if total_required > 0 else 0.0

    # VM statistics
    total_vms = len(vm_calcs)
    avg_vm_size_mib = total_provisioned / total_vms if total_vms > 0 else 0.0

    # CPU and memory totals
    total_cpus = sum(int(_safe_float(r.get("num_cpus"))) for r in row_data)
    total_memory_mib = sum(_safe_float(r.get("memory_mib")) for r in row_data)
    avg_vm_cpus = total_cpus / total_vms if total_vms > 0 else 0.0
    avg_vm_memory_mib = total_memory_mib / total_vms if total_vms > 0 else 0.0

    # Largest VM by provisioned size
    largest_vm = max(vm_calcs, key=lambda v: v.provisioned_mib)
    largest_vm_name = largest_vm.vm_name
    largest_vm_provisioned_mib = largest_vm.provisioned_mib

    # Performance totals
    has_performance_data = any(v.peak_iops > 0 for v in vm_calcs)
    total_avg_iops = sum(v.avg_iops for v in vm_calcs)
    hottest_vm = max(vm_calcs, key=lambda v: v.peak_iops)
    max_vm_peak_iops = hottest_vm.peak_iops
    max_vm_peak_iops_name = hottest_vm.vm_name
    peak_throughput_mbs = max((v.peak_throughput_mbs for v in vm_calcs), default=0.0)
    total_iops_8k_equivalent = sum(v.iops_8k_equivalent for v in vm_calcs)

    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=workload_groups,
        total_vms=total_vms,
        total_provisioned_mib=total_provisioned,
        total_in_use_mib=total_in_use,
        total_required_mib=total_required,
        weighted_avg_drr=weighted_avg_drr,
        avg_vm_size_mib=avg_vm_size_mib,
        avg_vm_cpus=avg_vm_cpus,
        avg_vm_memory_mib=avg_vm_memory_mib,
        total_cpus=total_cpus,
        total_memory_mib=total_memory_mib,
        largest_vm_name=largest_vm_name,
        largest_vm_provisioned_mib=largest_vm_provisioned_mib,
        total_avg_iops=total_avg_iops,
        max_vm_peak_iops=max_vm_peak_iops,
        max_vm_peak_iops_name=max_vm_peak_iops_name,
        peak_throughput_mbs=peak_throughput_mbs,
        total_iops_8k_equivalent=total_iops_8k_equivalent,
        has_performance_data=has_performance_data,
    )
