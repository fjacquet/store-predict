"""Layout engine: datastore placement strategies using multi-dimensional BFD.

Pure pipeline module with zero UI imports.

Public entry point: generate_all_proposals(summary, constraints)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import StrEnum
from math import ceil
from typing import TYPE_CHECKING

from store_predict.pipeline.layout_models import (
    _DEFAULT_IOPS_FALLBACK,
    DEFAULT_IOPS_BY_WORKLOAD,
    DatastoreRecommendation,
    LayoutMetrics,
    LayoutProposal,
    PlacementConstraints,
)

if TYPE_CHECKING:
    from store_predict.pipeline.calculation import CalculationSummary, VMCalculation

__all__ = [
    "generate_all_proposals",
]


# ---------------------------------------------------------------------------
# Internal mutable builder (NOT frozen — accumulates VMs during placement)
# ---------------------------------------------------------------------------


@dataclass
class _DatastoreBuilder:
    """Mutable state during BFD placement. Converted to DatastoreRecommendation at end."""

    name: str
    raw_capacity_mib: float
    usable_capacity_mib: float
    assigned_vms: list[VMCalculation] = field(default_factory=list)
    used_capacity_mib: float = 0.0
    total_iops: float = 0.0

    def can_fit(self, vm: VMCalculation, max_vms: int, iops_budget: float) -> bool:
        """Return True if VM can be placed in this datastore without violating any constraint."""
        fits_capacity = self.used_capacity_mib + vm.required_mib <= self.usable_capacity_mib
        fits_iops = self.total_iops + vm.peak_iops <= iops_budget
        fits_count = len(self.assigned_vms) < max_vms
        return fits_capacity and fits_iops and fits_count

    def add_vm(self, vm: VMCalculation) -> None:
        """Add VM to this datastore, updating running totals."""
        self.assigned_vms.append(vm)
        self.used_capacity_mib += vm.required_mib
        self.total_iops += vm.peak_iops

    def to_recommendation(self) -> DatastoreRecommendation:
        """Freeze this builder into an immutable DatastoreRecommendation."""
        utilization_pct = (
            self.used_capacity_mib / self.usable_capacity_mib * 100.0 if self.usable_capacity_mib > 0 else 0.0
        )
        workload_types: frozenset[str] = frozenset(vm.workload_category for vm in self.assigned_vms)
        return DatastoreRecommendation(
            name=self.name,
            raw_capacity_mib=self.raw_capacity_mib,
            usable_capacity_mib=self.usable_capacity_mib,
            assigned_vms=tuple(self.assigned_vms),
            used_capacity_mib=self.used_capacity_mib,
            utilization_pct=utilization_pct,
            total_iops=self.total_iops,
            vm_count=len(self.assigned_vms),
            workload_types=workload_types,
        )


# ---------------------------------------------------------------------------
# Default IOPS injection (REQ-014)
# ---------------------------------------------------------------------------


def _apply_default_iops(vm: VMCalculation) -> VMCalculation:
    """Return a new VMCalculation with estimated IOPS when no real performance data exists.

    When vm.peak_iops == 0, injects workload-based IOPS estimates.
    avg_iops is estimated as 70% of peak.
    Uses dataclasses.replace() since VMCalculation is frozen.
    """
    if vm.peak_iops > 0:
        return vm  # already has real data — preserve it unchanged
    estimated = DEFAULT_IOPS_BY_WORKLOAD.get(vm.workload_category, _DEFAULT_IOPS_FALLBACK)
    return dataclasses.replace(
        vm,
        peak_iops=estimated,
        avg_iops=estimated * 0.7,
    )


# ---------------------------------------------------------------------------
# BFD core algorithm
# ---------------------------------------------------------------------------


def _bfd_place(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
    name_prefix: str,
    max_vms_override: int | None = None,
) -> list[_DatastoreBuilder]:
    """Multi-dimensional Best Fit Decreasing (BFD) datastore placement.

    Sorts VMs by max(capacity_ratio, iops_ratio) descending.
    Places each VM into the tightest-fitting bin that satisfies all three constraints.
    Opens a new bin when no existing bin can accommodate the VM.

    Oversized VMs (required_mib > usable_capacity_mib) are separated first and
    given dedicated datastores named {name_prefix}_OVER_{idx:02d}.

    Args:
        vms: List of VMs to place.
        constraints: Placement constraints (capacity, IOPS, count limits).
        name_prefix: Prefix for datastore names (e.g. "DS_CONSOL").
        max_vms_override: Override constraints.max_vms_per_ds if provided.

    Returns:
        List of _DatastoreBuilder objects (one per datastore).
    """
    if not vms:
        return []

    max_vms = max_vms_override if max_vms_override is not None else constraints.max_vms_per_ds
    usable = constraints.usable_capacity_mib
    iops_budget = constraints.iops_budget_per_ds

    # Separate oversized VMs before BFD — they can never fit in a standard bin
    normal_vms: list[VMCalculation] = []
    oversized_vms: list[VMCalculation] = []
    for vm in vms:
        if vm.required_mib > usable:
            oversized_vms.append(vm)
        else:
            normal_vms.append(vm)

    bins: list[_DatastoreBuilder] = []

    # Give each oversized VM a dedicated datastore sized to the VM
    for idx, vm in enumerate(oversized_vms, start=1):
        # Size to VM with growth margin and snapshot reserve applied
        vm_raw_mib = vm.required_mib / constraints.usable_ratio if constraints.usable_ratio > 0 else vm.required_mib
        ds_name = f"{name_prefix}_OVER_{idx:02d}"
        b = _DatastoreBuilder(
            name=ds_name,
            raw_capacity_mib=vm_raw_mib,
            usable_capacity_mib=vm.required_mib,
        )
        b.add_vm(vm)
        bins.append(b)

    # BFD for normal VMs
    def demand_score(vm: VMCalculation) -> float:
        cap_ratio = vm.required_mib / usable if usable > 0 else 0.0
        iops_ratio = vm.peak_iops / iops_budget if iops_budget > 0 else 0.0
        return max(cap_ratio, iops_ratio)

    sorted_vms = sorted(normal_vms, key=demand_score, reverse=True)

    # Count of regular (non-OVER) bins for naming
    regular_bin_count = 0

    for vm in sorted_vms:
        # Find best-fit bin: least remaining capacity that still fits
        best_bin: _DatastoreBuilder | None = None
        best_remaining = float("inf")

        for b in bins:
            # Skip OVER bins — they are dedicated to a single oversized VM
            if "_OVER_" in b.name:
                continue
            if b.can_fit(vm, max_vms, iops_budget):
                remaining = b.usable_capacity_mib - b.used_capacity_mib
                if remaining < best_remaining:
                    best_bin = b
                    best_remaining = remaining

        if best_bin is None:
            # Open new datastore
            regular_bin_count += 1
            new_bin = _DatastoreBuilder(
                name=f"{name_prefix}_{regular_bin_count:02d}",
                raw_capacity_mib=constraints.max_ds_capacity_mib,
                usable_capacity_mib=usable,
            )
            new_bin.add_vm(vm)
            bins.append(new_bin)
        else:
            best_bin.add_vm(vm)

    return bins


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


def _compute_metrics(datastores: list[DatastoreRecommendation]) -> LayoutMetrics:
    """Compute aggregate layout metrics from a list of datastore recommendations.

    Handles empty list by returning a zeroed LayoutMetrics.
    """
    if not datastores:
        return LayoutMetrics(
            total_ds_count=0,
            total_raw_capacity_mib=0.0,
            total_usable_capacity_mib=0.0,
            total_used_capacity_mib=0.0,
            avg_utilization_pct=0.0,
            min_utilization_pct=0.0,
            max_utilization_pct=0.0,
            avg_vm_density=0.0,
            max_vm_density=0,
            total_iops_placed=0.0,
            max_iops_single_ds=0.0,
            iops_headroom_pct=100.0,
            isolation_score=0.0,
            snapshot_granularity_rating="fine",
            oversized_vm_count=0,
        )

    ds_count = len(datastores)
    utilizations = [ds.utilization_pct for ds in datastores]
    vm_densities = [ds.vm_count for ds in datastores]
    iops_values = [ds.total_iops for ds in datastores]

    # Isolation score: ratio of datastores that contain only a single workload type
    single_workload_ds = sum(1 for ds in datastores if len({v.workload_category for v in ds.assigned_vms}) <= 1)
    isolation_score = single_workload_ds / ds_count if ds_count > 0 else 0.0

    # Snapshot granularity rating based on average VM density
    avg_density = sum(vm_densities) / ds_count if ds_count > 0 else 0.0
    if avg_density <= 3:
        snapshot_granularity = "fine"
    elif avg_density <= 10:
        snapshot_granularity = "medium"
    else:
        snapshot_granularity = "coarse"

    # Count oversized VMs (in datastores with _OVER_ in the name)
    oversized_vm_count = sum(ds.vm_count for ds in datastores if "_OVER_" in ds.name)

    max_iops = max(iops_values, default=0.0)
    iops_headroom_pct = (1.0 - max_iops / 100_000.0) * 100.0 if max_iops < 100_000.0 else 0.0

    return LayoutMetrics(
        total_ds_count=ds_count,
        total_raw_capacity_mib=sum(ds.raw_capacity_mib for ds in datastores),
        total_usable_capacity_mib=sum(ds.usable_capacity_mib for ds in datastores),
        total_used_capacity_mib=sum(ds.used_capacity_mib for ds in datastores),
        avg_utilization_pct=sum(utilizations) / ds_count,
        min_utilization_pct=min(utilizations),
        max_utilization_pct=max(utilizations),
        avg_vm_density=avg_density,
        max_vm_density=max(vm_densities),
        total_iops_placed=sum(iops_values),
        max_iops_single_ds=max_iops,
        iops_headroom_pct=iops_headroom_pct,
        isolation_score=isolation_score,
        snapshot_granularity_rating=snapshot_granularity,
        oversized_vm_count=oversized_vm_count,
    )


# ---------------------------------------------------------------------------
# Consolidation strategy
# ---------------------------------------------------------------------------


def _consolidation_strategy(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> LayoutProposal:
    """Consolidation strategy: minimize datastore count using multi-dimensional BFD.

    All VMs are placed together regardless of workload type, prioritizing
    maximum utilization and minimum datastore count.
    """
    builders = _bfd_place(vms, constraints, "DS_CONSOL")
    recommendations = [b.to_recommendation() for b in builders]
    metrics = _compute_metrics(recommendations)
    return LayoutProposal(
        strategy_name="consolidation",
        datastores=tuple(recommendations),
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Performance strategy — Phase 0 isolation + tier-based BFD
# ---------------------------------------------------------------------------


class PerformanceTier(StrEnum):
    """Three-tier workload classification for the Performance strategy."""

    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


# Mission-critical isolation thresholds (Phase 0)
_ISOLATION_CAPACITY_THRESHOLD_MIB: float = 2 * 1024 * 1024  # 2 TiB
_ISOLATION_IOPS_THRESHOLD: float = 5_000.0


def _is_mission_critical(vm: VMCalculation) -> bool:
    """Return True if VM qualifies for Phase 0 dedicated isolation.

    Criteria:
    - Workload contains "SAP HANA" or "Exchange" (business-critical applications)
    - required_mib > 2 TiB (very large VMs)
    - peak_iops > 5000 (very high IOPS demand)
    """
    if "SAP HANA" in vm.workload_category or "Exchange" in vm.workload_category:
        return True
    if vm.required_mib > _ISOLATION_CAPACITY_THRESHOLD_MIB:
        return True
    return vm.peak_iops > _ISOLATION_IOPS_THRESHOLD


def _classify_tier(vm: VMCalculation) -> PerformanceTier:
    """Classify a VM into a performance tier.

    HOT: peak_iops > 500 or workload category starts with "Database"
    WARM: 100 <= peak_iops <= 500
    COLD: otherwise (low IOPS, non-Database)

    Uses startswith("Database") rather than "in" to avoid false positive on
    categories like "Virtual Machines/... - No Database, File nor Email".
    """
    if vm.peak_iops > 500 or vm.workload_category.startswith("Database"):
        return PerformanceTier.HOT
    if 100.0 <= vm.peak_iops <= 500.0:
        return PerformanceTier.WARM
    return PerformanceTier.COLD


def _isolate_vms(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> tuple[list[_DatastoreBuilder], list[VMCalculation]]:
    """Phase 0: separate mission-critical VMs into 1:1 dedicated datastores.

    Each isolated VM gets its own datastore sized exactly to that VM
    (not the global max DS size). Naming uses workload-based prefixes with
    per-prefix independent counters.

    Returns:
        (isolated_bins, remaining_vms) — remaining VMs go through tier BFD.
    """
    isolated_bins: list[_DatastoreBuilder] = []
    remaining_vms: list[VMCalculation] = []

    # Per-prefix naming counters (independent per Pitfall 5)
    prefix_counters: dict[str, int] = {}

    for vm in vms:
        if not _is_mission_critical(vm):
            remaining_vms.append(vm)
            continue

        # Determine naming prefix from workload
        wcat = vm.workload_category
        if "SAP HANA" in wcat or "HANA" in wcat:
            prefix = "DS_HANA"
        elif "Exchange" in wcat:
            prefix = "DS_EXCHANGE"
        elif "Oracle" in wcat:
            prefix = "DS_ORA"
        else:
            prefix = "DS_ISOLATED"

        prefix_counters[prefix] = prefix_counters.get(prefix, 0) + 1
        ds_name = f"{prefix}_{prefix_counters[prefix]:02d}"

        # Size DS exactly to this VM (not global max)
        vm_raw_mib = vm.required_mib / constraints.usable_ratio if constraints.usable_ratio > 0 else vm.required_mib
        b = _DatastoreBuilder(
            name=ds_name,
            raw_capacity_mib=vm_raw_mib,
            usable_capacity_mib=vm.required_mib,
        )
        b.add_vm(vm)
        isolated_bins.append(b)

    return isolated_bins, remaining_vms


def _performance_strategy(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> LayoutProposal:
    """Performance strategy with Phase 0 isolation and three-tier BFD.

    Phase 0: Mission-critical VMs → dedicated per-VM datastores.
    Phase 1: Classify remaining VMs into HOT / WARM / COLD tiers.
    Phase 2: BFD within each tier using tier-specific constraints (independent bins).

    Anti-affinity between Database and VDI is naturally enforced because each
    tier runs a completely independent _bfd_place() call.
    """
    # Phase 0 — isolate mission-critical VMs
    isolated_builders, remaining = _isolate_vms(vms, constraints)

    # Phase 1 — classify remaining VMs by tier
    hot_vms: list[VMCalculation] = []
    warm_vms: list[VMCalculation] = []
    cold_vms: list[VMCalculation] = []

    for vm in remaining:
        tier = _classify_tier(vm)
        if tier == PerformanceTier.HOT:
            hot_vms.append(vm)
        elif tier == PerformanceTier.WARM:
            warm_vms.append(vm)
        else:
            cold_vms.append(vm)

    # Phase 2 — independent BFD per tier
    hot_builders = _bfd_place(hot_vms, constraints, "DS_HOT", max_vms_override=10)
    warm_builders = _bfd_place(warm_vms, constraints, "DS_WARM")
    cold_builders = _bfd_place(cold_vms, constraints, "DS_COLD")

    all_builders = isolated_builders + hot_builders + warm_builders + cold_builders
    recommendations = [b.to_recommendation() for b in all_builders]
    metrics = _compute_metrics(recommendations)

    return LayoutProposal(
        strategy_name="performance",
        datastores=tuple(recommendations),
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Uniform strategy — LPT distribution across equal-sized datastores
# ---------------------------------------------------------------------------


def _uniform_strategy(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> LayoutProposal:
    """Uniform strategy: distribute VMs evenly across equal-sized datastores using LPT.

    DS count is driven by whichever dimension (capacity or IOPS) requires more datastores.
    LPT (Longest Processing Time): sort VMs by required_mib descending, assign each to
    the least-loaded bin. This produces balanced utilization across datastores.

    Oversized VMs (required_mib > usable_capacity_mib) get dedicated datastores,
    same as BFD strategies — they can never fit in a standard bin.
    """
    if not vms:
        return LayoutProposal(
            strategy_name="uniform",
            datastores=(),
            metrics=_compute_metrics([]),
        )

    usable = constraints.usable_capacity_mib
    iops_budget = constraints.iops_budget_per_ds

    # Separate oversized VMs — they can never fit in a standard bin
    normal_vms: list[VMCalculation] = []
    oversized_vms: list[VMCalculation] = []
    for vm in vms:
        if vm.required_mib > usable:
            oversized_vms.append(vm)
        else:
            normal_vms.append(vm)

    bins: list[_DatastoreBuilder] = []

    # Give each oversized VM a dedicated datastore sized to the VM
    for idx, vm in enumerate(oversized_vms, start=1):
        vm_raw_mib = vm.required_mib / constraints.usable_ratio if constraints.usable_ratio > 0 else vm.required_mib
        ds_name = f"DS_UNIFORM_OVER_{idx:02d}"
        b = _DatastoreBuilder(
            name=ds_name,
            raw_capacity_mib=vm_raw_mib,
            usable_capacity_mib=vm.required_mib,
        )
        b.add_vm(vm)
        bins.append(b)

    if normal_vms:
        total_cap = sum(vm.required_mib for vm in normal_vms)
        total_iops = sum(vm.peak_iops for vm in normal_vms)

        # DS count is max of capacity-driven and IOPS-driven requirements
        ds_count_cap = ceil(total_cap / usable) if usable > 0 else 1
        ds_count_iops = ceil(total_iops / iops_budget) if iops_budget > 0 else 1
        ds_count = max(ds_count_cap, ds_count_iops, 1)

        # Create equal-sized bins upfront
        uniform_bins: list[_DatastoreBuilder] = [
            _DatastoreBuilder(
                name=f"DS_UNIFORM_{idx:02d}",
                raw_capacity_mib=constraints.max_ds_capacity_mib,
                usable_capacity_mib=usable,
            )
            for idx in range(1, ds_count + 1)
        ]

        # LPT: largest VMs first, assign to least-loaded bin that can still fit
        sorted_vms = sorted(normal_vms, key=lambda vm: vm.required_mib, reverse=True)
        for vm in sorted_vms:
            # Try to find a bin where the VM actually fits
            eligible = [b for b in uniform_bins if b.used_capacity_mib + vm.required_mib <= b.usable_capacity_mib]
            if eligible:
                least_loaded = min(eligible, key=lambda b: b.used_capacity_mib)
                least_loaded.add_vm(vm)
            else:
                # All existing bins would overflow — open a new one
                new_bin = _DatastoreBuilder(
                    name=f"DS_UNIFORM_{len(uniform_bins) + 1:02d}",
                    raw_capacity_mib=constraints.max_ds_capacity_mib,
                    usable_capacity_mib=usable,
                )
                new_bin.add_vm(vm)
                uniform_bins.append(new_bin)

        bins.extend(uniform_bins)

    recommendations = [b.to_recommendation() for b in bins]
    metrics = _compute_metrics(recommendations)

    return LayoutProposal(
        strategy_name="uniform",
        datastores=tuple(recommendations),
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_all_proposals(
    summary: CalculationSummary,
    constraints: PlacementConstraints | None = None,
) -> list[LayoutProposal]:
    """Generate layout proposals for all three strategies.

    Strategies returned (in order): consolidation, performance, uniform.

    Args:
        summary: Output from pipeline/calculation.py calculate().
        constraints: Tunable parameters; uses defaults if None.

    Returns:
        List of exactly 3 LayoutProposal objects, one per strategy.
    """
    if constraints is None:
        constraints = PlacementConstraints()

    vms = list(summary.vm_calculations)

    # Apply IOPS estimates if no real performance data (REQ-014)
    if not summary.has_performance_data:
        vms = [_apply_default_iops(vm) for vm in vms]

    if not vms:
        empty_metrics = _compute_metrics([])
        return [
            LayoutProposal(strategy_name="consolidation", datastores=(), metrics=empty_metrics),
            LayoutProposal(strategy_name="performance", datastores=(), metrics=empty_metrics),
            LayoutProposal(strategy_name="uniform", datastores=(), metrics=empty_metrics),
        ]

    return [
        _consolidation_strategy(vms, constraints),
        _performance_strategy(vms, constraints),
        _uniform_strategy(vms, constraints),
    ]
