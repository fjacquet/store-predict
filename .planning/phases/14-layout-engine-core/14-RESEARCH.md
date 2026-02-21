# Phase 14: Layout Engine Core - Research

**Researched:** 2026-02-21
**Domain:** Pure-Python multi-dimensional bin-packing algorithms, VMFS datastore layout, Dell PowerStore placement heuristics
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-001 | Data models (`PlacementConstraints`, `DatastoreRecommendation`, `LayoutProposal`, `LayoutMetrics`) | Dataclass patterns verified against existing `VMCalculation`/`CalculationSummary` in `pipeline/calculation.py`; frozen dataclasses are the project standard |
| REQ-002 | Consolidation strategy — multi-dimensional BFD, minimize datastore count | BFD algorithm confirmed in ADR-055; sorting key `max(capacity_ratio, iops_ratio)` and "least remaining space" bin selection documented |
| REQ-003 | Performance strategy — Phase 0 isolation + tier classification + per-tier BFD + anti-affinity | Three-phase design confirmed in ADR-058 and REQ-003; isolation thresholds configurable |
| REQ-004 | Uniform strategy — LPT across pre-computed equal-sized datastores | LPT variant confirmed in ADR-055; datastore count formula `max(ceil(total_cap/usable), ceil(total_iops/budget))` |
| REQ-005 | Comparison metrics: utilization, isolation score, snapshot granularity rating, IOPS stats | Metric definitions fully specified in REQUIREMENTS.md REQ-005 |
| REQ-006 | Datastore naming convention encoding strategy and workload | Naming patterns fully specified: `DS_CONSOL_01`, `DS_HOT_SQL_01`, `DS_UNIFORM_01` etc. |
| REQ-014 | Default IOPS estimates when no LiveOptics performance data (RVTools import) | IOPS defaults table defined in REQUIREMENTS.md REQ-014; `has_performance_data` flag already in `CalculationSummary` |
</phase_requirements>

---

## Summary

Phase 14 implements the pure-Python layout engine core — the computational heart of the v3.0 milestone. No UI is touched. The engine accepts a `CalculationSummary` (already produced by the existing pipeline) plus `PlacementConstraints` and returns three `LayoutProposal` objects, one per strategy.

The algorithmic approach is fully decided (ADR-055, ADR-056, ADR-057, ADR-058): multi-dimensional BFD for Consolidation and Performance, LPT for Uniform, with a Phase 0 isolation pass in Performance. The implementation is pure stdlib Python — no new dependencies, no numpy, no OR-Tools. The engine lives in a new `pipeline/layout_engine.py` module, maintaining the existing contract that `pipeline/` is UI-free and fully testable.

The key implementation insight is that all three strategies share a single `_bfd_place()` core function and differ only in how VMs are pre-sorted, grouped, and filtered before placement. This makes the engine small (estimated ~300 LOC) and easy to test in isolation.

**Primary recommendation:** Implement `pipeline/layout_engine.py` as a pure function module with `generate_all_proposals(summary, constraints) -> list[LayoutProposal]` as the single public entry point. Internal helpers `_consolidation_strategy()`, `_performance_strategy()`, `_uniform_strategy()`, and `_bfd_place()` handle each strategy's logic. Keep all dataclasses in the same module or a companion `pipeline/layout_models.py`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.12 | Domain model definitions | Project standard — all pipeline models use `@dataclass(frozen=True)` |
| Python stdlib `math` | 3.12 | `ceil()` for uniform DS count, ratio calculations | Already used in `calculation.py` |
| Python stdlib `collections` | 3.12 | `defaultdict` for grouping VMs by tier/workload | Already used in `calculation.py` |
| Python stdlib `enum` | 3.12 | `StrEnum` for tier names (Hot/Warm/Cold), strategy names | Already used in `config.py` (`StorageModel`) |

### No New Dependencies

NFR-002 is explicit: no PuLP, no OR-Tools, no numpy. The layout engine is 100% stdlib + existing deps.

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Module Structure

```
src/store_predict/pipeline/
    layout_models.py     # PlacementConstraints, DatastoreRecommendation, LayoutProposal, LayoutMetrics
    layout_engine.py     # generate_all_proposals() + strategy functions + _bfd_place()
```

Alternative: single file `pipeline/layout_engine.py` with models inline. Given the number of dataclasses (4 models), a companion `layout_models.py` is cleaner and mirrors the existing `models.py` pattern.

### Recommended Project Structure Addition

```
src/store_predict/pipeline/
    __init__.py
    ingestion.py         # existing
    classification.py    # existing
    calculation.py       # existing
    models.py            # existing (VMRecord, FileFormat)
    layout_models.py     # NEW — layout domain dataclasses
    layout_engine.py     # NEW — placement algorithms
    validation.py        # existing
    errors.py            # existing
    parsers/             # existing

tests/
    test_layout_engine.py    # NEW — unit tests for all strategies
```

### Pattern 1: Frozen Dataclass Models

**What:** All domain objects are `@dataclass(frozen=True)` with explicit type annotations. Lists inside use `field(default_factory=list)` — frozen dataclasses cannot have mutable default arguments.

**When to use:** Every model in this phase. Consistent with `VMCalculation`, `CalculationSummary`, `WorkloadGroupResult`.

**Example:**

```python
# Source: existing pipeline/calculation.py pattern
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PlacementConstraints:
    max_ds_capacity_mib: float = 4 * 1024 * 1024   # 4 TiB in MiB
    max_vms_per_ds: int = 25
    iops_budget_per_ds: float = 100_000.0
    snapshot_reserve_pct: float = 15.0              # 0-100
    growth_margin_pct: float = 20.0                 # 0-100

    @property
    def usable_ratio(self) -> float:
        """Fraction of raw capacity available for VM data."""
        return (1.0 - self.snapshot_reserve_pct / 100.0) * (1.0 - self.growth_margin_pct / 100.0)

    @property
    def usable_capacity_mib(self) -> float:
        return self.max_ds_capacity_mib * self.usable_ratio
```

### Pattern 2: Mutable Builder + Frozen Output

**What:** During BFD placement, datastores must accumulate VMs (mutable state). Use an internal mutable `_DatastoreBuilder` dataclass during the algorithm, then convert to frozen `DatastoreRecommendation` at the end.

**When to use:** Every strategy's internal placement loop.

**Example:**

```python
from dataclasses import dataclass, field

@dataclass
class _DatastoreBuilder:
    """Mutable state during BFD placement. NOT frozen — accumulates VMs."""
    name: str
    raw_capacity_mib: float
    usable_capacity_mib: float
    assigned_vms: list[VMCalculation] = field(default_factory=list)
    used_capacity_mib: float = 0.0
    total_iops: float = 0.0

    def can_fit(self, vm: VMCalculation, max_vms: int, iops_budget: float) -> bool:
        fits_capacity = self.used_capacity_mib + vm.required_mib <= self.usable_capacity_mib
        fits_iops = self.total_iops + vm.peak_iops <= iops_budget
        fits_count = len(self.assigned_vms) < max_vms
        return fits_capacity and fits_iops and fits_count

    def add_vm(self, vm: VMCalculation) -> None:
        self.assigned_vms.append(vm)
        self.used_capacity_mib += vm.required_mib
        self.total_iops += vm.peak_iops

    def to_recommendation(self) -> DatastoreRecommendation:
        utilization_pct = (self.used_capacity_mib / self.usable_capacity_mib * 100.0
                           if self.usable_capacity_mib > 0 else 0.0)
        return DatastoreRecommendation(
            name=self.name,
            raw_capacity_mib=self.raw_capacity_mib,
            usable_capacity_mib=self.usable_capacity_mib,
            assigned_vms=tuple(self.assigned_vms),
            used_capacity_mib=self.used_capacity_mib,
            utilization_pct=utilization_pct,
            total_iops=self.total_iops,
            vm_count=len(self.assigned_vms),
        )
```

### Pattern 3: BFD Core Algorithm

**What:** Sort VMs descending by demand score, place each in the "tightest-fitting" bin that can still accept it. When no bin fits, open a new one.

**When to use:** Consolidation strategy directly; Performance strategy per-tier.

**Example:**

```python
def _bfd_place(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
    name_prefix: str,
    max_vms_override: int | None = None,
) -> list[_DatastoreBuilder]:
    """Multi-dimensional Best Fit Decreasing placement.

    Sorts VMs by max(capacity_ratio, iops_ratio) descending.
    Places each VM into the tightest bin that fits all three constraints.
    Opens a new bin when no existing bin fits.
    """
    max_vms = max_vms_override if max_vms_override is not None else constraints.max_vms_per_ds
    usable = constraints.usable_capacity_mib
    iops_budget = constraints.iops_budget_per_ds

    # Compute demand score per VM
    def demand_score(vm: VMCalculation) -> float:
        cap_ratio = vm.required_mib / usable if usable > 0 else 0.0
        iops_ratio = vm.peak_iops / iops_budget if iops_budget > 0 else 0.0
        return max(cap_ratio, iops_ratio)

    sorted_vms = sorted(vms, key=demand_score, reverse=True)
    bins: list[_DatastoreBuilder] = []

    for vm in sorted_vms:
        # Find best-fit bin: least remaining capacity that still fits
        best_bin: _DatastoreBuilder | None = None
        best_remaining = float("inf")

        for b in bins:
            if b.can_fit(vm, max_vms, iops_budget):
                remaining = b.usable_capacity_mib - b.used_capacity_mib
                if remaining < best_remaining:
                    best_bin = b
                    best_remaining = remaining

        if best_bin is None:
            # Open new datastore
            idx = len(bins) + 1
            new_bin = _DatastoreBuilder(
                name=f"{name_prefix}_{idx:02d}",
                raw_capacity_mib=constraints.max_ds_capacity_mib,
                usable_capacity_mib=usable,
            )
            new_bin.add_vm(vm)
            bins.append(new_bin)
        else:
            best_bin.add_vm(vm)

    return bins
```

### Pattern 4: LPT Algorithm for Uniform Strategy

**What:** Pre-compute datastore count; assign each VM (sorted descending by size) to the least-loaded datastore.

**When to use:** Uniform strategy only.

**Example:**

```python
import math

def _uniform_strategy(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> list[_DatastoreBuilder]:
    if not vms:
        return []

    total_cap = sum(v.required_mib for v in vms)
    total_iops = sum(v.peak_iops for v in vms)
    usable = constraints.usable_capacity_mib

    ds_count = max(
        math.ceil(total_cap / usable) if usable > 0 else 1,
        math.ceil(total_iops / constraints.iops_budget_per_ds) if constraints.iops_budget_per_ds > 0 else 1,
        1,
    )

    bins = [
        _DatastoreBuilder(
            name=f"DS_UNIFORM_{i + 1:02d}",
            raw_capacity_mib=constraints.max_ds_capacity_mib,
            usable_capacity_mib=usable,
        )
        for i in range(ds_count)
    ]

    # LPT: sort descending, assign to least-loaded bin
    sorted_vms = sorted(vms, key=lambda v: v.required_mib, reverse=True)
    for vm in sorted_vms:
        least_loaded = min(bins, key=lambda b: b.used_capacity_mib)
        least_loaded.add_vm(vm)

    return bins
```

### Pattern 5: Performance Strategy Phase 0 Isolation

**What:** Extract mission-critical VMs before BFD. Each isolated VM gets a dedicated datastore sized to the VM (not the global max DS size).

**When to use:** Performance strategy only, before tier classification.

**Example:**

```python
_ISOLATION_WORKLOADS = frozenset({"Database/SAP HANA(S4)", "Email"})
_ISOLATION_CAPACITY_THRESHOLD_MIB = 2 * 1024 * 1024   # 2 TiB
_ISOLATION_IOPS_THRESHOLD = 5_000.0

def _is_mission_critical(vm: VMCalculation) -> bool:
    """Return True if VM must be isolated to its own dedicated datastore."""
    if any(kw in vm.workload_category for kw in ("SAP HANA", "Exchange")):
        return True
    if vm.required_mib > _ISOLATION_CAPACITY_THRESHOLD_MIB:
        return True
    if vm.peak_iops > _ISOLATION_IOPS_THRESHOLD:
        return True
    return False

def _isolate_vms(
    vms: list[VMCalculation],
    constraints: PlacementConstraints,
) -> tuple[list[_DatastoreBuilder], list[VMCalculation]]:
    """Phase 0: isolate mission-critical VMs into 1:1 datastores.

    Returns (isolated_bins, remaining_vms).
    Isolated datastores are sized to the individual VM, not the global max DS size.
    """
    isolated_bins: list[_DatastoreBuilder] = []
    remaining: list[VMCalculation] = []
    counters: dict[str, int] = {}

    for vm in vms:
        if _is_mission_critical(vm):
            # Determine naming suffix from workload
            if "SAP HANA" in vm.workload_category:
                prefix = "DS_HANA"
            elif "Exchange" in vm.workload_category:
                prefix = "DS_EXCHANGE"
            elif "Oracle" in vm.workload_category:
                prefix = "DS_ORA"
            else:
                prefix = "DS_ISOLATED"
            counters[prefix] = counters.get(prefix, 0) + 1
            ds_name = f"{prefix}_{counters[prefix]:02d}"

            # Size to VM, not global max
            vm_raw_mib = vm.required_mib / constraints.usable_ratio
            b = _DatastoreBuilder(
                name=ds_name,
                raw_capacity_mib=vm_raw_mib,
                usable_capacity_mib=vm.required_mib,
            )
            b.add_vm(vm)
            isolated_bins.append(b)
        else:
            remaining.append(vm)

    return isolated_bins, remaining
```

### Pattern 6: Metrics Computation

**What:** After all strategies produce proposals, compute `LayoutMetrics` from the list of `DatastoreRecommendation` objects.

**Example:**

```python
def _compute_metrics(datastores: list[DatastoreRecommendation]) -> LayoutMetrics:
    if not datastores:
        return LayoutMetrics(...)  # zeroed struct

    ds_count = len(datastores)
    utilizations = [ds.utilization_pct for ds in datastores]
    vm_densities = [ds.vm_count for ds in datastores]
    iops_values = [ds.total_iops for ds in datastores]

    # Isolation score: ratio of datastores with single workload type
    single_workload_ds = sum(
        1 for ds in datastores
        if len({v.workload_category for v in ds.assigned_vms}) <= 1
    )
    isolation_score = single_workload_ds / ds_count if ds_count > 0 else 0.0

    # Snapshot granularity rating: based on avg VM density
    avg_density = sum(vm_densities) / ds_count
    if avg_density <= 3:
        snapshot_granularity = "fine"
    elif avg_density <= 10:
        snapshot_granularity = "medium"
    else:
        snapshot_granularity = "coarse"

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
        max_iops_single_ds=max(iops_values, default=0.0),
        iops_headroom_pct=(
            (1.0 - max(iops_values, default=0.0) / 100_000.0) * 100.0
            if iops_values else 100.0
        ),
        isolation_score=isolation_score,
        snapshot_granularity_rating=snapshot_granularity,
    )
```

### Pattern 7: Default IOPS Estimates (REQ-014)

**What:** When `CalculationSummary.has_performance_data` is False (RVTools import), inject workload-based IOPS estimates before running the placement algorithms.

**When to use:** Called by `generate_all_proposals()` before any strategy when `not summary.has_performance_data`.

**Example:**

```python
# In layout_models.py or a constants section
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
_DEFAULT_IOPS_FALLBACK = 50.0

def _apply_default_iops(vm: VMCalculation) -> VMCalculation:
    """Return a new VMCalculation with estimated IOPS when no performance data."""
    if vm.peak_iops > 0:
        return vm  # already has real data
    estimated = DEFAULT_IOPS_BY_WORKLOAD.get(vm.workload_category, _DEFAULT_IOPS_FALLBACK)
    # Return a new instance since VMCalculation is frozen
    return VMCalculation(
        vm_name=vm.vm_name,
        workload_category=vm.workload_category,
        provisioned_mib=vm.provisioned_mib,
        in_use_mib=vm.in_use_mib,
        drr=vm.drr,
        required_mib=vm.required_mib,
        peak_iops=estimated,
        avg_iops=estimated * 0.7,  # estimate avg as 70% of peak
        peak_throughput_mbs=vm.peak_throughput_mbs,
        iops_8k_equivalent=vm.iops_8k_equivalent,
    )
```

### Anti-Patterns to Avoid

- **Mutating frozen dataclasses:** `VMCalculation` is frozen. Use `dataclasses.replace(vm, peak_iops=...)` or construct a new instance explicitly.
- **Importing from `ui/` in `pipeline/`:** The layout engine must never import from `ui/` — it must remain fully testable without NiceGUI.
- **Using `app.storage.tab` inside the engine:** `generate_all_proposals()` accepts `PlacementConstraints` as a parameter. The caller (UI layer) reads constraints from session storage and passes them in.
- **Float equality comparisons for capacity:** Use `<=` with a small epsilon or simple `<=` (floats from MiB math are safe here; no irrational numbers).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BFD sorting | Custom priority queue | Standard `sorted()` + `min()` | O(n*m) is fast enough for 1,000 VMs (NFR-001); heapq adds complexity for no gain |
| Dataclass serialization | Custom `to_dict()` | `dataclasses.asdict()` | Built-in, handles nested dataclasses and lists |
| Isolation workload matching | Regex engine | Simple `in` substring check | Workload categories are normalized strings like "Database/SAP HANA(S4)"; no fuzzy matching needed |
| Metrics statistics | numpy/statistics | `sum() / len()`, `min()`, `max()` | Pure stdlib is explicit and dependency-free; NFR-002 |

**Key insight:** The placement algorithms are O(n × m) loops over Python lists — no fancy data structures needed. Premature optimization with heaps or sorted containers would add code complexity with no measurable gain for the target scale (≤1,000 VMs, ≤50 datastores).

---

## Common Pitfalls

### Pitfall 1: VM Larger Than Maximum Datastore Capacity

**What goes wrong:** A VM with `required_mib` greater than `usable_capacity_mib` (e.g., a 5 TiB Oracle DB on a 4 TiB max-DS config) can never fit into any datastore in the standard BFD loop. The loop opens infinite new datastores, or if the algorithm has a guard, silently drops the VM.

**Why it happens:** The constraint parameters are user-tunable. A user might set max DS to 2 TiB but have a 3 TiB VM.

**How to avoid:** Before running BFD, separate "oversized" VMs. Each oversized VM gets a dedicated datastore sized to the VM (same logic as the isolation pass). Emit a warning flag in `LayoutMetrics` indicating how many VMs were oversized.

**Warning signs:** DS count equals VM count (every VM forced to its own datastore), or `LayoutMetrics.total_ds_count` spikes unexpectedly.

### Pitfall 2: Zero VMs Edge Case

**What goes wrong:** `generate_all_proposals()` called with an empty `vm_calculations` list crashes on `max()`, `min()`, or division by zero.

**Why it happens:** The UI may call the engine before any file is uploaded or after all VMs are filtered out.

**How to avoid:** Guard at the start of `generate_all_proposals()`: if `not vms`, return three proposals with empty datastore lists. The metrics computation must also handle empty lists — use `default=0.0` in `max()` calls.

### Pitfall 3: IOPS Budget Ignored When has_performance_data Is False

**What goes wrong:** RVTools imports set `peak_iops=0` for all VMs. The BFD `can_fit()` method sees `0 <= budget` as always true, so IOPS never constrains placement. The Uniform strategy's DS count becomes just the capacity ceiling with no IOPS-driven floor — potentially producing too few datastores for high-IOPS workloads.

**Why it happens:** Developers test with LiveOptics data. RVTools path is not covered in tests with realistic IOPS estimates.

**How to avoid:** Apply `_apply_default_iops()` unconditionally when `not summary.has_performance_data`. Test both paths. Add an assertion in `TestConsolidationStrategy` that IOPS constraints are applied even for RVTools-only data.

### Pitfall 4: Anti-Affinity Not Enforced After Tier Placement

**What goes wrong:** The Performance strategy classifies Database VMs as Hot tier and VDI VMs as Warm tier. If both tiers get packed via BFD into the same pool of datastores (shared `bins` list), a Warm-tier VDI VM might end up co-located with a Hot-tier Database VM.

**Why it happens:** The tier-BFD approach uses separate `_bfd_place()` calls per tier. Anti-affinity is naturally enforced if each tier has its own independent list of bins. The pitfall occurs if bins are accidentally shared across tier calls.

**How to avoid:** Each tier call to `_bfd_place()` starts with a fresh empty `bins: list[_DatastoreBuilder] = []`. Never pass an existing bins list from one tier into the next tier's BFD call.

### Pitfall 5: Datastore Naming Counter Resets Across Strategies

**What goes wrong:** If a shared counter is used for DS naming, a Consolidation datastore `DS_CONSOL_03` might conflict with a Performance datastore from a previous run that also used index 3.

**Why it happens:** Global counters or class-level state shared between strategy calls.

**How to avoid:** Each strategy function maintains its own local counter (just `len(bins) + 1` during bin creation). No global state. Strategies are pure functions.

### Pitfall 6: Frozen Dataclass with List Field

**What goes wrong:** `@dataclass(frozen=True)` with `assigned_vms: list[VMCalculation] = []` raises `ValueError: mutable default is not allowed`.

**Why it happens:** Python's dataclass system prevents mutable defaults in frozen dataclasses to avoid shared state bugs.

**How to avoid:** Use `field(default_factory=list)` for any list/dict field. The `DatastoreRecommendation` output model should store VMs as `tuple[VMCalculation, ...]` (immutable) or use `field(default_factory=tuple)` pattern.

```python
# Wrong
@dataclass(frozen=True)
class DatastoreRecommendation:
    assigned_vms: list[VMCalculation] = []  # ValueError

# Correct
@dataclass(frozen=True)
class DatastoreRecommendation:
    assigned_vms: tuple[VMCalculation, ...] = ()
```

---

## Code Examples

### Public API Entry Point

```python
# Source: derived from existing pipeline/calculation.py pattern
def generate_all_proposals(
    summary: CalculationSummary,
    constraints: PlacementConstraints | None = None,
) -> list[LayoutProposal]:
    """Generate three layout proposals (Consolidation, Performance, Uniform).

    Args:
        summary: Output from pipeline/calculation.py calculate()
        constraints: Tunable parameters; uses defaults if None

    Returns:
        List of three LayoutProposal objects, one per strategy.
    """
    if constraints is None:
        constraints = PlacementConstraints()

    vms = list(summary.vm_calculations)

    # Apply IOPS estimates if no real performance data
    if not summary.has_performance_data:
        vms = [_apply_default_iops(vm) for vm in vms]

    proposals = [
        _consolidation_strategy(vms, constraints),
        _performance_strategy(vms, constraints),
        _uniform_strategy(vms, constraints),
    ]

    return proposals
```

### DatastoreRecommendation Model

```python
@dataclass(frozen=True)
class DatastoreRecommendation:
    name: str
    raw_capacity_mib: float
    usable_capacity_mib: float
    assigned_vms: tuple[VMCalculation, ...]  # frozen — use tuple not list
    used_capacity_mib: float
    utilization_pct: float
    total_iops: float
    vm_count: int
    workload_types: frozenset[str] = field(default_factory=frozenset)
```

### LayoutProposal Model

```python
@dataclass(frozen=True)
class LayoutProposal:
    strategy_name: str                          # "consolidation" | "performance" | "uniform"
    datastores: tuple[DatastoreRecommendation, ...]
    metrics: LayoutMetrics
```

### LayoutMetrics Model

```python
@dataclass(frozen=True)
class LayoutMetrics:
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
    isolation_score: float                      # 0.0-1.0
    snapshot_granularity_rating: str            # "fine" | "medium" | "coarse"
    oversized_vm_count: int = 0                 # VMs larger than max DS capacity
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SDRS I/O load balancing | PowerStore QoS + manual layout planning | vSphere 8.0 U3 (Jun 2024) | Manual layout correctness matters more now; BFD value proposition is stronger |
| ILP/OR-Tools for optimal packing | BFD heuristic (within 10-15% of optimal) | Architecture decision (ADR-055, Feb 2026) | No solver dependency; pure Python; fast |
| vVol per-VM storage policy | VMFS volume-level layout | Project scope decision (ADR-057, Feb 2026) | Snapshot granularity is at DS level; isolation score metric is meaningful |

**Deprecated/outdated:**
- SDRS (Storage DRS): VMware deprecated SDRS I/O balancing in vSphere 8.0 U3. Do not mention SDRS in any output or documentation.
- SIOC (Storage I/O Control): Same deprecation. Use PowerStore QoS instead.

---

## Open Questions

1. **`workload_category` key format in `VMCalculation`**
   - What we know: `VMCalculation.workload_category` is a string like `"Database/Microsoft SQL"` (category + subcategory joined with `/`)
   - What's unclear: Whether isolation matching should use exact string equality or substring matching — e.g., does `"Database/SAP HANA(S4)"` need exact match or should `"SAP HANA" in category` suffice?
   - Recommendation: Use substring matching (`"SAP HANA" in vm.workload_category`) — more robust to DRR.csv changes that might alter the exact subcategory string. Document this in code comments.

2. **`required_mib` vs `provisioned_mib` for sizing oversized VM datastores**
   - What we know: For isolated VMs, the datastore is "sized to the VM with growth margin and snapshot reserve applied" (ADR-058)
   - What's unclear: Does "sized to the VM" mean `required_mib` (post-DRR) or `provisioned_mib` (raw provisioned)?
   - Recommendation: Use `required_mib` (post-DRR after deduplication reduction) as the base, then apply growth margin and snapshot reserve on top: `ds_capacity = required_mib / constraints.usable_ratio`. This is consistent with how the constraints work.

3. **IOPS estimate for multi-subcategory workloads**
   - What we know: A VM can have multiple workload categories selected (multi-workload DRR uses lowest DRR). The IOPS estimate table is keyed by single category.
   - What's unclear: Which IOPS estimate to use when a VM has multiple workloads?
   - Recommendation: Use the highest IOPS estimate from the matching workloads (opposite of the conservative DRR approach — for IOPS we want the upper bound for capacity planning). Fall back to `_DEFAULT_IOPS_FALLBACK` if no match.

---

## Sources

### Primary (HIGH confidence)

- ADR-055 (`docs/adr/055-layout-engine-bfd-heuristic.md`) — BFD algorithm choice, complexity analysis, quality guarantees
- ADR-056 (`docs/adr/056-three-layout-strategies.md`) — Three strategies, default parameters, tunable constraints
- ADR-057 (`docs/adr/057-vmfs-not-vvol-layout.md`) — VMFS scope, SDRS/SIOC deprecation context
- ADR-058 (`docs/adr/058-isolated-vm-dedicated-datastore.md`) — Phase 0 isolation logic, isolation triggers, sizing rule
- `src/store_predict/pipeline/calculation.py` — Existing frozen dataclass patterns, `VMCalculation` fields, `has_performance_data` flag
- `src/store_predict/pipeline/models.py` — Existing `@dataclass(frozen=True)` usage pattern
- `.planning/REQUIREMENTS.md` — REQ-001 through REQ-014, NFR-001 through NFR-004, acceptance criteria

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` (2026-02-19) — Component boundary rules (pipeline/ never imports ui/), session state patterns
- `.planning/research/STACK.md` (2026-02-19) — No new dependencies confirmed for layout engine work
- `samples/DRR.csv` — Workload category strings (exact format for IOPS estimate table keys)

### Tertiary (LOW confidence)

- VMware vSphere 8.0 U3 release notes (SDRS/SIOC deprecation) — referenced in ADR-057; not directly re-verified in this research session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed zero new dependencies; existing stdlib patterns from calculation.py apply directly
- Architecture: HIGH — module placement, naming, and boundary rules are consistent with ADR-029 (three-layer architecture) and all existing pipeline modules
- BFD algorithm: HIGH — documented in ADR-055 with complexity analysis; standard CS algorithm with known properties
- LPT algorithm: HIGH — standard scheduling algorithm, documented in ADR-055
- Phase 0 isolation: HIGH — fully specified in ADR-058 with exact thresholds
- IOPS defaults: HIGH — specified in REQUIREMENTS.md REQ-014 with explicit values per workload
- Pitfalls: HIGH — derived from code inspection (frozen dataclass constraints) and algorithm analysis (oversized VM, empty list, shared state)

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable domain; algorithms don't change, but verify if new ADRs are added before planning)
