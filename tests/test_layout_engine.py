"""Unit tests for layout engine models, consolidation strategy, metrics, and default IOPS.

Tests use real objects and fixtures — no unittest.mock per project convention.
"""

from __future__ import annotations

from pathlib import Path

from store_predict.pipeline.calculation import CalculationSummary, VMCalculation
from store_predict.pipeline.layout_engine import (
    _apply_default_iops,
    _bfd_place,
    _compute_metrics,
    _consolidation_strategy,
    _performance_strategy,
    _uniform_strategy,
    generate_all_proposals,
)
from store_predict.pipeline.layout_models import (
    _DEFAULT_IOPS_HARDCODED,
    DatastoreRecommendation,
    PlacementConstraints,
    _load_iops_from_csv,
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


def _make_summary(
    vms: list[VMCalculation],
    has_performance_data: bool = True,
) -> CalculationSummary:
    """Build a minimal CalculationSummary from a list of VMCalculation objects."""
    total_vms = len(vms)
    total_provisioned = sum(v.provisioned_mib for v in vms)
    total_required = sum(v.required_mib for v in vms)
    total_in_use = sum(v.in_use_mib for v in vms)
    weighted_drr = sum(v.drr * v.provisioned_mib for v in vms) / total_provisioned if total_provisioned > 0 else 0.0
    return CalculationSummary(
        vm_calculations=vms,
        workload_groups=[],
        total_vms=total_vms,
        total_provisioned_mib=total_provisioned,
        total_in_use_mib=total_in_use,
        total_required_mib=total_required,
        weighted_avg_drr=weighted_drr,
        has_performance_data=has_performance_data,
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


# ---------------------------------------------------------------------------
# TestPerformanceStrategy
# ---------------------------------------------------------------------------


class TestPerformanceStrategy:
    def test_sap_hana_isolated(self) -> None:
        """VM with 'Database/SAP HANA(S4)' workload gets its own DS named DS_HANA_01."""
        c = PlacementConstraints()
        hana_vm = _make_vm("vm-hana", "Database/SAP HANA(S4)", 200 * _GiB, peak_iops=1000.0)
        proposal = _performance_strategy([hana_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]
        assert "DS_HANA_01" in ds_names

    def test_exchange_isolated(self) -> None:
        """VM with 'Exchange' in workload category gets DS_EXCHANGE_01."""
        c = PlacementConstraints()
        exch_vm = _make_vm("vm-exch", "Email/Exchange", 100 * _GiB, peak_iops=400.0)
        proposal = _performance_strategy([exch_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]
        assert "DS_EXCHANGE_01" in ds_names

    def test_high_iops_isolated(self) -> None:
        """VM with peak_iops > 5000 gets DS_ISOLATED_01."""
        c = PlacementConstraints()
        hot_vm = _make_vm("vm-hot", "Database/Microsoft SQL", 50 * _GiB, peak_iops=6000.0)
        proposal = _performance_strategy([hot_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]
        assert "DS_ISOLATED_01" in ds_names

    def test_large_vm_isolated(self) -> None:
        """VM with required_mib > 2 TiB gets DS_ISOLATED_01 (non-HANA, non-Exchange category)."""
        c = PlacementConstraints()
        # Use a category that doesn't match HANA/Exchange/Oracle naming
        big_vm = _make_vm("vm-big", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 3 * _TiB)
        proposal = _performance_strategy([big_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]
        assert "DS_ISOLATED_01" in ds_names

    def test_hot_tier_max_10_vms(self) -> None:
        """15 hot VMs: no DS should have more than 10 VMs (HOT tier constraint)."""
        c = PlacementConstraints()
        # SQL VMs with moderate size — classified as HOT (Database category)
        hot_vms = [
            _make_vm(f"vm-sql-{i:02d}", "Database/Microsoft SQL", 100 * _GiB, peak_iops=200.0) for i in range(15)
        ]
        proposal = _performance_strategy(hot_vms, c)
        hot_datastores = [ds for ds in proposal.datastores if ds.name.startswith("DS_HOT")]
        assert len(hot_datastores) >= 2, "15 hot VMs at max 10/DS should create at least 2 DS"
        assert all(ds.vm_count <= 10 for ds in hot_datastores), "No HOT DS should exceed 10 VMs"

    def test_tier_classification(self) -> None:
        """SQL VM = HOT tier, 200 IOPS VM = WARM, 50 IOPS VM = COLD."""
        c = PlacementConstraints()
        sql_vm = _make_vm("vm-sql", "Database/Microsoft SQL", 50 * _GiB, peak_iops=600.0)
        warm_vm = _make_vm("vm-warm", "File/General Purpose", 50 * _GiB, peak_iops=200.0)
        _vm_cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        cold_vm = _make_vm("vm-cold", _vm_cat, 50 * _GiB, peak_iops=50.0)

        proposal = _performance_strategy([sql_vm, warm_vm, cold_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]

        assert any(name.startswith("DS_HOT") for name in ds_names), "SQL VM should land in DS_HOT"
        assert any(name.startswith("DS_WARM") for name in ds_names), "200 IOPS VM should land in DS_WARM"
        assert any(name.startswith("DS_COLD") for name in ds_names), "50 IOPS VM should land in DS_COLD"

    def test_anti_affinity_natural(self) -> None:
        """Database VMs and VDI VMs should NOT share any datastore."""
        c = PlacementConstraints()
        db_vms = [_make_vm(f"vm-sql-{i:02d}", "Database/Microsoft SQL", 50 * _GiB, peak_iops=600.0) for i in range(5)]
        vdi_vms = [
            _make_vm(f"vm-vdi-{i:02d}", "VDI/Full Clone / MCS (Citrix)", 20 * _GiB, peak_iops=30.0) for i in range(5)
        ]

        proposal = _performance_strategy(db_vms + vdi_vms, c)

        for ds in proposal.datastores:
            has_db = any("Database" in vm.workload_category for vm in ds.assigned_vms)
            has_vdi = any("VDI" in vm.workload_category for vm in ds.assigned_vms)
            assert not (has_db and has_vdi), f"DS {ds.name} co-locates Database and VDI VMs (anti-affinity violation)"

    def test_isolated_ds_sized_to_vm(self) -> None:
        """Isolated DS raw capacity equals vm.required_mib / constraints.usable_ratio."""
        c = PlacementConstraints()
        hana_vm = _make_vm("vm-hana", "Database/SAP HANA(S4)", 500 * _GiB, peak_iops=1000.0)
        proposal = _performance_strategy([hana_vm], c)

        hana_ds = next(ds for ds in proposal.datastores if ds.name.startswith("DS_HANA"))
        expected_raw = hana_vm.required_mib / c.usable_ratio
        assert abs(hana_ds.raw_capacity_mib - expected_raw) < 1.0, (
            f"Isolated DS should be sized to VM: expected {expected_raw:.1f}, got {hana_ds.raw_capacity_mib:.1f}"
        )

    def test_naming_prefixes(self) -> None:
        """HOT tier DS names start with DS_HOT, WARM with DS_WARM, COLD with DS_COLD."""
        c = PlacementConstraints()
        # Create one VM in each tier to ensure all tier datastores are created
        hot_vm = _make_vm("vm-hot", "Database/Oracle", 50 * _GiB, peak_iops=800.0)
        warm_vm = _make_vm("vm-warm", "File/General Purpose", 50 * _GiB, peak_iops=200.0)
        _vm_cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        cold_vm = _make_vm("vm-cold", _vm_cat, 50 * _GiB, peak_iops=10.0)

        proposal = _performance_strategy([hot_vm, warm_vm, cold_vm], c)
        ds_names = [ds.name for ds in proposal.datastores]

        assert any(n.startswith("DS_HOT") for n in ds_names)
        assert any(n.startswith("DS_WARM") for n in ds_names)
        assert any(n.startswith("DS_COLD") for n in ds_names)


# ---------------------------------------------------------------------------
# TestUniformStrategy
# ---------------------------------------------------------------------------


class TestUniformStrategy:
    def test_basic_uniform(self) -> None:
        """10 VMs distributed across the calculated DS count — all VMs are placed."""
        c = PlacementConstraints()
        vms = [
            _make_vm(f"vm-{i:02d}", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 100 * _GiB)
            for i in range(10)
        ]
        proposal = _uniform_strategy(vms, c)
        total_vms_placed = sum(ds.vm_count for ds in proposal.datastores)
        assert total_vms_placed == 10, "All 10 VMs should be placed"

    def test_naming_convention(self) -> None:
        """DS names follow DS_UNIFORM_01, DS_UNIFORM_02, etc."""
        c = PlacementConstraints()
        vms = [
            _make_vm(f"vm-{i:02d}", "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email", 100 * _GiB)
            for i in range(5)
        ]
        proposal = _uniform_strategy(vms, c)
        for ds in proposal.datastores:
            assert ds.name.startswith("DS_UNIFORM_"), f"Unexpected DS name: {ds.name}"

    def test_balanced_distribution(self) -> None:
        """Max utilization difference between any two DS should be < 30%."""
        c = PlacementConstraints()
        # Create VMs of varying sizes to test LPT balancing
        _vm_cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        vms = [_make_vm(f"vm-{i:02d}", _vm_cat, (i + 1) * 50 * _GiB) for i in range(10)]
        proposal = _uniform_strategy(vms, c)

        if len(proposal.datastores) >= 2:
            util_values = [ds.utilization_pct for ds in proposal.datastores]
            max_diff = max(util_values) - min(util_values)
            assert max_diff < 30.0, f"Utilization imbalance too high: {max_diff:.1f}%"

    def test_iops_driven_ds_count(self) -> None:
        """High-IOPS VMs force more datastores than capacity alone would require."""
        # Use large IOPS budget constraint — force IOPS to drive count
        c = PlacementConstraints(iops_budget_per_ds=1000.0)
        # 10 VMs each with 200 IOPS → total 2000 IOPS → need ceil(2000/1000) = 2 DS for IOPS
        # But capacity: each VM is 10 GiB, total 100 GiB / 2.7 TiB → only 1 DS needed for capacity
        _vm_cat = "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"
        vms = [_make_vm(f"vm-{i:02d}", _vm_cat, 10 * _GiB, peak_iops=200.0) for i in range(10)]
        proposal = _uniform_strategy(vms, c)
        # IOPS forces 2 DS (2000 / 1000), capacity only needs 1 DS
        assert proposal.metrics.total_ds_count >= 2, "IOPS constraint should drive DS count above capacity-only minimum"

    def test_empty_vms(self) -> None:
        """Empty VM list returns proposal with 0 datastores."""
        c = PlacementConstraints()
        proposal = _uniform_strategy([], c)
        assert proposal.strategy_name == "uniform"
        assert proposal.metrics.total_ds_count == 0
        assert len(proposal.datastores) == 0

    def test_no_datastore_exceeds_capacity(self) -> None:
        """Regression: uniform strategy must never produce >100% utilization."""
        # Create VMs with very uneven sizes — one large VM close to usable capacity
        constraints = PlacementConstraints(
            max_ds_capacity_mib=4 * 1024 * 1024,
            snapshot_reserve_pct=15.0,
            growth_margin_pct=20.0,
        )
        usable = constraints.usable_capacity_mib  # ~2.72 TiB
        vms = [
            _make_vm("big1", "Email", required_mib=usable * 0.95),
            _make_vm("big2", "Email", required_mib=usable * 0.90),
            _make_vm("big3", "Email", required_mib=usable * 0.85),
            _make_vm("small1", "Email", required_mib=usable * 0.20),
            _make_vm("small2", "Email", required_mib=usable * 0.15),
        ]
        result = _uniform_strategy(vms, constraints)
        for ds in result.datastores:
            assert ds.utilization_pct <= 100.0, f"{ds.name} has {ds.utilization_pct:.1f}% utilization (>100%)"

    def test_oversized_vm_gets_dedicated_datastore(self) -> None:
        """Oversized VMs should get DS_UNIFORM_OVER_ datastores, not overflow standard bins."""
        constraints = PlacementConstraints(max_ds_capacity_mib=4 * 1024 * 1024)
        usable = constraints.usable_capacity_mib
        vms = [
            _make_vm("huge", "Email", required_mib=usable * 2.5),  # 2.5x usable — definitely oversized
            _make_vm("normal1", "Email", required_mib=usable * 0.3),
            _make_vm("normal2", "Email", required_mib=usable * 0.3),
        ]
        result = _uniform_strategy(vms, constraints)
        over_ds = [ds for ds in result.datastores if "_OVER_" in ds.name]
        assert len(over_ds) == 1
        assert over_ds[0].vm_count == 1
        assert over_ds[0].assigned_vms[0].vm_name == "huge"
        # Standard bins should not be overloaded
        for ds in result.datastores:
            if "_OVER_" not in ds.name:
                assert ds.utilization_pct <= 100.0


# ---------------------------------------------------------------------------
# TestGenerateAllProposals
# ---------------------------------------------------------------------------


class TestGenerateAllProposals:
    def test_returns_three_proposals(self) -> None:
        """generate_all_proposals always returns exactly 3 proposals."""
        vms = [_make_vm("vm-01", "Database/Microsoft SQL", 100 * _GiB, peak_iops=500.0)]
        summary = _make_summary(vms)
        proposals = generate_all_proposals(summary)
        assert len(proposals) == 3

    def test_strategy_names(self) -> None:
        """Strategy names are exactly ['consolidation', 'performance', 'uniform'] in order."""
        vms = [_make_vm("vm-01", "Database/Oracle", 200 * _GiB, peak_iops=800.0)]
        summary = _make_summary(vms)
        proposals = generate_all_proposals(summary)
        names = [p.strategy_name for p in proposals]
        assert names == ["consolidation", "performance", "uniform"]

    def test_empty_summary(self) -> None:
        """Empty vm_calculations returns 3 proposals each with 0 datastores."""
        summary = _make_summary([])
        proposals = generate_all_proposals(summary)
        assert len(proposals) == 3
        for p in proposals:
            assert p.metrics.total_ds_count == 0

    def test_default_iops_applied_for_rvtools(self) -> None:
        """For has_performance_data=False (RVTools), zero-IOPS VMs get default IOPS injected."""
        # SQL VM with zero IOPS — simulate RVTools export (no performance data)
        vms = [
            _make_vm("vm-sql", "Database/Microsoft SQL", 100 * _GiB, peak_iops=0.0),
        ]
        summary = _make_summary(vms, has_performance_data=False)
        proposals = generate_all_proposals(summary)
        # With default IOPS injected (500 for SQL), IOPS constraint should be exercised
        # The key invariant: we get 3 proposals successfully, and the performance strategy
        # sees non-zero IOPS (SQL at 500 > 500 threshold is not > 500, so HOT tier via Database check)
        assert len(proposals) == 3
        # Each proposal should have placed all VMs
        for p in proposals:
            total = sum(ds.vm_count for ds in p.datastores)
            assert total == 1, f"Strategy {p.strategy_name} should place 1 VM, got {total}"

    def test_real_iops_preserved_for_liveoptics(self) -> None:
        """For has_performance_data=True (LiveOptics), original IOPS are preserved."""
        # VM with real IOPS measurement — Oracle workload with very high IOPS
        # Oracle VMs with peak_iops > 5000 are isolated with DS_ORA prefix
        vms = [
            _make_vm("vm-perf", "Database/Oracle", 200 * _GiB, peak_iops=5500.0),
        ]
        summary = _make_summary(vms, has_performance_data=True)
        proposals = generate_all_proposals(summary)
        assert len(proposals) == 3

        # With real IOPS > 5000, VM should be in an isolated DS in performance strategy
        # Oracle workloads get DS_ORA prefix, not DS_ISOLATED
        perf_proposal = next(p for p in proposals if p.strategy_name == "performance")
        ds_names = [ds.name for ds in perf_proposal.datastores]
        assert "DS_ORA_01" in ds_names, "High-IOPS Oracle VM should be isolated with DS_ORA prefix"

    def test_consolidation_fewest_datastores(self) -> None:
        """Consolidation should produce <= datastores than uniform and performance."""
        # Create a mix of VMs that would be separated by performance strategy
        vms = [_make_vm(f"vm-sql-{i:02d}", "Database/Microsoft SQL", 100 * _GiB, peak_iops=300.0) for i in range(5)] + [
            _make_vm(f"vm-vdi-{i:02d}", "VDI/Full Clone / MCS (Citrix)", 20 * _GiB, peak_iops=30.0) for i in range(10)
        ]
        summary = _make_summary(vms)
        proposals = generate_all_proposals(summary)

        consolidation = next(p for p in proposals if p.strategy_name == "consolidation")
        performance = next(p for p in proposals if p.strategy_name == "performance")
        uniform = next(p for p in proposals if p.strategy_name == "uniform")

        assert consolidation.metrics.total_ds_count <= performance.metrics.total_ds_count, (
            f"Consolidation ({consolidation.metrics.total_ds_count}) should use <= DS than "
            f"performance ({performance.metrics.total_ds_count})"
        )
        assert consolidation.metrics.total_ds_count <= uniform.metrics.total_ds_count, (
            f"Consolidation ({consolidation.metrics.total_ds_count}) should use <= DS than "
            f"uniform ({uniform.metrics.total_ds_count})"
        )

    def test_default_constraints_used(self) -> None:
        """When constraints=None, defaults are applied and result is valid."""
        vms = [_make_vm("vm-01", "Database/Microsoft SQL", 100 * _GiB, peak_iops=500.0)]
        summary = _make_summary(vms)
        # Pass constraints=None explicitly to exercise the default-injection path
        proposals = generate_all_proposals(summary, constraints=None)
        assert len(proposals) == 3
        for p in proposals:
            # All VMs should be placed
            total = sum(ds.vm_count for ds in p.datastores)
            assert total == 1


# ---------------------------------------------------------------------------
# TestLoadIOPSFromCSV
# ---------------------------------------------------------------------------


class TestLoadIOPSFromCSV:
    def test_load_iops_from_csv_returns_dict(self) -> None:
        """CSV loader returns dict with at least 8 entries and correct SQL value."""
        result = _load_iops_from_csv()
        assert isinstance(result, dict)
        assert len(result) >= 8
        assert result["Database/Microsoft SQL"] == 500.0

    def test_load_iops_from_csv_fallback_when_missing(self) -> None:
        """Missing CSV path returns _DEFAULT_IOPS_HARDCODED values unchanged."""
        result = _load_iops_from_csv(Path("/nonexistent/IOPS.csv"))
        assert result == _DEFAULT_IOPS_HARDCODED

    def test_load_iops_from_csv_strips_whitespace(self, tmp_path: Path) -> None:
        """Keys and values with surrounding whitespace are stripped before parsing."""
        csv_file = tmp_path / "IOPS.csv"
        csv_file.write_text("Workload Category;IOPS Estimate\n Database/Oracle ; 800 \n", encoding="utf-8")
        result = _load_iops_from_csv(csv_file)
        assert "Database/Oracle" in result
        assert result["Database/Oracle"] == 800.0

    def test_load_iops_from_csv_skips_bad_rows(self, tmp_path: Path) -> None:
        """Rows with non-numeric IOPS values are skipped; valid rows are loaded."""
        csv_file = tmp_path / "IOPS.csv"
        csv_file.write_text(
            "Workload Category;IOPS Estimate\nDatabase/Oracle;800\nBadCategory;notanumber\n",
            encoding="utf-8",
        )
        result = _load_iops_from_csv(csv_file)
        assert "Database/Oracle" in result
        assert result["Database/Oracle"] == 800.0
        assert "BadCategory" not in result

    def test_load_iops_from_csv_empty_file_uses_fallback(self, tmp_path: Path) -> None:
        """CSV with only a header row (no data) returns _DEFAULT_IOPS_HARDCODED."""
        csv_file = tmp_path / "IOPS.csv"
        csv_file.write_text("Workload Category;IOPS Estimate\n", encoding="utf-8")
        result = _load_iops_from_csv(csv_file)
        assert result == _DEFAULT_IOPS_HARDCODED
