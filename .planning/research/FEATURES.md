# Feature Research — StorePredict v4.0

**Domain:** VMware pre-sales sizing tool — compute sizing, health checks, IOPS display, grid UX, classification
**Researched:** 2026-02-22
**Confidence:** MEDIUM-HIGH (domain knowledge verified with VMware/Broadcom official docs + LiveOptics support docs + community sources)

---

## Context: What Already Exists (v3.0 baseline)

The following features are DONE and must not be re-built:

- RVTools + LiveOptics ingestion; `num_cpus`, `memory_mib`, `is_powered_on`, `is_template`, `peak_iops`, `avg_iops` already in CANONICAL_COLUMNS
- 43-rule classification engine with OS-fallback tier (priority 900-949) and LLM fallback
- AG Grid review table (editable workload dropdown, DRR override, multi-select, bulk update)
- Datastore layout engine (3 strategies, /layout page)
- PDF + Excel export, i18n FR/EN, Docker deployment
- 353 tests, 86% backend coverage, 6,802 LOC Python

The v4.0 milestone adds: compute sizing, health/concerns page, per-VM IOPS in grid, grid UX improvements, and classification rule improvements.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features pre-sales engineers assume exist in a VM assessment tool. Missing these makes the tool feel incomplete compared to RVTools, Runecast, or vSphere Cluster Calculator.

| Feature | Why Expected | Complexity | Existing Dependencies |
|---------|--------------|------------|----------------------|
| Per-VM IOPS in the review grid | LiveOptics already collects it; users uploaded it and expect to see it | LOW | `peak_iops`, `avg_iops` already in CANONICAL_COLUMNS and parsed from LiveOptics; only AG Grid column defs need updating |
| Grid quick text search | Any data table with 100+ VMs needs a global search box | LOW | AG Grid `quickFilterText` built-in; NiceGUI `ui.input` binds to it via `run_grid_method` |
| Filter by workload category | "Show only Unknown VMs" is the most-requested filter action | LOW | AG Grid built-in set filter on `workload_category` column |
| Column visibility toggle | Engineers hide columns not needed for a customer conversation | LOW | AG Grid Column Tool Panel or custom header checkbox group; well-documented |
| Powered-off / template exclusion | Size only powered-on, non-template VMs; templates are not deployed | LOW | `is_powered_on` and `is_template` already parsed; toggle to exclude from sizing totals |
| Data quality warnings | If sizing is based on dirty data, the report is wrong; engineers need to know before presenting | MEDIUM | No concerns page exists; new analysis module + page needed |
| Compute host count recommendation | RVTools provides vCPU + RAM; engineers expect a host count, not just storage | HIGH | `num_cpus` and `memory_mib` already in canonical schema; new sizing engine + page needed |

### Differentiators (Competitive Advantage)

Features that make StorePredict better than ad-hoc spreadsheets or point tools like vSphere Cluster Calculator.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Concerns / Health Check page from offline data | Detects data quality issues and VMware best practice risks from a static export file — no live vCenter access required | HIGH | Runecast and VMware Skyline require live vCenter; this works from exported files only |
| Compute + storage + layout in one tool | Engineers currently switch between vSphere Cluster Calculator (compute), StorePredict (storage), and Excel (layout); unified view saves time | HIGH | New `/compute` page; depends on already-parsed RVTools data |
| HA / N+1 / stretch cluster toggle | Customers always ask "what if one host fails?" — pre-sales must justify the host count | MEDIUM | Multiplier logic; high perceived value; Broadcom documents the formula |
| Conservative vs aggressive vCPU ratio presets | Broadcom 2025 guidance recommends 1:1 for safety; most tools default to 4:1 without explaining the risk | MEDIUM | Preset dropdown with consequence description helps engineers justify the recommendation |
| Fewer Unknown VMs (OS-based fallback improvements) | Unknown VMs reduce DRR credibility; fewer unknowns means a more defensible report | MEDIUM | Extend existing RuleRegistry tier 900-949 OS fallbacks; add generic app-server patterns |
| IOPS-aware column highlighting | Visual indicator of IOPS-heavy VMs helps explain storage tiering decisions | MEDIUM | Color-coded cell renderers; already done for layout page |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Live vCenter connection | "Why export a file — just connect directly?" | Security risk; credentials required; firewall issues; explicitly out of scope per PROJECT.md | Upload-only model is simpler and trustworthy for customer-facing use |
| Snapshot age health check | Engineers expect it from RVTools vHealth tab | vInfo export does NOT contain snapshot metadata; vSnapshot is a separate tab requiring a different upload | Flag in Concerns as "Not detectable from vInfo export alone — use RVTools vHealth tab" |
| Per-host ESXi version check | Useful for patch compliance | Host metadata is in vHost tab, not vInfo; requires separate parser | Out of scope for v4.0; document as future extension |
| Network health checks (VLAN, MTU) | Common in health assessments | No network data in vInfo or LiveOptics exports | Document as out of scope |
| Real-time HA failover simulation | Simulate which VMs restart on which hosts | Requires DRS/HA scheduling algorithms; massive complexity | N+1 headroom calculation covers 90% of the use case |
| Per-cluster compute sizing | Some customers have multiple clusters | Complex UI with multi-cluster grouping | Single-cluster aggregation for v4.0; per-cluster deferred to v5+ |

---

## Feature Deep Dives

### Feature 1: Compute Sizing Page (`/compute`)

**Industry-standard behavior (HIGH confidence — from Broadcom TechDocs, vSphere Cluster Calculator, WintelGuy vmcalc):**

Pre-sales engineers follow this mental model:

1. Sum all vCPUs across powered-on, non-template VMs
2. Sum all RAM (MiB) across same filtered VM set
3. Choose target host spec: cores per host, sockets per host, RAM per host (GiB)
4. Choose vCPU:pCore ratio (preset or manual):
   - Conservative: 1:1 (Broadcom 2025 recommendation for performance-sensitive workloads)
   - Standard: 2:1 to 4:1 (typical mixed workloads)
   - Aggressive: 6:1 to 8:1 (Dev/Test, idle workloads)
5. Calculate hosts-needed-for-CPU: `ceil(total_vcpus / (cores_per_host * vcpu_ratio))`
6. Calculate hosts-needed-for-RAM: `ceil(total_ram_mib / (ram_per_host_mib * (1 - ram_overhead_pct)))`
7. Take the binding constraint: `host_count_raw = max(cpu_hosts, ram_hosts)`
8. Apply HA model:
   - **None:** `host_count = host_count_raw`
   - **N+1:** `host_count = host_count_raw + 1` (standard; reserves resources of one host for failover)
   - **N+2:** `host_count = host_count_raw + 2` (maintenance window without losing HA)
   - **Stretch Active/Active (vMSC):** `host_count = host_count_raw * 2` minimum 3+3 per site + witness
   - **Stretch Active/Passive:** `host_count = host_count_raw + standby_site_hosts`
9. Display: recommended host count, achieved vCPU ratio, RAM utilization %, headroom %

**Broadcom 2025 guidance (HIGH confidence):**

- 1:1 ratio without hyperthreading = safe conservative start
- Admission control N+1 is the standard HA setting for production
- Stretch cluster minimum: 6 hosts (3 per AZ) + witness in 3rd AZ; requires vSphere Enterprise Plus

**Data already available from RVTools parse:**

- `num_cpus` — vCPU count (already parsed in `rvtools.py`)
- `memory_mib` — RAM per VM (already parsed)
- `is_powered_on` — exclusion filter (already parsed)
- `is_template` — exclusion filter (already parsed)
- `cluster` — grouping field (already parsed)

**New UI inputs needed:**

- Target host spec: cores per host, RAM per host GiB (text inputs or preset dropdown)
- vCPU:pCore ratio (dropdown: 1:1 / 2:1 / 4:1 / 6:1 / custom)
- HA model (radio/toggle: None / N+1 / N+2 / Stretch AA / Stretch AP)
- RAM overhead % (default 10%)
- Include/exclude powered-off VMs toggle

**Complexity:** HIGH — new page, new `compute_sizing.py` module, new i18n keys, new PDF/Excel section, new tests (~20-30 test cases)

---

### Feature 2: Concerns / Health Check Page (`/concerns`)

**Industry standard checks from static export data (MEDIUM confidence — derived from RVTools vHealth 21-check list, Runecast, VMware HealthAnalyzer):**

**Category A — Data Quality Issues (directly affect sizing accuracy):**

| Check | Detection Logic | Severity |
|-------|----------------|---------|
| VMs with zero provisioned storage | `provisioned_mib == 0` | HIGH — distorts capacity calculation |
| Provisioned < In-Use storage | `in_use_mib > provisioned_mib` | HIGH — data corruption indicator |
| VMs with zero vCPUs or RAM | `num_cpus == 0 or memory_mib == 0` | MEDIUM — missing compute data |
| High powered-off VM ratio | `is_powered_on == False` count > 10% of total | MEDIUM — inflates sizing if included |
| Templates in VM list | `is_template == True` count > 0 | LOW — should be excluded from sizing |
| VMs with empty OS name | `os_name == ""` | LOW — reduces classification accuracy |
| No LiveOptics IOPS data | `peak_iops.isna().all()` (RVTools-only upload) | MEDIUM — IOPS sizing is estimated, not measured |

**Category B — Classification Quality Issues (affect DRR accuracy):**

| Check | Detection Logic | Severity |
|-------|----------------|---------|
| High Unknown VM ratio | `Unknown (Reducible)` > 20% of VM count | HIGH — DRR estimate unreliable |
| Large Unknown VMs | Unknown VMs with `provisioned_mib > 500 GiB` | HIGH — large VMs drive capacity; their DRR is guessed |
| Single workload type (no diversity) | All VMs in one category | LOW — informational; may indicate under-classification |

**Category C — VMware Best Practice Concerns (from vInfo data):**

| Check | Detection Logic | Severity |
|-------|----------------|---------|
| Very high single-VM vCPU count | `num_cpus > 16` | MEDIUM — NUMA boundary risk; VMware perf best practices |
| Very large single-VM provisioned storage | `provisioned_mib > 2_000_000` (2 TB) | MEDIUM — sizing risk; single point of failure |
| High RAM-per-vCPU ratio | `memory_mib / num_cpus > 32768` (32 GiB/vCPU) | LOW — possible oversizing |
| Single cluster in environment | `cluster.nunique() <= 1` with > 100 VMs | LOW — no isolation; informational |

**What cannot be detected from vInfo-only (must be explicit in UI):**

- Snapshot age (requires vSnapshot tab — not parsed)
- VMware Tools version (requires vTools tab — not parsed)
- Network configuration (requires vNetwork tab)
- Host hardware details (requires vHost tab)

**UX pattern (standard in Runecast, VMware HealthAnalyzer):**

- Card layout grouped by severity: Critical (red) / Warning (amber) / Info (gray-blue)
- Each concern card: title, description, affected VM count, example VMs (max 5), recommended action
- Summary badge count per severity level in page header
- Export concerns section to PDF (additional page) and Excel (new sheet)

**Complexity:** HIGH — new `concerns.py` analysis module, new `/concerns` page, new data models, i18n, PDF/Excel integration, ~30-40 test cases

---

### Feature 3: Per-VM IOPS in Grid

**Industry standard behavior:**

When a LiveOptics file is uploaded, engineers expect to see IOPS alongside storage metrics in the same table. This is the data LiveOptics was collected to provide.

**What already exists:**

- `peak_iops` and `avg_iops` are in CANONICAL_COLUMNS
- LiveOptics parser already populates both from `Peak IOPS` / `Average IOPS` columns in VM Performance tab
- RVTools sets these to `NaN` (correct behavior — no performance data)
- These columns are in the DataFrame but NOT shown in the current AG Grid

**What needs to be added:**

- Add `peak_iops` and `avg_iops` to AG Grid column definitions in the review grid
- Format as integers with comma separators (e.g., `1,234`); show `—` for `NaN`
- Optional but high-value: color-coded cell renderer (>1,000 IOPS = amber; >5,000 = red)
- Columns sortable and filterable

**LiveOptics performance columns already in schema (from `parsers/columns.py`):**

- `peak_iops`, `avg_iops`
- `peak_throughput_mbs`, `avg_throughput_mbs`
- `peak_latency_ms`, `avg_read_latency_ms`, `avg_write_latency_ms`
- `iops_8k_equivalent`

**Recommendation:** Show `peak_iops` and `avg_iops` by default. Hide latency and throughput columns behind column visibility toggle to avoid grid crowding.

**Complexity:** LOW — data exists in DataFrame; pure AG Grid column definition change in `vm_table.py` (or equivalent component)

---

### Feature 4: Grid UX Improvements

**Industry standard for 100–5,000 VM data tables:**

| UX Feature | AG Grid Mechanism | Complexity |
|------------|------------------|------------|
| Quick text search box | `quickFilterText` via `run_grid_method('setQuickFilter', text)` | LOW |
| Filter by workload category | Built-in set filter on `workload_category` column | LOW |
| Column show/hide toggle | Column Tool Panel or custom button group using `setColumnVisible` | LOW |
| Powered-off / template exclusion toggle | `isExternalFilterPresent` + `doesExternalFilterPass` callbacks | MEDIUM |
| Sort by IOPS descending | Standard sortable column (depends on F3) | LOW |
| Group by workload | `rowGroup: true` in column def — available in AG Grid Community | MEDIUM |
| Bulk workload reassign on filtered rows | Extend existing multi-select; apply to filtered rows only | MEDIUM |

**AG Grid Community vs Enterprise constraint:**
NiceGUI uses AG Grid Community by default. Community supports: column filters, quick filter, row sorting, column hide/show, client-side row grouping. Enterprise-only features (not available without license): server-side grouping with aggregation, pivot, advanced filter builder, Excel export from grid. Do NOT build features requiring Enterprise.

**Complexity:** LOW-MEDIUM overall; no new backend logic required

---

### Feature 5: Classification Rule Improvements

**Current state:**

- 43 rules, priority tiers 80-999
- OS-fallback tier (900-949) exists but has limited patterns
- LLM fallback handles truly ambiguous cases

**Root causes of Unknown VM classification:**

1. Generic VM names with no meaningful keywords (`VM-0042`, `PROD-APP-01`, `SRV001`)
2. Linux OS variants not in current OS-fallback patterns (`Other Linux (64-bit)`, `CentOS Linux (64-bit)`, `Debian GNU/Linux (64-bit)`)
3. Windows Server VMs without DB/App signal — should become `Virtual Machines/VMware...` not Unknown
4. Kubernetes/OpenShift node names that don't match current patterns
5. Customer-specific abbreviations that don't use the documented keywords

**Improvement approach (HIGH confidence):**

Extend tier 900-949 (OS-based fallback) with more OS string patterns:

- All `*Linux*` OS variants → `Virtual Machines/VMware / Hyper-V / KVM`
- All `*Windows Server*` OS variants → `Virtual Machines/VMware / Hyper-V / KVM`
- `*Ubuntu*`, `*Debian*`, `*CentOS*`, `*Red Hat*`, `*SUSE*` → `Virtual Machines` category

Add a new tier 500-549 for generic application-server VM name patterns:

- `app`, `web`, `svc`, `srv`, `api` as standalone tokens (word-boundary patterns)
- This covers common patterns that are clearly application workloads but don't map to a specific DB/VDI

**Risk:** Broad OS-based fallbacks may over-classify a SQL Server VM with generic name as `Virtual Machines` instead of `Database/Microsoft SQL`. Priority ordering (specific rules at 80-499 before OS fallback at 900+) prevents this — existing behavior is correct.

**Complexity:** MEDIUM — pure Python in `classification.py`; no new dependencies; requires careful test coverage with real Unknown VM names from sample data

---

## Feature Dependencies

```
F3: Per-VM IOPS in Grid
    └── no new dependencies — data already in canonical DataFrame
    └── enhances → F4: Grid UX (IOPS sort/filter only useful with data)

F4: Grid UX Improvements
    └── no new backend dependencies
    └── enhances → F3 (sort/filter on IOPS columns)
    └── enhances → F5 (filter by Unknown workload shows improvement)

F5: Classification Rule Improvements
    └── extends → existing RuleRegistry in classification.py
    └── reduces severity of → F2 "High Unknown VM ratio" concern

F2: Concerns / Health Check Page
    └── reads → existing canonical DataFrame (no new data for Category A+B)
    └── new → concerns.py analysis module + /concerns route
    └── optional future → parse vSnapshot tab (snapshot age checks)
    └── cross-links → F1 (concern: "X powered-off VMs excluded from compute sizing")

F1: Compute Sizing Page
    └── reads → num_cpus, memory_mib, is_powered_on, is_template (all in canonical DataFrame)
    └── new → compute_sizing.py module + /compute route
    └── new → PDF/Excel sections for compute summary
```

### Dependency Notes

- **F3 has no backend dependencies.** It is the lowest-risk and fastest-to-ship feature. Data already exists; it is a pure AG Grid column definition change.
- **F4 should ship alongside F3.** Adding IOPS columns without sort/filter/search makes large datasets harder to use.
- **F5 is independent but synergistic.** Better classification reduces the severity of the "High Unknown VM ratio" health concern in F2.
- **F2 and F1 are new pages.** Both require new Python modules, new routes, new i18n keys, new PDF/Excel sections, and new tests. They are the highest-effort features in v4.0.
- **F1 requires RVTools source data for compute sizing.** LiveOptics does export CPU/RAM, but verify `num_cpus` and `memory_mib` are populated for LiveOptics uploads before enabling the `/compute` page for that format.
- **No circular dependencies.** All features can be developed in parallel; F4 depends on F3 being useful (implicit), but not a hard code dependency.

---

## MVP Definition for v4.0

### Launch With (v4.0 scope)

Minimum set that delivers the milestone goal: "Transform StorePredict from storage-only into a full pre-sales assessment platform."

- [ ] **F3: Per-VM IOPS columns in grid** — lowest effort, highest perceived value; shows LiveOptics data is fully utilized
- [ ] **F4: Grid quick search + workload filter + column visibility** — table stakes for 100+ VM lists
- [ ] **F4: Powered-off / template exclusion toggle** — engineers expect this for accurate sizing
- [ ] **F5: Classification OS-based fallback improvements** — reduce Unknown VMs below 20% on typical customer data
- [ ] **F2: Data quality concerns (Category A)** — data correctness flags; directly affects report credibility
- [ ] **F2: Classification quality concerns (Category B)** — Unknown VM ratio flags with guidance
- [ ] **F1: Compute sizing page (basic N+1)** — vCPU/RAM totals, host count, N+1 HA toggle
- [ ] **F2: VMware best practice concerns (Category C)** — oversized VMs, high vCPU count flags

### Add After Validation (v4.x)

- [ ] Stretch cluster (vMSC) sizing with per-site breakdown — N+1 covers 80% of use cases
- [ ] Parse vSnapshot tab for snapshot age health checks — requires new parser + user re-upload flow
- [ ] Parse vTools tab for VMware Tools version health check — same cost as vSnapshot
- [ ] IOPS heatmap color coding in grid — visual polish
- [ ] Concerns export as separate PDF page — useful but not blocking

### Future Consideration (v5+)

- [ ] Per-cluster compute sizing (group VMs by cluster, size each independently)
- [ ] Host hardware catalog (pre-defined Dell PowerEdge specs for compute sizing presets)
- [ ] AI-assisted rule suggestion surfaced in UI (beyond current log output)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| F3: Per-VM IOPS columns | HIGH | LOW | P1 |
| F4: Grid quick search | HIGH | LOW | P1 |
| F4: Grid workload filter | HIGH | LOW | P1 |
| F4: Grid column visibility | MEDIUM | LOW | P1 |
| F5: Classification OS fallback rules | HIGH | MEDIUM | P1 |
| F2: Data quality concerns (Cat A) | HIGH | MEDIUM | P1 |
| F1: Compute sizing — basic N+1 | HIGH | HIGH | P1 |
| F4: Powered-off exclusion toggle | MEDIUM | MEDIUM | P2 |
| F2: Classification quality (Cat B) | MEDIUM | MEDIUM | P2 |
| F2: Best practice concerns (Cat C) | MEDIUM | MEDIUM | P2 |
| F1: Stretch cluster sizing | MEDIUM | HIGH | P2 |
| F4: Row grouping by workload | LOW | MEDIUM | P3 |
| F2: Snapshot age check (new parser) | MEDIUM | HIGH | P3 |

**Priority key:**

- P1: Must have for v4.0 launch
- P2: Should have; add when possible in v4.0
- P3: Nice to have; defer to v4.x

---

## Competitor Feature Analysis

| Feature | RVTools vHealth | vSphere Cluster Calculator | Runecast | StorePredict v4.0 |
|---------|----------------|---------------------------|----------|------------------|
| Compute sizing | No | Yes (manual host spec) | No | Yes — from RVTools data automatically |
| Health checks | 21 checks (requires live vCenter) | No | Yes (requires live vCenter) | Yes — from static export, no vCenter needed |
| Storage sizing + DRR | No | No | No | Yes (v1.0+) |
| Per-VM IOPS display | No | No | No | Yes — from LiveOptics |
| Datastore layout | No | No | No | Yes (v3.0) |
| PDF / Excel export | No | No | No | Yes |
| No live vCenter needed | Yes | Yes | No | Yes |
| Unified tool (all 4 capabilities) | No | No | No | Yes (v4.0 goal) |

**Key differentiator:** StorePredict v4.0 is the only tool that combines storage sizing, compute sizing, health checks from offline data, AND datastore layout recommendations from a static export file. No competitor tool does all four.

---

## Sources

- [Virtual CPU to Physical CPU Ratios: Are They Still Relevant? — Broadcom VCF Blog, June 2025](https://blogs.vmware.com/cloud-foundation/2025/06/04/vcpu-to-pcpu-ratio-guidelines/)
- [Sizing Compute Resources for ESXi — Broadcom TechDocs VCF 4.5](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-5-2-and-earlier/4-5/vcf-design-management-domain-4-5/vcf-esxi-design/vcf-deployment-specification-for-esxi/vcf-physical-design-for-esxi.html)
- [vSphere Cluster Calculator User Guide — vmusketeers.com](https://vmusketeers.com/userguide-vsphere-cluster-calculator/)
- [RVTools as a health check tool — vInfrastructure Blog](https://vinfrastructure.it/2017/09/rvtools-healt-check-tool/)
- [Best practices for VMware snapshots — Broadcom KB 318825](https://knowledge.broadcom.com/external/article/318825/best-practices-for-using-vmware-snapshot.html)
- [VMware Skyline Health Diagnostics Tool — Broadcom TechDocs vSphere 8.0](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-monitoring-and-performance/monitoring-and-diagnostics-of-vsphere-health/vmware-skyline-health-diagnostics-tool.html)
- [Optical Prime VM Performance Data — Live Optics Support](https://support.liveoptics.com/hc/en-us/articles/360060070213-Optical-Prime-VM-Performance-Data)
- [Optical Prime VMware Excel Definitions — Live Optics Support](https://support.liveoptics.com/hc/en-us/articles/1260802114709-Optical-Prime-VMware-Excel-Definitions)
- [AG Grid Quick Filter — Official Docs](https://www.ag-grid.com/javascript-data-grid/filter-quick/)
- [AG Grid Row Grouping — Official Docs](https://www.ag-grid.com/javascript-data-grid/grouping-filtering/)
- [Analyzing RVTools Data — sizing-workshop.readthedocs.io](https://sizing-workshop.readthedocs.io/en/latest/datacollection/rvtools/rvtools.html)
- [Performance Best Practices for VMware vSphere 8.0 — Broadcom](https://www.vmware.com/docs/vsphere-esxi-vcenter-server-80-performance-best-practices)
- [vSphere Cluster Overcommit Ratios in Aria Operations — Brock Peterson Blog](https://www.brockpeterson.com/post/vsphere-cluster-overcommit-ratios-in-aria-operations)

---

*Feature research for: StorePredict v4.0 — compute sizing, health checks, IOPS display, grid UX, classification*
*Researched: 2026-02-22*
