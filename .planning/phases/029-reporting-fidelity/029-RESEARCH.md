# Phase 29: Reporting Fidelity - Research

**Researched:** 2026-03-26
**Domain:** Python calculation pipeline, workload classification rules, matplotlib/ReportLab PDF rendering
**Confidence:** HIGH

## Summary

Phase 29 delivers three independent work streams. Wave A fixes a groupby-key bug in the calculation pipeline: `WorkloadGroupResult` groups only on `category` (ignoring `drr`), so VMs in the same workload category but with different DRR values collapse into one averaged row. The fix requires changing the groupby key from `category` to `(category, drr)`, updating the `WorkloadGroupResult` dataclass to carry a `drr` field, and propagating the display key change to all four consumers (web UI table, PDF table, Excel breakdown sheet, ECharts Sankey nodes). Wave B adds pattern rules for backup/archive tools (Veeam agent, Commvault proxy, Veritas, NetBackup), monitoring infrastructure (Nagios, SolarWinds), and a handful of common databases that are already present in the DRR.csv but lack explicit VM-name patterns. Wave C upgrades the matplotlib Agg Sankey rendering resolution from 150 DPI to 300+ DPI to eliminate pixelation at standard print resolution.

**Primary recommendation:** Treat all three waves as data-flow problems rather than API problems. Wave A lives entirely in `pipeline/calculation.py` with mechanical propagation to consumers. Wave B is additive `ClassificationRule` entries in `pipeline/classification.py`. Wave C is a one-line DPI change in `services/pdf_charts.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DRR-01 | Web UI workload summary table shows separate rows when same-named workloads have different DRR values | Groupby key change in `calculate()` directly controls what `workload_groups` produces; the web UI table iterates `summary.workload_groups` verbatim |
| DRR-02 | PDF workload breakdown shows separate rows for different-DRR same-category workloads | `pdf_report.py` iterates `summary.workload_groups` identically — fix upstream groupby fixes PDF automatically |
| DRR-03 | Excel workload breakdown shows separate rows | `excel_report.py` iterates `summary.workload_groups` identically — same upstream fix propagates |
| CLASSIF-01 | Backup/archive VMs (Veeam agent, Commvault proxy, Veritas, NetBackup) classified instead of Unknown Reducible | DRR.csv has "VM Replication;Veeam, Zerto, RP4VM;1.5" and "VM Replication;Commvault;1.5" — need new ClassificationRule entries with relevant patterns |
| CLASSIF-02 | Monitoring VMs (Nagios, SolarWinds) classified instead of Unknown Reducible | DRR.csv maps to "Logging - Analytics;FortiNet, Elastic Search, Splunk, ELK, etc;1.5" — Zabbix and PRTG already covered; Nagios/SolarWinds/Icinga patterns missing |
| CLASSIF-03 | Common database VMs (MySQL, PostgreSQL, MongoDB, Redis, MariaDB) classified | Already covered by existing rules (priority 94-105) — Redis is the only gap, maps to "Database;My SQL / NoSQL;5" |
| REPORT-01 | Sankey PDF renders at print quality (no pixelation) | Matplotlib Agg renders at 150 DPI; upgrading to 300 DPI with matching figsize doubles effective resolution without layout changes |
| REPORT-02 | Sankey nodes/edges have legible labels and correct colors | Font size 5 is marginal at 150 DPI; same fix (300 DPI) and minor font-size bump improves legibility; colors already use Dell palette from `charts.py` |
</phase_requirements>

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| matplotlib (Agg backend) | installed | Headless PNG Sankey rendering | Already the project choice per ADR-071; no Playwright/kaleido |
| ReportLab Platypus | installed | PDF tables and flowables | Project standard, all PDF surfaces use it |
| pytest | installed | Test framework | Project standard; 158+ existing tests |
| pandas | installed | DataFrame manipulation in pipeline | Project standard for ingestion/classification |

### No New Dependencies Required

All three waves use libraries already installed. No `pip install` step needed.

## Architecture Patterns

### Wave A: DRR Category Split

**The bug location** — `pipeline/calculation.py`, function `calculate()`, lines 136-158.

Current groupby key (the bug):
```python
groups: dict[str, list[VMCalculation]] = defaultdict(list)
for vm in vm_calcs:
    groups[vm.workload_category].append(vm)
```

The key is `vm.workload_category` (a `str`). Two VMs with the same `workload_category` but different `drr` values land in the same group. The averaged `avg_drr` in `WorkloadGroupResult` then hides the distinction.

**Fix pattern** — group on `(category, drr)` tuple:
```python
groups: dict[tuple[str, float], list[VMCalculation]] = defaultdict(list)
for vm in vm_calcs:
    groups[(vm.workload_category, vm.drr)].append(vm)
```

**WorkloadGroupResult must carry the DRR** so consumers can display it. Add a `drr` field:
```python
@dataclass(frozen=True)
class WorkloadGroupResult:
    category: str
    drr: float          # NEW: the DRR value for this specific group
    vm_count: int
    total_provisioned_mib: float
    total_in_use_mib: float
    avg_drr: float      # keep for backward compat (equals drr when grouped by drr)
    total_required_mib: float
```

**Display key for row identity** — the workload breakdown tables need a display label. Use `f"{category} (DRR {drr}x)"` only when the category appears more than once in `workload_groups`; use bare `category` when it is unique. This avoids cluttering the common case.

Alternative simpler approach: always show `category` as-is in the row, but the row appears multiple times if the same category has multiple DRR values. Since the `drr` column already shows the numeric value, users can distinguish rows without label decoration. This is simpler and preferred.

**Consumer impact** (each iterates `summary.workload_groups` directly):

| File | Location | Change needed |
|------|----------|---------------|
| `ui/pages/report.py` | line 157-166 | No change needed if `grp.category` and `grp.avg_drr` are preserved |
| `services/pdf_report.py` | lines 641-650 | No change needed — shows `grp.category` and `grp.avg_drr` |
| `services/excel_report.py` | lines 162-173 | No change needed — shows `grp.category` and `grp.avg_drr` |
| `services/pdf_charts.py` | lines 39-250 | Bar charts use `grp.category` as axis label — may show duplicate labels; acceptable |
| `services/charts.py` | lines 41-60 | ECharts Sankey: nodes keyed on `grp.category` — duplicate names will conflict in ECharts `data` array; must use unique node names |

**ECharts Sankey node collision** — ECharts Sankey node names must be unique. If two groups share the same `category` but differ in `drr`, the node dict will have two entries with the same `"name"`. ECharts will merge or discard one. Fix: use the display label `f"{grp.category} ({grp.drr:.1f}x)"` as node name in `echart_sankey_options()`. The matplotlib PDF Sankey uses a different rendering approach and truncates `grp.category[:12]` — duplicate truncated labels are visually confusing but not a crash.

### Wave B: Classification Expansion

**Where rules live** — `pipeline/classification.py`, function `build_default_rules()`. Rules are appended to the list; the `RuleRegistry` sorts by `priority` on construction.

**Priority tiers currently used:**

| Tier | Priority range | Purpose |
|------|----------------|---------|
| 0 | 80-99 | Encrypted/compressed DB variants |
| 1 | 100-199 | Databases |
| 2 | 200-299 | Application-specific (HealthCare, Email, VDI) |
| 3 | 300-399 | Infrastructure (Replication, Containers, Web, File) |
| 4 | 400-499 | Logging/Analytics |
| 5 | 500-599 | Boot from SAN |
| 6 | 900-949 | OS-based fallback |
| 7 | 999 | Default (Unknown Reducible) |

**Already-classified patterns (no change needed for CLASSIF-03):**

| VM name trigger | Rule | Priority | Category/Subcategory | DRR |
|----------------|------|----------|---------------------|-----|
| MYSQL, NOSQL, MARIADB, FILEMAKER, SQLITE | "MySQL / NoSQL" | 101 | Database/My SQL / NoSQL | 5 |
| PGSQL, POSTGRES, POSTGRESQL | "PostgreSQL" | 102 | Database/PostgreSQL | 1.5 |
| MONGODB, MONGO | "MongoDB" | 105 | Database/MongoDB | 1.5 |

**Gap for CLASSIF-03:** Redis. No existing rule matches "REDIS". Maps to `Database/My SQL / NoSQL` (DRR=5) per DRR.csv category grouping. Add `"REDIS"` to the "MySQL / NoSQL" rule at priority 101.

**Already-classified backup patterns (partial for CLASSIF-01):**

| VM name trigger | Rule | Priority | Category/Subcategory | DRR |
|----------------|------|----------|---------------------|-----|
| VEEAM, VBR, ZERTO, RP4VM | "VM Replication" | 300 | VM Replication/Veeam, Zerto, RP4VM | 1.5 |
| COMMVAULT, CVD | "Commvault" | 297 | VM Replication/Commvault | 1.5 |
| DDVE, DATADOMAIN | "DDVE" | 293 | VM Replication/DDVE | 1.0 |

**Gap for CLASSIF-01:** Veritas NetBackup and NBU patterns. VMs named "veritas-media", "netbackup-master", "nbu-client" are not matched. Add new rule at priority 298 in Tier 3. Also "BACKUP" as a bare keyword hits `File/Archive / Backup...` (DRR=1) only via the "ARCHIVE" pattern — the word "BACKUP" is not captured. Adding "BACKUP" to the File Archive rule (priority 360) would classify `*BACKUP*` VMs correctly.

**Gap for CLASSIF-02:** Nagios and SolarWinds. Zabbix, PRTG, Grafana already match "Logging - Analytics" (priority 400). Nagios, Icinga, SolarWinds, LibreNMS, OpenNMS are missing.

**ClassificationRule format** (frozen dataclass from classification.py):
```python
ClassificationRule(
    name="Veritas / NetBackup",
    category="VM Replication",
    subcategory="Veeam, Zerto, RP4VM",   # closest DRR.csv entry
    priority=298,
    vm_name_patterns=_patterns("VERITAS", "NETBACKUP", "NBU"),
)
```

Note: "VM Replication" subcategory "Veeam, Zerto, RP4VM" is the correct match for backup agents/proxies. DRR = 1.5 is appropriate for backup repository VMs.

### Wave C: PDF Chart Quality

**Current rendering** — `services/pdf_charts.py`, function `make_sankey_image_flowable()`.

Key parameters:
```python
dpi = 150
fig = Figure(figsize=(width_pt / 72, height_pt / 72), dpi=dpi, facecolor="white")
# ...
fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
```

`width_pt` defaults to 500 pt, `height_pt` to 200 pt. At 150 DPI:
- Physical size: 500/72 = 6.94 inches × 200/72 = 2.78 inches
- Pixel dimensions: 1042 × 417 px
- When embedded in A4 PDF at original size, ReportLab scales the 1042×417 pixel PNG back to 500×200 pt — effective resolution = 150 DPI.

**Fix** — raise DPI to 300:
```python
dpi = 300
```

At 300 DPI with same `figsize`:
- Pixel dimensions: 2083 × 833 px
- Embedded at 500×200 pt = 300 DPI effective — print quality, no pixelation.

**Font size legibility** — at 150 DPI, `fontsize=5` for mid-node labels is borderline. At 300 DPI the same numeric `fontsize` maps to the same physical point size on the figure coordinate system, but with 2x more pixels per inch, the rasterized glyphs will be sharper. No font size change is strictly required, but bumping from 5 to 6 for mid-node labels and from 6.5 to 7 for axis labels provides additional safety margin.

**Color match with web UI** — web UI uses ECharts Sankey via `charts.py` with `DELL_PALETTE = ["#007DB8", "#40A8D8", "#6C757D", "#ADB5BD", "#CED4DA", "#DEE2E6"]`. The matplotlib Sankey uses `palette = ["#007DB8", "#40A8D8", "#6C757D", "#ADB5BD", "#CED4DA", "#5B8DB8"]`. The sixth color differs (`#5B8DB8` vs `#DEE2E6`). Align the matplotlib palette with the ECharts palette to satisfy REPORT-02.

**Callsite** — `make_sankey_image_flowable(summary, width_pt=500, height_pt=200)` is called in `pdf_report.py`. The `width_pt` and `height_pt` arguments are already at defaults. No signature change needed.

### Recommended Project Structure (no changes)

```
src/store_predict/
├── pipeline/
│   ├── calculation.py     # Wave A: groupby fix here
│   └── classification.py  # Wave B: new rules added here
└── services/
    └── pdf_charts.py      # Wave C: DPI and palette fix here
```

### Anti-Patterns to Avoid

- **Don't add a `drr` field to the display label string** — this breaks ECharts Sankey only; keep category label as-is in table consumers, fix only the ECharts Sankey node name.
- **Don't change `avg_drr` semantics** — when grouped by `(category, drr)`, `avg_drr` will equal `drr` for each group. Keep it for backward compatibility with tests that assert `grp.avg_drr`.
- **Don't add classification rules for CLASSIF-03 databases that already have rules** — MySQL, PostgreSQL, MongoDB, MariaDB are already covered. Only Redis is missing.
- **Don't raise DPI beyond 300** — 300 DPI is print standard. Higher values (600) quadruple memory usage and produce no visible improvement in PDF readers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique node labels for ECharts Sankey | Custom deduplication logic | Append DRR to node name: `f"{cat} ({drr:.1f}x)"` | Simple f-string; ECharts just needs unique strings |
| High-res PNG for PDF | Separate Pillow upscale step | Raise matplotlib `dpi` parameter | Agg backend renders at requested DPI natively |
| Classification coverage check | Custom audit script | Add pytest parametrize tests for new VM name patterns | Already the project pattern |

## Common Pitfalls

### Pitfall 1: WorkloadGroupResult Sort Order After Groupby Key Change

**What goes wrong:** Current code sorts `workload_groups` by `category` (`for category in sorted(groups)`). After changing the key to `(category, drr)`, the sort must change to `sorted(groups)` on the tuple, which naturally sorts by `(category, drr)` lexicographically. This is the correct behavior — rows for the same category cluster together, ordered by DRR.

**How to avoid:** Replace `for category in sorted(groups):` with `for key in sorted(groups):` and unpack `category, drr = key`.

### Pitfall 2: ECharts Sankey Node Name Collision

**What goes wrong:** ECharts `data` array in a Sankey chart must have unique `"name"` values. If two `WorkloadGroupResult` entries share the same `category` (e.g., "Database" with DRR=5.0 and "Database" with DRR=1.5), the generated `nodes` list has two `{"name": "Database", ...}` entries. ECharts behavior is undefined — it may render only one segment or crash silently.

**How to avoid:** In `echart_sankey_options()`, build node names as `f"{grp.category} ({grp.drr:.1f}x)"` for any category that appears more than once. A simpler approach: always use `f"{grp.category}"` but detect duplicates and append DRR suffix only on collision.

**Warning signs:** Missing Sankey links or zero-value flows in the web UI after applying the Wave A fix.

### Pitfall 3: Test Helper `_make_summary` Bypasses `calculate()`

**What goes wrong:** Most PDF and Excel tests build `CalculationSummary` directly using `WorkloadGroupResult(...)` constructor calls (see `test_pdf_report.py` lines 30-53). After adding a `drr` field to `WorkloadGroupResult`, these constructors will break with `TypeError: __init__() missing 1 required positional argument: 'drr'`.

**How to avoid:** Add a default value to the new `drr` field (`drr: float = 0.0`) or update all 30 tests. Prefer `drr: float = 0.0` as default since it's backward-safe and tests that don't care about DRR splitting don't need to change.

### Pitfall 4: "BACKUP" Pattern False Positives

**What goes wrong:** Adding `"BACKUP"` as a vm_name pattern to the File/Archive rule would classify VMs like "backup-server" correctly but also match "veeam-backup-01" — which should match the VM Replication rule (priority 300) and already does. Since the File/Archive rule is at priority 360 (lower precedence), Veeam VMs at priority 300 are matched first. No false positive risk here; the priority system handles it.

**Warning signs:** A VM named "veeam-backup-01" reclassifying from VM Replication to File Archive after the change.

### Pitfall 5: Matplotlib Figure Memory at 300 DPI

**What goes wrong:** At 300 DPI with figsize (6.94 × 2.78 inches), pixel dimensions are ~2083 × 833 = ~1.7 million pixels. At 4 bytes/pixel (RGBA), this is ~6.8 MB per figure. For a single report page this is fine. If Sankey is ever called in a loop (batch export), memory could accumulate.

**How to avoid:** `fig` is garbage-collected after the function returns (no reference kept). No explicit `plt.close()` call is needed because `Figure()` is used directly (not `plt.figure()`), so the Agg canvas is freed when `fig` goes out of scope.

## Code Examples

Verified from source code audit:

### Current groupby key (Wave A bug location)

```python
# pipeline/calculation.py lines 136-158 — CURRENT (buggy)
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
```

### Fixed groupby key (Wave A target state)

```python
# Group by (category, drr) tuple so rows with same name but different DRR stay separate
groups: dict[tuple[str, float], list[VMCalculation]] = defaultdict(list)
for vm in vm_calcs:
    groups[(vm.workload_category, vm.drr)].append(vm)

workload_groups: list[WorkloadGroupResult] = []
for key in sorted(groups):
    category, drr = key
    vms = groups[key]
    grp_provisioned = sum(v.provisioned_mib for v in vms)
    grp_in_use = sum(v.in_use_mib for v in vms)
    grp_required = sum(v.required_mib for v in vms)
    grp_avg_drr = drr  # uniform within this group by construction
    workload_groups.append(
        WorkloadGroupResult(
            category=category,
            drr=drr,          # new field
            vm_count=len(vms),
            total_provisioned_mib=grp_provisioned,
            total_in_use_mib=grp_in_use,
            avg_drr=grp_avg_drr,
            total_required_mib=grp_required,
        )
    )
```

### New ClassificationRule format (Wave B — Veritas/NetBackup example)

```python
# pipeline/classification.py, inside build_default_rules(), Tier 3 around priority 298
ClassificationRule(
    name="Veritas / NetBackup",
    category="VM Replication",
    subcategory="Veeam, Zerto, RP4VM",
    priority=298,
    vm_name_patterns=_patterns("VERITAS", "NETBACKUP", "NBU"),
),
```

### DPI upgrade (Wave C — one-line fix)

```python
# services/pdf_charts.py, make_sankey_image_flowable(), line 143
dpi = 300  # was 150; 300 DPI = print quality, eliminates pixelation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plotly+kaleido Sankey | matplotlib Agg Sankey | ADR-071 (recent) | No browser dependency; pure Python headless |
| 150 DPI PNG | 300 DPI PNG (after this phase) | Phase 29 | Print-quality output |
| groupby category only | groupby (category, drr) tuple | Phase 29 | Correct row splitting for same-name different-DRR workloads |

## Open Questions

1. **Should the ECharts web UI Sankey use DRR-qualified node names universally or only on collision?**
   - What we know: ECharts requires unique node names; most datasets will NOT have same-category different-DRR situations
   - What's unclear: Whether pre-sales users find "Database (5.0x)" cleaner than two "Database" rows
   - Recommendation: Qualify node names only when there are actual duplicates in `workload_groups`; this avoids polluting the common case

2. **Should `avg_drr` be removed from `WorkloadGroupResult` after the fix?**
   - What we know: When grouped by `(category, drr)`, `avg_drr` always equals `drr`; the field is redundant
   - What's unclear: Whether removing it breaks downstream callers that read `grp.avg_drr`
   - Recommendation: Keep `avg_drr` for backward compat; callers already use it (pdf_report.py:648, excel_report.py:172, charts.py:104)

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version from project .venv) |
| Config file | `pytest.ini` or `pyproject.toml` (project root) |
| Quick run command | `rtk pytest tests/test_calculation.py tests/test_classification.py -x` |
| Full suite command | `rtk pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DRR-01 | Two VMs, same category, different DRR — produce two `WorkloadGroupResult` rows | unit | `rtk pytest tests/test_calculation.py::TestDRRSplit -x` | Wave 0 gap |
| DRR-02 | PDF table iterates two separate rows | unit | `rtk pytest tests/test_pdf_report.py::test_drr_split_rows -x` | Wave 0 gap |
| DRR-03 | Excel breakdown shows two rows | unit | `rtk pytest tests/test_excel_report.py::test_drr_split_rows -x` | Wave 0 gap |
| CLASSIF-01 | Veeam/Commvault/Veritas/NetBackup VMs not Unknown Reducible | unit | `rtk pytest tests/test_classification.py -k "backup or veeam or netbackup" -x` | Wave 0 gap for Veritas/NetBackup |
| CLASSIF-02 | Nagios/SolarWinds VMs classify to Logging Analytics | unit | `rtk pytest tests/test_classification.py -k "nagios or solarwinds" -x` | Wave 0 gap |
| CLASSIF-03 | Redis VM classifies to Database/My SQL/NoSQL | unit | `rtk pytest tests/test_classification.py -k "redis" -x` | Wave 0 gap |
| REPORT-01 | Sankey PNG pixel dimensions >= 2000px wide | unit | `rtk pytest tests/test_pdf_report.py::test_sankey_resolution -x` | Wave 0 gap |
| REPORT-02 | Sankey palette matches ECharts palette | unit | `rtk pytest tests/test_pdf_report.py::test_sankey_colors -x` | Wave 0 gap |

### Sampling Rate

- **Per task commit:** `rtk pytest tests/test_calculation.py tests/test_classification.py -x`
- **Per wave merge:** `rtk pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_calculation.py` — add `TestDRRSplit` class testing `calculate()` with two VMs of same category, different DRR
- [ ] `tests/test_pdf_report.py` — add `test_drr_split_rows` verifying PDF table has two rows when `workload_groups` has two entries for same category
- [ ] `tests/test_excel_report.py` — add `test_drr_split_rows` verifying Excel breakdown sheet row count
- [ ] `tests/test_classification.py` — add tests for REDIS, NAGIOS, SOLARWINDS, VERITAS, NETBACKUP, NBU patterns
- [ ] `tests/test_pdf_report.py` — add `test_sankey_resolution` checking `fig.savefig` DPI or resulting PNG pixel dimensions via PIL

Note: `WorkloadGroupResult` constructor changes affect 30 test files that build `WorkloadGroupResult` directly. Adding `drr: float = 0.0` as a default avoids mass test breakage.

## Sources

### Primary (HIGH confidence)

- Source audit: `/src/store_predict/pipeline/calculation.py` — full read, exact bug location lines 136-158
- Source audit: `/src/store_predict/pipeline/classification.py` — full read, all rules, priority tiers, `ClassificationRule` dataclass format
- Source audit: `/src/store_predict/services/pdf_charts.py` — full read, exact `dpi=150` and `fig.savefig` call
- Source audit: `/src/store_predict/services/charts.py` — full read, ECharts Sankey node structure
- Source audit: `/src/store_predict/services/pdf_report.py` — lines 628-694, exact table rendering loop
- Source audit: `/src/store_predict/services/excel_report.py` — lines 140-188, exact breakdown sheet loop
- Source audit: `/src/store_predict/services/drr_table.py` — DRREntry/DRRTable, lookup by (category, subcategory) key
- Source audit: `/samples/DRR.csv` — all 43 DRR entries; VM Replication subcategories confirmed

### Secondary (MEDIUM confidence)

- matplotlib documentation: `Figure(figsize, dpi)` and `fig.savefig(format='png', dpi=dpi)` — DPI parameter controls rasterization resolution; verified against matplotlib architecture (non-interactive Agg backend renders directly to pixel buffer at requested DPI)
- ECharts Sankey documentation: node `name` must be unique within `data` array — confirmed from ECharts source structure in `charts.py`

### Tertiary (LOW confidence)

- None — all claims verified from project source code directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from installed packages and source imports
- Architecture: HIGH — all module locations and function signatures verified from source read
- Pitfalls: HIGH — identified from direct source analysis, not inference
- Test gaps: HIGH — verified by grepping tests for DRR-split and new pattern tests

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable internal codebase, no external API changes)
