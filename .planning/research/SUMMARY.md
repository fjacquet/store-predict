# Project Research Summary

**Project:** StorePredict v4.0 — Compute Sizing & VMware Health Checks
**Domain:** VMware pre-sales sizing tool — offline file analysis (RVTools + LiveOptics)
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

StorePredict v4.0 transforms the tool from a storage-only sizing tool into a full pre-sales assessment platform. The v3.0 baseline already provides a robust pipeline: RVTools and LiveOptics ingestion, a 43-rule classification engine, AG Grid review table, datastore layout engine, PDF/Excel export, i18n FR/EN, and 353 tests at 86% backend coverage. The v4.0 milestone adds five features: compute host sizing, a health/concerns page, per-VM IOPS surfaced in the grid, AG Grid UX improvements, and classification rule improvements. Critically, every single v4.0 feature is implementable with the existing stack — no new runtime dependencies are required, and all vCPU, RAM, and IOPS data already exist in the canonical DataFrame schema.

The recommended approach is to build in dependency order: grid UX and IOPS columns first (pure UI, zero risk), then classification improvements (reduces noise before health checks flag it), then the health check module, and finally the compute sizing page. Each phase adds a new pure-pipeline module following the established `layout_engine.py` pattern, with a corresponding NiceGUI page following the `layout_page.py` pattern. The architecture is clean, the contracts are well-defined, and the data flows are verified against the live codebase. The tool's key differentiator will be that it is the only tool combining storage sizing, compute sizing, health checks from offline data, and datastore layout — all from a static export file with no live vCenter required.

The primary risks are not technical but implementation-quality risks: AG Grid Community edition does not support row grouping (must use pandas-backed filtering instead), the `CANONICAL_COLUMNS` whitelist will silently drop columns added in parsers but not registered there, session JSON round-trips corrupt typed data (NaN becomes None, ints become floats), and duplicate VM names in customer exports corrupt the `getRowId` identity used for inline editing and IOPS join. All these pitfalls have clear prevention strategies confirmed against the live codebase and are addressed in the phase ordering below.

## Key Findings

### Recommended Stack

The existing stack — NiceGUI 3.x, pandas 2.2, openpyxl, ReportLab, python-i18n, matplotlib, and pytest — covers all v4.0 features without modification. The compute sizing math is pure arithmetic using `math.ceil()` from the Python stdlib. The health check engine is DataFrame scanning using pandas operations already in use. AG Grid Community (bundled with NiceGUI) supports all planned UX features — quick filter, column visibility sidebar, number column filters — with the important constraint that row grouping requires AG Grid Enterprise (which is not included).

**Core technologies:**

- `pandas>=2.2`: DataFrame canonical schema, aggregations for compute totals, health check scans — already installed
- `nicegui>=3.4`: NiceGUI AG Grid Community for the review grid (column defs, sidebar, quick filter) — already installed
- `math` (stdlib): `math.ceil()` for host count rounding in all sizing formulas — no new dependency
- `dataclasses` (stdlib): `@dataclass(frozen=True)` for `HealthFinding`, `HealthCheckResult`, `ComputeSizingResult` — consistent with existing `LayoutProposal` pattern
- `re` (stdlib): regex pattern matching for new OS-fallback classification rules — already used in `classification.py`

No changes to `pyproject.toml` are required for v4.0. Full detail in `.planning/research/STACK.md`.

### Expected Features

**Must have (table stakes):**

- Per-VM IOPS columns in the review grid — LiveOptics users uploaded IOPS data and expect to see it; data already in `CANONICAL_COLUMNS`
- Grid quick text search — any table with 100+ VMs requires global search; AG Grid `quickFilterText` is built-in
- Grid workload category filter — "Show only Unknown VMs" is the most-requested filter action
- Column visibility toggle — engineers hide columns not needed for a customer conversation
- Powered-off / template exclusion toggle — size only deployed, running VMs
- Data quality warnings — sizing based on dirty data produces wrong reports; engineers need to know before presenting
- Compute host count recommendation — RVTools provides vCPU + RAM; engineers expect a host count, not just storage sizing

**Should have (competitive):**

- Concerns/Health Check page from offline data — Runecast and VMware Skyline require live vCenter; this is a unique offline differentiator
- HA / N+1 / stretch cluster toggle — customers always ask "what if one host fails?"
- Fewer Unknown VMs via OS-based fallback improvements — Unknown VMs reduce DRR credibility
- Conservative vs aggressive vCPU ratio presets — engineers need to justify overcommit choices to customers

**Defer (v4.x+):**

- Stretch cluster (vMSC) per-site breakdown — N+1 covers 80% of use cases; vMSC requires site data not reliably in RVTools
- Parse vSnapshot / vTools tabs for snapshot age and VMware Tools version health checks — requires new parser + re-upload flow
- Per-cluster compute sizing — complex UI grouping; single-cluster aggregation covers most use cases
- Host hardware catalog (Dell PowerEdge presets) — useful polish; initial version uses user-supplied specs

Full prioritization matrix in `.planning/research/FEATURES.md`.

### Architecture Approach

All v4.0 features integrate into the existing three-layer architecture without violating any of its contracts. The pipeline layer (`pipeline/`) remains UI-free and fully testable. Session state continues to flow through `app.storage.tab` as JSON-serializable `list[dict]`. Two new pure pipeline modules are added following the `layout_engine.py` pattern: `health_checks.py` (DataFrame scanning to `HealthFinding` list) and `compute_sizing.py` (aggregate totals to `ComputeSizingResult`). Two new UI pages are added following the `layout_page.py` pattern: `/concerns` and `/compute`. The `vm_table.py` component receives new hidden column definitions (IOPS, CPU, RAM) with an AG Grid sidebar for visibility toggling. No new state keys are needed — compute and health check results are derived on-demand from the existing `vm_data` session key.

**Major components:**

1. `pipeline/health_checks.py` (NEW) — scans session row_data for data quality, classification quality, and VMware best practice findings; returns `HealthCheckResult` with severity-tagged `HealthFinding` objects
2. `pipeline/compute_sizing.py` (NEW) — takes `total_vcpus` and `total_ram_gib` aggregates from `CalculationSummary`, returns `ComputeSizingResult` with host counts for N+1/N+2/vMSC/A-P scenarios across configurable host specs
3. `ui/components/vm_table.py` (MODIFIED) — adds hidden IOPS, CPU, and memory column definitions; adds AG Grid `sideBar` with `agColumnsToolPanel`; adds `rowGroupPanelShow` for workload grouping display
4. `ui/pages/concerns.py` (NEW) — `/concerns` page, reads session data, calls `run_health_checks()`, renders findings grouped by severity; on-demand computation avoids stale state after user edits
5. `ui/pages/compute.py` (NEW) — `/compute` page, reads session data, calls `calculate()` then `compute_sizing()`, renders reactive host count table with overcommit ratio and HA mode toggles

Full data flow diagrams in `.planning/research/ARCHITECTURE.md`.

### Critical Pitfalls

1. **AG Grid row grouping requires Enterprise license** — NiceGUI ships Community only; use pandas-backed category filter chips above the grid instead of `rowGroup: true` in column definitions. Designing for Enterprise grouping requires a full grid rewrite to recover.

2. **`CANONICAL_COLUMNS` silently drops new parser columns** — both parsers end with `return result[CANONICAL_COLUMNS]`; any new column not registered in `columns.py` is silently stripped. Add to `CANONICAL_COLUMNS` first, test with real sample files, then add parser reads. Note: `num_cpus`, `memory_mib`, `peak_iops`, `avg_iops` are already registered — no parser changes needed for v4.0.

3. **Session JSON round-trip corrupts typed data** — `float('nan')` becomes `None`, integers may become floats, `memory_mib` unit (MiB vs MB) must be verified. Always use `pd.to_numeric(val, errors='coerce').fillna(0)` when reading compute columns from session row_data.

4. **Duplicate VM names corrupt `getRowId` and IOPS join** — AG Grid uses `vm_name` as row identity; RVTools exports with templates or clones often have duplicate names. Fix: add a stable integer `row_index` column during ingestion and update `getRowId` to use it. Also deduplicate `perf_df` on `vm_name` before the IOPS merge.

5. **Health check must read session state, not re-run classification** — if health check re-classifies from scratch, it ignores user edits made in the Review grid. The `/concerns` page must start with `df = load_session_data()` and derive all findings from the current edited session state.

6. **Powered-off VMs and templates inflate compute totals** — filter to `is_powered_on == True` and `is_template == False` as the first step in any compute aggregation. Display the count of excluded VMs prominently.

7. **i18n key parity gaps** — `python-i18n` silently returns the key string when a translation is missing; adding 20-30 keys per new page creates FR/EN drift. Add a pytest test asserting `set(en_keys) == set(fr_keys)` before the first new-page PR merges.

Full pitfall-to-phase mapping in `.planning/research/PITFALLS.md`.

## Implications for Roadmap

Based on combined research, a four-phase structure is recommended. The ordering follows hard dependencies identified in ARCHITECTURE.md and risk mitigation identified in PITFALLS.md.

### Phase 1: Grid UX and Per-VM IOPS Columns

**Rationale:** Entirely UI-layer changes to `vm_table.py` and `review.py`. Zero pipeline risk. All IOPS data already exists in session row_data — it only needs to be surfaced. This is the lowest-risk, highest-perceived-value change and validates the AG Grid sidebar pattern that Phase 3 and 4 pages will reuse. It also forces resolution of the `getRowId` duplicate VM name pitfall before any further grid work proceeds.

**Delivers:** IOPS columns (hidden by default, enabled via sidebar), grid quick search, workload filter, column visibility toggle, `num_cpus` and `memory_mib` columns (hidden by default). Pitfall resolution: `getRowId` switched to `row_index` for duplicate-safe row identity.

**Addresses:** F3 (per-VM IOPS), F4 (grid UX improvements) from FEATURES.md

**Avoids:** AG Grid Enterprise grouping trap (design filter chips in this phase), duplicate VM name corruption (fix `getRowId` in this phase), IOPS peak methodology misleading pre-sales (add `avg_iops` as primary, `peak_iops` as secondary, add column tooltips)

**Research flag:** Standard AG Grid Community patterns — no additional research needed. Verify `agColumnsToolPanel` works with NiceGUI v3.4 AG Grid Community bundle (MEDIUM confidence — confirmed in architecture research).

### Phase 2: Classification Rule Improvements

**Rationale:** Pure pipeline change with no UI side effects. Must precede the health check phase because the health check will flag "High Unknown VM ratio" — reducing unknowns first makes that signal actionable rather than noise. No dependencies on Phase 1.

**Delivers:** Reduced Unknown (Reducible) classification rate. OS-based fallback rules at priority 900+ for Windows Server, Linux distros (RHEL, CentOS, Ubuntu, Debian, SUSE, Oracle Linux). VM name pattern rules for generic application server patterns (`app`, `web`, `svc`, `srv`, `api` as word-boundary tokens). `classify_dataframe()` signature and return columns unchanged.

**Addresses:** F5 (classification improvements) from FEATURES.md

**Avoids:** Health check "Unknown VM ratio" concern being inflated by classifiable VMs, priority ordering risk (specific rules at 80-499 fire before OS fallback at 900+, preventing over-classification of SQL/Oracle VMs)

**Research flag:** Standard pattern extension — no additional research needed. Verify against sample data that Windows Server + generic VM names correctly classify (HIGH confidence — pattern validated in FEATURES.md research).

### Phase 3: Health Check Module and Concerns Page

**Rationale:** New pure pipeline module following the `layout_engine.py` pattern plus a new UI page following the `layout_page.py` pattern. Simpler than compute sizing (no reactive inputs, no math beyond DataFrame comparisons). Doing this before compute sizing validates the new-page architecture pattern at lower risk.

**Delivers:** `pipeline/health_checks.py` with 10+ health check functions covering data quality (zero provisioned storage, zero vCPU/RAM, no OS name, powered-off VM ratio, no IOPS data), classification quality (high Unknown ratio, large Unknown VMs), and best practice (oversized VMs, no cluster assignment, high DRR override). New `/concerns` page rendering findings grouped by severity (Critical/Warning/Info). Navigation link added to `layout.py`.

**Addresses:** F2 (concerns/health check page) from FEATURES.md, all three concern categories (A, B, C)

**Avoids:** Health check reading stale classification (enforced: page starts with `load_session_data()`, never re-runs pipeline), health check as blocking pipeline step (findings computed on-demand each page visit, not cached in session), health check flags on powered-off VMs (filter to `is_powered_on == True` before all checks)

**Research flag:** Standard pattern — no additional research needed. Health check logic is pure DataFrame comparisons; architecture pattern is established by `layout_engine.py` (HIGH confidence — verified against live codebase).

### Phase 4: Compute Sizing Module and Page

**Rationale:** New pure pipeline module plus a new UI page with the most user-facing complexity: reactive overcommit ratio inputs, HA mode radio buttons, vMSC toggle, host spec table. Build last so the simpler patterns established in Phases 1-3 are proven. The compute data (`num_cpus`, `memory_mib`, `total_cpus`, `total_memory_mib`) is already fully parsed and aggregated by `CalculationSummary` — no parser changes needed.

**Delivers:** `pipeline/compute_sizing.py` with `HostConfig`, `ComputeSizingResult`, `compute_sizing()` function. Host count recommendations for 4 default Dell PowerEdge configurations (R760/28c, R760/32c, R860/28c, R960/32c). N+1 and N+2 HA modes. vMSC toggle with datacenter validation warning. Active/Passive column. New `/compute` page with reactive overcommit ratio input and HA mode selector. Navigation link added to `layout.py`.

**Addresses:** F1 (compute sizing page) from FEATURES.md

**Avoids:** Powered-off/template inflation (filter before aggregation, display exclusion count), session round-trip type corruption (use `pd.to_numeric` with `fillna(0)` for all compute columns), vMSC with missing site data (validate `datacenter` column has 2+ distinct values before showing vMSC results), compute page bypassing `calculate()` (use `CalculationSummary.total_cpus` not a raw DataFrame sum), compute page auto-calculating before inputs are set (show editable inputs panel first, require explicit "Calculate" click)

**Research flag:** Sizing formulas are well-documented (HIGH confidence). vMSC sizing requires site topology awareness that RVTools vInfo does not reliably provide — implement with datacenter validation and graceful degradation warning. Host config catalog (PowerEdge specs) should be validated with a Dell partner/SE before customer presentations.

### Phase Ordering Rationale

- **Phase 1 before all others:** Grid UX has no dependencies, and fixing `getRowId` to use `row_index` for duplicate-safe identity must happen before any further grid work. Validates the AG Grid sidebar pattern reused in later pages.
- **Phase 2 before Phase 3:** Classification improvements reduce Unknown VM ratio before health checks flag it — otherwise the health check "High Unknown ratio" concern appears on every customer dataset, diluting its signal.
- **Phase 3 before Phase 4:** Health check page is simpler (no reactive inputs) and validates the new-page architecture pattern at lower cost before the more complex compute page.
- **Phase 4 last:** Highest UI complexity (reactive inputs, multi-scenario table, vMSC/AP toggle logic). Benefits from patterns established in Phases 1-3.

### Research Flags

Phases needing additional research during planning:

- **Phase 4 (vMSC sizing):** The stretch cluster formula and site topology requirements are well-documented but the graceful degradation UX (single-datacenter warning) needs stakeholder input on acceptable fallback behavior.
- **Phase 4 (host config catalog):** The 4 default PowerEdge configurations are reasonable starting points, but validating correct cores-per-socket, HT factor, and typical RAM configs with Dell product specs would improve accuracy.

Phases with standard patterns (skip research-phase):

- **Phase 1 (Grid UX):** AG Grid Community API is well-documented; patterns are established in the existing codebase.
- **Phase 2 (Classification):** Pure Python rule extension; the existing `RuleRegistry` and priority system are fully understood.
- **Phase 3 (Health Checks):** DataFrame scanning with established pipeline pattern; no novel integrations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against live `pyproject.toml`; no new dependencies needed; all formulas confirmed as pure stdlib math |
| Features | HIGH | Table stakes verified against competitor tool gap analysis (RVTools vHealth, Runecast, vSphere Cluster Calculator); Broadcom TechDocs confirm industry-standard compute sizing formulas |
| Architecture | HIGH | All integration points verified against live source code (`columns.py`, `calculation.py`, `parsers/rvtools.py`, `parsers/liveoptics.py`, `vm_table.py`); IOPS columns confirmed present in schema, absent from grid |
| Pitfalls | HIGH | Most pitfalls verified against live codebase inspection + NiceGUI community discussions + official AG Grid docs; `getRowId` duplicate issue confirmed via AG Grid v23+ changelog |

**Overall confidence:** HIGH

### Gaps to Address

- **LiveOptics CPU/RAM availability:** `num_cpus` and `memory_mib` are confirmed in `CANONICAL_COLUMNS` and parsed from RVTools. Verify they are also populated for LiveOptics uploads before enabling the `/compute` page for that format — FEATURES.md flagged this as needing verification.
- **AG Grid `agColumnsToolPanel` in NiceGUI v3.4:** Confirmed as AG Grid Community feature; verify the exact `sideBar` configuration object syntax is compatible with NiceGUI's `ui.aggrid` wrapper (MEDIUM confidence — architecture research references it as used in v3.0 `layout_page.py`).
- **vMSC minimum cluster size:** Broadcom documents minimum 3+3 hosts per site + witness for vSAN stretched. For non-vSAN compute-only stretched clusters the minimum is 2+2. The v4.0 compute page should clarify which topology the customer is sizing for.
- **`memory_mib` unit consistency:** PITFALLS.md flags potential MiB vs MB unit mismatch from RVTools version differences. Add a sanity check during ingestion that flags suspiciously small values (less than 64 MiB for a production VM).

## Sources

### Primary (HIGH confidence)

- `pyproject.toml` at project root — all installed dependencies verified directly
- `src/store_predict/pipeline/parsers/columns.py` — CANONICAL_COLUMNS schema, RVTOOLS_ALIASES confirmed
- `src/store_predict/pipeline/calculation.py` — CalculationSummary.total_cpus and total_memory_mib confirmed
- `src/store_predict/pipeline/parsers/rvtools.py` and `liveoptics.py` — num_cpus, memory_mib, peak_iops extraction confirmed
- `src/store_predict/ui/components/vm_table.py` — IOPS columns confirmed absent from grid column definitions
- [Broadcom KB 312100 — ESXi hosts and compatible VM hardware versions](https://knowledge.broadcom.com/external/article/312100) — official compatibility matrix
- [VMware vSAN Stretched Cluster Guide](https://www.vmware.com/docs/vsan-stretched-cluster-guide) — 50% admission control per site
- [VMware Architecture Toolkit — vCPU-to-pCPU ratio](https://download3.vmware.com/vcat/) — official guidance on pCPU (not logical threads) for sizing
- [AG Grid Community vs Enterprise features](https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise/) — row grouping is Enterprise-only confirmed
- [Broadcom TechDocs VCF — Sizing Compute Resources for ESXi](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/) — industry-standard formula confirmed

### Secondary (MEDIUM confidence)

- [NiceGUI AG Grid discussions — row grouping Enterprise limitation](https://github.com/zauberzeug/nicegui/discussions/3182) — confirmed Community limitation
- [NiceGUI AG Grid — cellValueChanged only fires on actual value change](https://github.com/zauberzeug/nicegui/discussions/2887) — AG Grid v23+ behavior
- [Broadcom KB 315655 — Virtual machine hardware versions](https://knowledge.broadcom.com/external/article/315655) — HW version to ESXi mapping (could not fetch directly; corroborated by multiple community sources)
- [virten.net — Virtual Machine Hardware Versions](https://www.virten.net/vmware/virtual-machine-hardware-versions/) — vmx version table
- [vSphere Cluster Overcommit Ratios — Brock Peterson Blog](https://www.brockpeterson.com/post/vsphere-cluster-overcommit-ratios-in-aria-operations) — 4:1 CPU ratio community standard

### Tertiary (LOW confidence)

- VMware vCPU overcommit ratios various community sources — 4:1 ratio is widely cited; Broadcom 2025 guidance recommends 1:1 for performance-sensitive workloads; validate with customer workload profile
- Dell PowerEdge R760/R860/R960 core counts — need validation against current product specs before using as default presets

---
*Research completed: 2026-02-22*
*Ready for roadmap: yes*
