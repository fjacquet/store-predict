"""Layout engine data models for datastore placement recommendations.

Pure pipeline module with zero UI imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store_predict.pipeline.calculation import VMCalculation

__all__ = [
    "DEFAULT_IOPS_BY_WORKLOAD",
    "_DEFAULT_IOPS_FALLBACK",
    "DatastoreRecommendation",
    "LayoutMetrics",
    "LayoutProposal",
    "PlacementConstraints",
]

# ---------------------------------------------------------------------------
# Default IOPS estimates when no LiveOptics performance data (REQ-014)
# Keys match workload_category format: "Category/Subcategory"
# ---------------------------------------------------------------------------

DEFAULT_IOPS_BY_WORKLOAD: dict[str, float] = {
    "Database/Microsoft SQL": 500.0,
    "Database/Oracle": 800.0,
    "Database/SAP HANA(S4)": 1000.0,
    "VDI/Full Clone / MCS (Citrix)": 30.0,
    "VDI/Linked Clone / PVS (Citrix)": 50.0,
    "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email": 50.0,
    "File/General Purpose": 100.0,
    "Unknown (Reducible)/Unknown (Reducible)": 50.0,
}

_DEFAULT_IOPS_FALLBACK: float = 50.0


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlacementConstraints:
    """Tunable parameters for datastore layout. All values use defaults from Dell best practices."""

    max_ds_capacity_mib: float = 4 * 1024 * 1024  # 4 TiB in MiB
    max_vms_per_ds: int = 25
    iops_budget_per_ds: float = 100_000.0
    snapshot_reserve_pct: float = 15.0  # 0-100
    growth_margin_pct: float = 20.0  # 0-100

    @property
    def usable_ratio(self) -> float:
        """Fraction of raw capacity available for VM data after snapshot reserve and growth margin."""
        return (1.0 - self.snapshot_reserve_pct / 100.0) * (1.0 - self.growth_margin_pct / 100.0)

    @property
    def usable_capacity_mib(self) -> float:
        """Effective capacity available for VM data in MiB."""
        return self.max_ds_capacity_mib * self.usable_ratio


@dataclass(frozen=True)
class DatastoreRecommendation:
    """A single recommended datastore with assigned VMs and utilization metrics."""

    name: str
    raw_capacity_mib: float
    usable_capacity_mib: float
    assigned_vms: tuple[VMCalculation, ...]  # frozen — use tuple not list
    used_capacity_mib: float
    utilization_pct: float
    total_iops: float
    vm_count: int
    workload_types: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class LayoutMetrics:
    """Aggregate metrics for a layout proposal."""

    total_ds_count: int
    total_raw_capacity_mib: float
    total_usable_capacity_mib: float
    total_used_capacity_mib: float
    avg_utilization_pct: float
    min_utilization_pct: float
    max_utilization_pct: float
    avg_vm_density: float
    max_vm_density: int
    total_iops_placed: float
    max_iops_single_ds: float
    iops_headroom_pct: float
    isolation_score: float  # 0.0-1.0: ratio of datastores with single workload type
    snapshot_granularity_rating: str  # "fine" | "medium" | "coarse"
    oversized_vm_count: int = 0  # VMs larger than max DS capacity


@dataclass(frozen=True)
class LayoutProposal:
    """A complete layout recommendation for one strategy."""

    strategy_name: str  # "consolidation" | "performance" | "uniform"
    datastores: tuple[DatastoreRecommendation, ...]
    metrics: LayoutMetrics
