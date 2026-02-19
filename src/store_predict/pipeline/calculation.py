"""Calculation service: per-VM required capacity, workload group subtotals, and totals.

Pure pipeline module with zero UI imports.
"""

from __future__ import annotations

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

    # Per-VM calculations
    vm_calcs: list[VMCalculation] = []
    for row in row_data:
        vm_name = str(row.get("vm_name", ""))
        workload_category = str(row.get("workload_category", "Unknown (Reducible)"))
        provisioned_mib = float(row.get("provisioned_mib", 0))
        in_use_mib = float(row.get("in_use_mib", 0))
        drr = max(float(row.get("drr", 5.0)), 0.1)
        required_mib = provisioned_mib / drr

        vm_calcs.append(
            VMCalculation(
                vm_name=vm_name,
                workload_category=workload_category,
                provisioned_mib=provisioned_mib,
                in_use_mib=in_use_mib,
                drr=drr,
                required_mib=required_mib,
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

    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=workload_groups,
        total_vms=len(vm_calcs),
        total_provisioned_mib=total_provisioned,
        total_in_use_mib=total_in_use,
        total_required_mib=total_required,
        weighted_avg_drr=weighted_avg_drr,
    )
