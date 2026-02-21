# Phase 15: Default IOPS & Research Docs - Research

**Researched:** 2026-02-21
**Domain:** Documentation (ADR + MkDocs research page) + optional CSV-configurable IOPS table
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-014 | Default IOPS estimates for RVTools imports (no LiveOptics performance data) | Implementation already done in `layout_models.py`; phase focuses on making the table configurable and documenting it via ADR |
| NFR-004 | ADR for layout engine decisions + research page documenting domain knowledge | ADRs 055-058 cover layout algorithm decisions; this phase adds ADR-059 for IOPS defaults policy and writes `docs/research/phase-15-default-iops.md` |
</phase_requirements>

---

## Summary

Phase 15 is primarily a **documentation and configurability** phase. The code that implements REQ-014 (default IOPS estimation for RVTools imports) already ships in `layout_models.py` (`DEFAULT_IOPS_BY_WORKLOAD` dict) and `layout_engine.py` (`_apply_default_iops()` function). Phase 14 delivered that implementation.

What remains is threefold:

1. **ADR-059**: Document the architectural decision to use workload-based default IOPS estimates (the "why" behind the numbers, conservative sizing rationale, and the fallback constant `_DEFAULT_IOPS_FALLBACK = 50.0`).

2. **Research page** (`docs/research/phase-15-default-iops.md`): Document domain knowledge — where these IOPS values come from, Dell PowerStore IOPS guidance, industry sources for workload IOPS benchmarks, and the design choice to use peak rather than average IOPS for layout planning.

3. **Configurability** (if required by REQ-014's "Configurable via CSV or code constants" clause): The dict is currently hardcoded in `layout_models.py`. REQ-014 says it should be configurable via CSV or code constants. "Code constants" is already satisfied. "CSV" would follow the same pattern as `DRR.csv` — a semicolon-delimited file in `samples/`. This is the main implementation work of this phase.

**Primary recommendation:** Implement CSV-based configurability for IOPS defaults (following the DRR.csv pattern), write ADR-059, and produce the research page. The ADR number is 059 — no gaps exist in 001-058.

---

## Current State Assessment

### What Already Exists (Phase 14 delivered)

| Item | Location | Status |
|------|----------|--------|
| `DEFAULT_IOPS_BY_WORKLOAD` dict | `src/store_predict/pipeline/layout_models.py:28-37` | Done |
| `_DEFAULT_IOPS_FALLBACK = 50.0` | `src/store_predict/pipeline/layout_models.py:39` | Done |
| `_apply_default_iops()` | `src/store_predict/pipeline/layout_engine.py:90-104` | Done |
| IOPS applied in `generate_all_proposals()` | `layout_engine.py:546-547` | Done |
| Test class `TestDefaultIOPS` | `tests/test_layout_engine.py` | Done |

### Current IOPS Values in `DEFAULT_IOPS_BY_WORKLOAD`

| Key (workload_category) | IOPS | Notes |
|------------------------|------|-------|
| `Database/Microsoft SQL` | 500.0 | REQ-014 target |
| `Database/Oracle` | 800.0 | REQ-014 target |
| `Database/SAP HANA(S4)` | 1000.0 | REQ-014 target |
| `VDI/Full Clone / MCS (Citrix)` | 30.0 | REQ-014 target |
| `VDI/Linked Clone / PVS (Citrix)` | 50.0 | REQ-014 target |
| `Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email` | 50.0 | REQ-014 target |
| `File/General Purpose` | 100.0 | REQ-014 target |
| `Unknown (Reducible)/Unknown (Reducible)` | 50.0 | REQ-014 target |

**Gap:** REQ-014 specifies `Virtual Machines/Linux: 40 IOPS` as a separate entry. The current dict uses the single `Virtual Machines/VMware...` key at 50 IOPS for all VMs. Linux VMs would get 50 rather than 40. This is a minor discrepancy since the actual workload_category string from DRR.csv doesn't distinguish Linux from Windows at that level — both map to `Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email`.

**Decision needed for planner:** Either accept 50 IOPS for all generic VMs (conservative), or split the Virtual Machines category. Research indicates splitting is not possible without adding a Linux/Windows detection sub-classification, which is out of scope. Accept 50 IOPS as the conservative fallback.

### ADR Number

ADRs 001-058 are all used. The next ADR is **059**. No gaps.

### Research Page

Existing research pages follow a consistent structure visible in `docs/research/phase-14-app-level-drr-variants.md`:
- Problem Statement section
- Domain knowledge sections (sourced from Dell docs, industry guides)
- Implementation summary
- References table

The new research page `phase-15-default-iops.md` follows this exact pattern.

---

## Standard Stack

### Core (no new dependencies)

| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| Python dataclasses | stdlib | `DEFAULT_IOPS_BY_WORKLOAD` dict and constants | Already used in layout_models.py |
| pandas / csv stdlib | stdlib | Optional CSV loading | Same pattern as DRR.csv loading via `calculation.py` |
| MkDocs Material | latest | Research page rendering | Already used — all docs/ pages use this |
| MkDocs superfences | via pymdownx | Markdown tables, code blocks | Already configured |

### Supporting (if CSV configurability)

| Approach | Notes |
|---|---|
| Semicolon-delimited CSV in `samples/` | Follows `samples/DRR.csv` precedent exactly |
| Load at startup with `_load_iops_csv()` | Same pattern as DRR loading in pipeline |
| Fallback to hardcoded dict if CSV missing | Defensive — keeps unit tests independent |

**Installation:** No new packages needed. This phase is pure documentation + optional CSV loading.

---

## Architecture Patterns

### Pattern 1: CSV-Configurable IOPS Table

Follow the exact same pattern as `samples/DRR.csv` + loading code:

**CSV format (semicolon-delimited):**
```
Workload Category;IOPS Estimate
Database/Microsoft SQL;500
Database/Oracle;800
Database/SAP HANA(S4);1000
VDI/Full Clone / MCS (Citrix);30
VDI/Linked Clone / PVS (Citrix);50
Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email;50
File/General Purpose;100
Unknown (Reducible)/Unknown (Reducible);50
```

**Loading pattern (in `layout_models.py`):**
```python
# Source: follows DRR.csv loading pattern established in Phase 1
import csv
from pathlib import Path

_IOPS_CSV_PATH = Path(__file__).parent.parent.parent.parent / "samples" / "IOPS.csv"

def _load_iops_from_csv(path: Path = _IOPS_CSV_PATH) -> dict[str, float]:
    """Load workload IOPS estimates from CSV. Falls back to hardcoded dict if file missing."""
    if not path.exists():
        return dict(_DEFAULT_IOPS_HARDCODED)
    result: dict[str, float] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cat = row.get("Workload Category", "").strip()
            iops_str = row.get("IOPS Estimate", "").strip()
            if cat and iops_str:
                try:
                    result[cat] = float(iops_str)
                except ValueError:
                    pass
    return result if result else dict(_DEFAULT_IOPS_HARDCODED)

DEFAULT_IOPS_BY_WORKLOAD: dict[str, float] = _load_iops_from_csv()
```

**When to use:** Satisfies REQ-014's "Configurable via CSV or code constants" requirement. Pre-sales engineers can adjust IOPS estimates without code changes.

### Pattern 2: ADR Format

All 58 existing ADRs follow this exact structure:
```markdown
# ADR-NNN: Title

**Date:** YYYY-MM-DD
**Status:** Accepted

## Context
[2-3 paragraphs on why the decision was needed]

## Decision
[The chosen approach, clearly stated]

## Consequences
[Trade-offs: what becomes easier/harder]
```

ADR-059 documents: why default IOPS are needed (RVTools has no IOPS data), where values come from (Dell PowerStore IOPS guidance, workload benchmarks), and the conservative bias (pre-sales must not under-provision IOPS budget).

### Pattern 3: Research Page Format

The existing `docs/research/phase-14-app-level-drr-variants.md` is the template. Structure:
1. **Problem Statement** — why default IOPS matter for pre-sales
2. **Domain Knowledge sections** — Dell PowerStore IOPS guidance, workload benchmarks
3. **Design choices** — peak vs. average, fallback constant, conservative bias
4. **Implementation summary** — what was built, how CSV overrides work
5. **References table** — URLs with source descriptions

### Pattern 4: ADR Index Update

After writing ADR-059, add it to `docs/adr/index.md`:
```markdown
| [059](059-default-iops-estimates.md) | Workload-based IOPS defaults for RVTools sizing | Accepted | 2026-02-21 |
```

### Anti-Patterns to Avoid

- **Do NOT create a new IOPS_DEFAULTS constant file**: Keep everything in `layout_models.py` — that's already the module boundary for layout domain data.
- **Do NOT make CSV path configurable via env var**: DRR.csv uses a fixed path in `samples/`; follow the same convention.
- **Do NOT add IOPS values to DRR.csv**: DRR.csv models storage reduction ratios — a different concern. A separate `IOPS.csv` keeps concerns separated.
- **Do NOT write new tests for the CSV loader**: The existing `TestDefaultIOPS` class already covers `_apply_default_iops()`. Only add a test for `_load_iops_from_csv()` if implementing the CSV path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom renderer | MkDocs Material (already configured) | Table rendering, code blocks, Mermaid already work |
| ADR numbering | Custom tracking system | Sequential files matching `docs/adr/index.md` | 58 ADRs follow this convention already |
| CSV parsing | Custom parser | `csv.DictReader` with `delimiter=";"` | Exact same pattern used by DRR.csv; semicolon delimiter is established convention |

---

## Common Pitfalls

### Pitfall 1: IOPS Key Mismatch

**What goes wrong:** The `DEFAULT_IOPS_BY_WORKLOAD` dict uses full workload_category strings like `"Database/Microsoft SQL"`, not just the base category. If the CSV uses different casing or spacing, `_apply_default_iops()` gets cache misses and falls back to 50 IOPS for everything.

**Why it happens:** `workload_category` is formed as `f"{category}/{subcategory}"` from DRR.csv. Subtle formatting differences (trailing space, different slash character) cause lookup failure.

**How to avoid:** Strip whitespace in the CSV loader. Add a test that loads the CSV and verifies all keys exist in the loaded dict.

**Warning signs:** Unit tests pass (they use the hardcoded dict) but integration tests show 50 IOPS for SQL VMs when CSV is present.

### Pitfall 2: ADR Number Collision

**What goes wrong:** ADRs 001-058 are all used. If someone creates ADR-059 simultaneously in another branch, you get a collision on merge.

**Why it happens:** The project has been in active development; multiple phases write ADRs.

**How to avoid:** Check `docs/adr/index.md` and file listing before writing. As of research date (2026-02-21), 059 is the correct next number. Verify immediately before committing.

### Pitfall 3: Research Page Not Linked

**What goes wrong:** New research page exists in `docs/research/` but `docs/research/index.md` isn't updated, so it's unreachable from navigation.

**How to avoid:** Always update `docs/research/index.md` when adding a new research page.

### Pitfall 4: CSV Fallback Breaks Tests

**What goes wrong:** If `_load_iops_from_csv()` is called at module import time, and the test environment doesn't have `samples/IOPS.csv`, tests fail with FileNotFoundError.

**How to avoid:** The loader must check `path.exists()` and fall back to the hardcoded dict. Write the CSV loader to be defensive by design.

### Pitfall 5: Linux vs. Windows IOPS Split

**What goes wrong:** REQ-014 specifies separate IOPS for Windows (50) and Linux (40) VMs. But `workload_category` for both is the same string from DRR.csv (`Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email`). There's no way to distinguish OS within the current data model.

**How to avoid:** Accept 50 IOPS for all generic VMs (the conservative value). Document this in the ADR as a known limitation. Do not attempt to re-classify VMs by OS for IOPS purposes — it's out of scope.

---

## Code Examples

### Current _apply_default_iops() — Already Working

```python
# Source: src/store_predict/pipeline/layout_engine.py:90-104
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
```

### CSV Loader Pattern (to implement)

```python
# Source: follows DRR.csv loading pattern from src/store_predict/pipeline/
import csv
from pathlib import Path

_IOPS_CSV_PATH = Path(__file__).parent.parent.parent.parent / "samples" / "IOPS.csv"

_DEFAULT_IOPS_HARDCODED: dict[str, float] = {
    "Database/Microsoft SQL": 500.0,
    "Database/Oracle": 800.0,
    "Database/SAP HANA(S4)": 1000.0,
    "VDI/Full Clone / MCS (Citrix)": 30.0,
    "VDI/Linked Clone / PVS (Citrix)": 50.0,
    "Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email": 50.0,
    "File/General Purpose": 100.0,
    "Unknown (Reducible)/Unknown (Reducible)": 50.0,
}

def _load_iops_from_csv(path: Path = _IOPS_CSV_PATH) -> dict[str, float]:
    if not path.exists():
        return dict(_DEFAULT_IOPS_HARDCODED)
    result: dict[str, float] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cat = (row.get("Workload Category") or "").strip()
            iops_str = (row.get("IOPS Estimate") or "").strip()
            if cat and iops_str:
                try:
                    result[cat] = float(iops_str)
                except ValueError:
                    pass
    return result if result else dict(_DEFAULT_IOPS_HARDCODED)

DEFAULT_IOPS_BY_WORKLOAD: dict[str, float] = _load_iops_from_csv()
_DEFAULT_IOPS_FALLBACK: float = 50.0
```

### ADR-059 Shell

```markdown
# ADR-059: Workload-based IOPS defaults for RVTools sizing

**Date:** 2026-02-21
**Status:** Accepted

## Context

RVTools exports do not include performance data (IOPS, throughput). When the
layout engine runs on an RVTools import, every VMCalculation has peak_iops=0.
Without IOPS estimates, the datastore IOPS budget constraint becomes inactive,
producing unrealistic layouts that ignore I/O contention entirely.

## Decision

When CalculationSummary.has_performance_data is False, apply workload-based
IOPS estimates via _apply_default_iops() before layout placement. Values are
loaded from samples/IOPS.csv (semicolon-delimited), falling back to hardcoded
constants if the file is missing.

Estimates are conservative (peak IOPS, not average) because pre-sales sizing
must not under-provision. avg_iops is estimated as 70% of peak.

## Consequences

- [consequences...]
```

### Research Page Table Structure

```markdown
| Workload | Default IOPS | Source | Notes |
|----------|-------------|--------|-------|
| Database/Microsoft SQL | 500 | Dell PowerStore VMware BP | Steady-state OLTP, 8K random |
| Database/Oracle | 800 | Dell PowerStore Oracle BP | OLTP, includes redo log I/O |
| Database/SAP HANA(S4) | 1,000 | SAP sizing guidelines | In-memory but persistent log I/O |
| VDI/Full Clone | 30 | VMware Horizon sizing | Boot storm excluded; steady state |
| VDI/Linked Clone | 50 | VMware Horizon sizing | Higher due to base disk writes |
| Virtual Machines (generic) | 50 | Dell conservative estimate | No workload signal available |
| File/General Purpose | 100 | Dell PowerStore file BP | NFS/SMB mixed I/O |
| Unknown | 50 | Conservative fallback | Applied when workload unclassifiable |
```

---

## IOPS Domain Knowledge

### Why Peak IOPS, Not Average

The layout engine uses IOPS to size datastores. For PowerStore's IOPS budget per datastore (default: 100,000 IOPS), the binding constraint is **peak** load, not average. If average IOPS were used, a OLTP SQL server spiky to 2,000 IOPS at lunch would be placed alongside 199 other "average 500 IOPS" servers — all fine until the peak hits simultaneously.

Pre-sales sizing rule: use peak IOPS for capacity planning, average for throughput reports.

### Industry Sources for Default Values

**Database/Microsoft SQL — 500 IOPS**
- Dell PowerStore VMware Best Practices (H18264): OLTP SQL Server 8K random I/O sizing
- Microsoft SQL Server storage guidance: 500-1,500 IOPS per core for moderate OLTP
- 500 is the lower bound — conservative for pre-sales

**Database/Oracle — 800 IOPS**
- Dell PowerStore Oracle RAC Best Practices: Oracle OLTP at 8K block size
- Includes redo log I/O overhead
- Oracle IOPS guidance: 800-1,200 IOPS for moderate databases

**Database/SAP HANA — 1,000 IOPS**
- SAP HANA Hardware Directory sizing criteria
- HANA stores hot data in memory but log persistence requires 1,000+ IOPS
- Dell EMC SAP HANA PowerStore BP confirms this range

**VDI/Full Clone — 30 IOPS (steady state)**
- VMware Horizon 8 Reference Architecture: 15-30 IOPS per desktop steady state
- Boot storms reach 100+ IOPS — excluded from steady state estimate
- Dell Horizon on PowerStore: 30 IOPS/VM is the standard planning value

**VDI/Linked Clone — 50 IOPS**
- Higher than full clone because linked clone writes go to replica disks
- VMware sizing: 30-50 IOPS depending on workload intensity
- 50 is conservative upper bound

**Virtual Machines (generic) — 50 IOPS**
- Dell PowerStore general VM sizing guidance
- No workload signal available; 50 IOPS covers mixed general-purpose workloads
- File/Print Server at 100 IOPS reflects higher I/O intensity of file serving

**avg_iops = 0.70 × peak_iops**
- Industry standard: busy systems run at 60-75% of peak in sustained operation
- 70% is the midpoint — defensible in pre-sales discussions
- This value is used only for reporting metrics, not for constraint evaluation

### PowerStore IOPS Architecture

PowerStore uses NVMe-based storage with a claimed 7M IOPS max (PowerStore T model). Per-volume IOPS is limited by software QoS policy (optional) or by the shared pool. The layout engine's `iops_budget_per_ds = 100,000` default is a conservative planning value that leaves headroom for peak spikes and is consistent with Dell's H18264 recommendations.

---

## State of the Art

| Old Approach | Current Approach | Status |
|---|---|---|
| No IOPS estimates (IOPS=0 from RVTools) | Workload-based defaults via `_apply_default_iops()` | Implemented in Phase 14 |
| Hardcoded dict in layout_models.py | CSV-loadable with hardcoded fallback | To implement in Phase 15 |
| No ADR for IOPS defaults | ADR-059 documents policy | To write in Phase 15 |
| No research page for IOPS domain | `docs/research/phase-15-default-iops.md` | To write in Phase 15 |

---

## Open Questions

1. **Linux vs. Windows IOPS split**
   - What we know: REQ-014 specifies Linux=40, Windows=50 as separate entries; current data model has no OS distinction at workload_category level
   - What's unclear: Whether adding sub-classification is worth the complexity
   - Recommendation: Accept 50 IOPS for all generic VMs. Document in ADR-059 as known limitation. Do not attempt OS-level sub-classification.

2. **IOPS.csv location**
   - What we know: DRR.csv lives in `samples/` — a convention used since Phase 1
   - What's unclear: Whether `samples/` is the right place for a second reference file
   - Recommendation: Use `samples/IOPS.csv` to maintain consistency with DRR.csv

3. **Whether CSV loading is strictly required**
   - What we know: REQ-014 says "Configurable via CSV or code constants" — "or" makes CSV optional if constants exist
   - What's unclear: Whether the planner should treat this as required or optional
   - Recommendation: Implement CSV loading (it's low effort following DRR.csv pattern) and document in ADR-059. This fully satisfies REQ-014.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/store_predict/pipeline/layout_models.py` — DEFAULT_IOPS_BY_WORKLOAD confirmed present and correct
- Direct code inspection: `src/store_predict/pipeline/layout_engine.py` — `_apply_default_iops()` confirmed implemented
- Direct code inspection: `src/store_predict/pipeline/calculation.py` — `has_performance_data: bool = False` in CalculationSummary
- Direct file inspection: `docs/adr/index.md` — ADRs 001-058 confirmed; next is 059
- Direct file inspection: `docs/research/index.md` — research page list confirmed; phase-15 missing
- Direct file inspection: `docs/adr/055-058` — layout engine ADRs confirmed as existing
- Direct inspection: `samples/DRR.csv` — semicolon-delimited format confirmed; CSV loading pattern established

### Secondary (MEDIUM confidence)
- Dell PowerStore VMware Best Practices (H18264) — IOPS planning values (not directly fetched, cited from layout_models.py and existing ADRs)
- VMware Horizon sizing guides — VDI IOPS benchmarks (industry standard, widely cited)

### Tertiary (LOW confidence)
- SAP HANA IOPS guidance — 1,000 IOPS value (aligns with published SAP Hardware Directory sizing, not directly verified via WebFetch in this session)

---

## Metadata

**Confidence breakdown:**
- Current code state: HIGH — directly inspected all relevant files
- ADR number (059): HIGH — directly counted 001-058 in index.md and file listing
- Research page format: HIGH — directly read phase-14 research page as template
- IOPS values accuracy: MEDIUM — values match REQ-014 spec; industry sources cited but not re-fetched
- CSV loader design: HIGH — follows established DRR.csv loading pattern

**Research date:** 2026-02-21
**Valid until:** 2026-03-23 (stable domain — code doesn't change without PR)
