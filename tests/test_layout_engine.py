"""Unit tests for layout engine models, consolidation strategy, metrics, and default IOPS.

Tests use real objects and fixtures — no unittest.mock per project convention.
"""

from __future__ import annotations

from store_predict.pipeline.calculation import VMCalculation
from store_predict.pipeline.layout_engine import (
    _apply_default_iops,
    _bfd_place,
    _compute_metrics,
    _consolidation_strategy,
)
from store_predict.pipeline.layout_models import (
    DatastoreRecommendation,
    PlacementConstraints,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MiB = 1.0
_GiB = 1024.0 * _MiB
_TiB = 1024.0 * _GiB


def _make_vm(
    name: str,
    category: str,
    required_mib: float,
    peak_iops: float = 0.0,
) -> VMCalculation:
    """Create a VMCalculation with sensible defaults for unused fields."""
    return VMCalculation(
        vm_name=name,
        workload_category=category,
        provisioned_mib=required_mib * 2,  # pretend DRR=2 for provisioned
        in_use_mib=required_mib,
        drr=2.0,
        required_mib=required_mib,
        peak_iops=peak_iops,
        avg_iops=peak_iops * 0.7,
    )


# ---------------------------------------------------------------------------
# TestPlacementConstraints
# ---------------------------------------------------------------------------


class TestPlacementConstraints:
    def test_default_usable_ratio(self) -> None:
        """usable_ratio = (1 - 0.15) * (1 - 0.20) = 0.85 * 0.80 = 0.68"""
        c = PlacementConstraints()
        assert abs(c.usable_ratio - 0.68) < 1e-9

    def test_default_usable_capacity(self) -> None:
        """4 TiB * 0.68 = 2,852,126.72 MiB (approximately)"""
        c = PlacementConstraints()
        expected = 4 * _TiB * 0.68
        assert abs(c.usable_capacity_mib - expected) < 1.0

    def test_custom_constraints(self) -> None:
        """Custom values compute correctly."""
        c = PlacementConstraints(
            max_ds_capacity_mib=2 * _TiB,
            snapshot_reserve_pct=10.0,
            growth_margin_pct=10.0,
        )
        # usable_ratio = 0.90 * 0.90 = 0.81
        assert abs(c.usable_ratio - 0.81) < 1e-9
        assert abs(c.usable_capacity_mib - 2 * _TiB * 0.81) < 1.0


# ---------------------------------------------------------------------------
# TestBFDPlace
# ---------------------------------------------------------------------------


class TestBFDPlace:
    def test_single_vm(self) -> None:
        """One VM produces one datastore."""
        c = PlacementConstraints()
        vms = [_make_vm("vm-01", "Database/Microsoft SQL", 100 * _GiB)]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        assert len(bins) == 1
        assert len(bins[0].assigned_vms) == 1

    def test_two_vms_fit_one_ds(self) -> None:
        """Two small VMs should pack into one DS when both fit."""
        c = PlacementConstraints()
        # Each VM is tiny relative to DS capacity
        vms = [
            _make_vm("vm-01", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 10 * _GiB),
            _make_vm("vm-02", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 10 * _GiB),
        ]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        assert len(bins) == 1
        assert len(bins[0].assigned_vms) == 2  # type: ignore[attr-defined]

    def test_capacity_overflow_creates_new_ds(self) -> None:
        """VM that overflows capacity creates a second DS."""
        # Use tiny DS to force overflow
        c = PlacementConstraints(max_ds_capacity_mib=100 * _GiB, snapshot_reserve_pct=0.0, growth_margin_pct=0.0)
        # DS capacity = 100 GiB, fill with 2 VMs of 60 GiB each
        vms = [
            _make_vm("vm-01", "Database/Microsoft SQL", 60 * _GiB),
            _make_vm("vm-02", "Database/Microsoft SQL", 60 * _GiB),
        ]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        assert len(bins) == 2

    def test_iops_overflow_creates_new_ds(self) -> None:
        """IOPS limit forces creation of a second DS."""
        # Very small IOPS budget
        c = PlacementConstraints(iops_budget_per_ds=1000.0)
        vms = [
            _make_vm("vm-01", "Database/Oracle", 10 * _GiB, peak_iops=800.0),
            _make_vm("vm-02", "Database/Oracle", 10 * _GiB, peak_iops=800.0),
        ]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        # 800 + 800 = 1600 > 1000 budget, so must split
        assert len(bins) == 2

    def test_vm_count_overflow(self) -> None:
        """max_vms_per_ds limit forces creation of a second DS."""
        c = PlacementConstraints(max_vms_per_ds=2)
        vms = [
            _make_vm(f"vm-{i:02d}", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 1 * _GiB)
            for i in range(3)
        ]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        assert len(bins) == 2
        # Verify no DS exceeds the max VM count
        assert all(len(b.assigned_vms) <= 2 for b in bins)  # type: ignore[attr-defined]

    def test_oversized_vm_gets_dedicated_ds(self) -> None:
        """VM larger than usable_capacity_mib gets its own OVER datastore."""
        # Small DS (1 TiB usable with no reserves)
        c = PlacementConstraints(
            max_ds_capacity_mib=1 * _TiB,
            snapshot_reserve_pct=0.0,
            growth_margin_pct=0.0,
        )
        # VM is 2 TiB — bigger than DS
        huge_vm = _make_vm("vm-huge", "Database/Oracle", 2 * _TiB)
        vms = [huge_vm]
        bins = _bfd_place(vms, c, "DS_CONSOL")
        assert len(bins) == 1
        assert "_OVER_" in bins[0].name  # type: ignore[attr-defined]
        assert bins[0].assigned_vms[0].vm_name == "vm-huge"  # type: ignore[attr-defined]

    def test_empty_vm_list(self) -> None:
        """Empty VM list returns empty list without crashing."""
        c = PlacementConstraints()
        bins = _bfd_place([], c, "DS_CONSOL")
        assert bins == []


# ---------------------------------------------------------------------------
# TestConsolidationStrategy
# ---------------------------------------------------------------------------


class TestConsolidationStrategy:
    def test_basic_consolidation(self) -> None:
        """5 small VMs consolidated into minimal DS count."""
        c = PlacementConstraints()
        vms = [
            _make_vm(f"vm-{i:02d}", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 50 * _GiB)
            for i in range(5)
        ]
        proposal = _consolidation_strategy(vms, c)
        # All 5 tiny VMs should fit in 1 DS (50 * 5 = 250 GiB << 2.7 TiB)
        assert proposal.metrics.total_ds_count == 1

    def test_naming_convention(self) -> None:
        """DS names follow DS_CONSOL_NN convention."""
        c = PlacementConstraints(max_ds_capacity_mib=100 * _GiB, snapshot_reserve_pct=0.0, growth_margin_pct=0.0)
        vms = [
            _make_vm("vm-01", "Database/Microsoft SQL", 60 * _GiB),
            _make_vm("vm-02", "Database/Microsoft SQL", 60 * _GiB),
        ]
        proposal = _consolidation_strategy(vms, c)
        ds_names = [ds.name for ds in proposal.datastores]
        assert "DS_CONSOL_01" in ds_names
        assert "DS_CONSOL_02" in ds_names

    def test_returns_layout_proposal(self) -> None:
        """Result is a LayoutProposal with strategy_name='consolidation'."""
        from store_predict.pipeline.layout_models import LayoutProposal
        c = PlacementConstraints()
        vms = [_make_vm("vm-01", "Database/Oracle", 100 * _GiB)]
        proposal = _consolidation_strategy(vms, c)
        assert isinstance(proposal, LayoutProposal)
        assert proposal.strategy_name == "consolidation"


# ---------------------------------------------------------------------------
# TestComputeMetrics
# ---------------------------------------------------------------------------


def _make_ds(
    name: str,
    vms: list[VMCalculation],
    usable_mib: float,
) -> DatastoreRecommendation:
    """Helper: build a DatastoreRecommendation from a list of VMs."""
    used = sum(v.required_mib for v in vms)
    total_iops = sum(v.peak_iops for v in vms)
    utilization_pct = used / usable_mib * 100.0 if usable_mib > 0 else 0.0
    workload_types: frozenset[str] = frozenset(v.workload_category for v in vms)
    return DatastoreRecommendation(
        name=name,
        raw_capacity_mib=usable_mib,
        usable_capacity_mib=usable_mib,
        assigned_vms=tuple(vms),
        used_capacity_mib=used,
        utilization_pct=utilization_pct,
        total_iops=total_iops,
        vm_count=len(vms),
        workload_types=workload_types,
    )


class TestComputeMetrics:
    def test_basic_metrics(self) -> None:
        """Verify utilization, VM density, IOPS stats are computed correctly."""
        usable = 100 * _GiB
        vm1 = _make_vm("vm-01", "Database/Microsoft SQL", 50 * _GiB, peak_iops=200.0)
        vm2 = _make_vm("vm-02", "Database/Microsoft SQL", 25 * _GiB, peak_iops=100.0)
        ds = _make_ds("DS_01", [vm1, vm2], usable)
        metrics = _compute_metrics([ds])
        assert metrics.total_ds_count == 1
        assert abs(metrics.total_used_capacity_mib - 75 * _GiB) < 1.0
        assert abs(metrics.avg_utilization_pct - 75.0) < 0.1
        assert metrics.avg_vm_density == 2.0
        assert abs(metrics.total_iops_placed - 300.0) < 0.1

    def test_isolation_score(self) -> None:
        """Single-workload DS = 1.0, mixed = lower."""
        usable = 500 * _GiB
        vm_sql1 = _make_vm("vm-01", "Database/Microsoft SQL", 10 * _GiB)
        vm_sql2 = _make_vm("vm-02", "Database/Microsoft SQL", 10 * _GiB)
        vm_oracle = _make_vm("vm-03", "Database/Oracle", 10 * _GiB)
        # DS1: single workload type (SQL only)
        ds_single = _make_ds("DS_01", [vm_sql1, vm_sql2], usable)
        # DS2: mixed workload types
        ds_mixed = _make_ds("DS_02", [vm_sql1, vm_oracle], usable)
        # Two DSes: 1 single-workload → isolation_score = 0.5
        metrics = _compute_metrics([ds_single, ds_mixed])
        assert abs(metrics.isolation_score - 0.5) < 0.01

    def test_isolation_score_all_single(self) -> None:
        """All single-workload datastores give isolation_score = 1.0."""
        usable = 500 * _GiB
        vm1 = _make_vm("vm-01", "Database/Microsoft SQL", 10 * _GiB)
        vm2 = _make_vm("vm-02", "Database/Oracle", 10 * _GiB)
        ds1 = _make_ds("DS_01", [vm1], usable)
        ds2 = _make_ds("DS_02", [vm2], usable)
        metrics = _compute_metrics([ds1, ds2])
        assert abs(metrics.isolation_score - 1.0) < 0.01

    def test_snapshot_granularity_fine(self) -> None:
        """avg density <= 3 = 'fine'."""
        usable = 500 * _GiB
        vm1 = _make_vm("vm-01", "Database/Microsoft SQL", 10 * _GiB)
        vm2 = _make_vm("vm-02", "Database/Microsoft SQL", 10 * _GiB)
        ds = _make_ds("DS_01", [vm1, vm2], usable)  # 2 VMs = density 2
        metrics = _compute_metrics([ds])
        assert metrics.snapshot_granularity_rating == "fine"

    def test_snapshot_granularity_coarse(self) -> None:
        """avg density > 10 = 'coarse'."""
        usable = 500 * _GiB
        cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        vms = [_make_vm(f"vm-{i:02d}", cat, 1 * _GiB) for i in range(15)]
        ds = _make_ds("DS_01", vms, usable)  # 15 VMs = density 15
        metrics = _compute_metrics([ds])
        assert metrics.snapshot_granularity_rating == "coarse"

    def test_snapshot_granularity_medium(self) -> None:
        """avg density between 3 and 10 = 'medium'."""
        usable = 500 * _GiB
        cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        vms = [_make_vm(f"vm-{i:02d}", cat, 1 * _GiB) for i in range(7)]
        ds = _make_ds("DS_01", vms, usable)  # 7 VMs = density 7
        metrics = _compute_metrics([ds])
        assert metrics.snapshot_granularity_rating == "medium"

    def test_empty_datastores(self) -> None:
        """Empty list returns zeroed metrics without crashing."""
        metrics = _compute_metrics([])
        assert metrics.total_ds_count == 0
        assert metrics.total_raw_capacity_mib == 0.0
        assert metrics.total_used_capacity_mib == 0.0
        assert metrics.avg_utilization_pct == 0.0
        assert metrics.snapshot_granularity_rating == "fine"


# ---------------------------------------------------------------------------
# TestDefaultIOPS
# ---------------------------------------------------------------------------


class TestDefaultIOPS:
    def test_sql_vm_gets_500_iops(self) -> None:
        """Database/Microsoft SQL gets 500 IOPS default."""
        vm = _make_vm("vm-sql", "Database/Microsoft SQL", 100 * _GiB, peak_iops=0.0)
        result = _apply_default_iops(vm)
        assert result.peak_iops == 500.0

    def test_oracle_vm_gets_800_iops(self) -> None:
        """Database/Oracle gets 800 IOPS default."""
        vm = _make_vm("vm-ora", "Database/Oracle", 100 * _GiB, peak_iops=0.0)
        result = _apply_default_iops(vm)
        assert result.peak_iops == 800.0

    def test_unknown_gets_fallback(self) -> None:
        """Unknown/unmapped category gets fallback of 50 IOPS."""
        vm = _make_vm("vm-misc", "HealthCare/EMR", 100 * _GiB, peak_iops=0.0)
        result = _apply_default_iops(vm)
        assert result.peak_iops == 50.0

    def test_existing_iops_preserved(self) -> None:
        """VM with peak_iops > 0 is returned unchanged."""
        vm = _make_vm("vm-perf", "Database/Oracle", 100 * _GiB, peak_iops=1200.0)
        result = _apply_default_iops(vm)
        assert result.peak_iops == 1200.0
        assert result is vm  # exact same object, not a copy

    def test_avg_iops_is_70pct_of_peak(self) -> None:
        """avg_iops is estimated as 70% of peak IOPS for injected values."""
        vm = _make_vm("vm-sql", "Database/Microsoft SQL", 100 * _GiB, peak_iops=0.0)
        result = _apply_default_iops(vm)
        assert abs(result.avg_iops - result.peak_iops * 0.7) < 1e-9
