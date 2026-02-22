# Architecture Research

**Domain:** Data processing web tool — v4.0 feature integration (compute sizing, health checks, per-VM IOPS, grid UX, classification improvements)
**Researched:** 2026-02-22
**Confidence:** HIGH (all integration points verified against actual source code)

---

## Context: Existing Architecture Snapshot (as of v3.0)

The current production structure after v3.0. This is the baseline for all v4.0 integration analysis.

```
src/store_predict/
  main.py                          # ui.run(), page route imports
  config.py                        # Paths, APP_PORT, StorageModel enum
  logging_config.py                # Logger; never log VM names or DataFrames

  pipeline/                        # Pure functions — zero UI imports
    ingestion.py                   # ingest_file() — detect + dispatch to parser
    classification.py              # RuleRegistry, ClassificationRule, classify_dataframe()
    calculation.py                 # CalculationSummary, calculate()
    layout_engine.py               # generate_all_proposals() — BFD placement
    layout_models.py               # DatastoreRecommendation, LayoutProposal, PlacementConstraints
    models.py                      # FileFormat enum
    validation.py                  # File extension + magic bytes checks
    errors.py                      # IngestionError
    llm_classifier.py              # LLM fallback for unmatched VMs
    zip_extraction.py              # .zip auto-extraction for LiveOptics archives
    parsers/
      __init__.py                  # re-exports parse_rvtools, parse_liveoptics_*
      columns.py                   # CANONICAL_COLUMNS, RVTOOLS_ALIASES, LIVEOPTICS_ALIASES
      rvtools.py                   # parse_rvtools() — reads vInfo sheet
      liveoptics.py                # parse_liveoptics_xlsx/csv() — reads VMs + VM Performance sheets

  services/
    drr_table.py                   # DRRTable.from_csv(), get_ratio(), apply_storage_model()
    pdf_report.py                  # generate_report_pdf(summary, project_name) -> bytes
    pdf_charts.py                  # ReportLab chart helpers
    excel_report.py                # generate_excel_report() -> bytes
    charts.py                      # ECharts helpers for web UI
    llm_config.py                  # LLM provider config dataclass
    playwright_pdf.py              # Playwright-based layout PDF generation
    print_session.py               # Print session token management

  i18n/                            # Translation infrastructure
    __init__.py                    # t() helper, get_locale(), set_locale()
    locales/en.yaml                # English string catalog
    locales/fr.yaml                # French string catalog (primary locale)

  ui/
    layout.py                      # layout() context manager — header, nav, dark toggle, locale toggle
    state.py                       # save/load session via app.storage.tab (JSON-serialized dicts)
    pages/
      upload.py                    # /upload — file upload, ingestion + classification trigger
      review.py                    # /review — AG Grid edit, workload dialogs, bulk update
      report.py                    # /report — summary cards, PDF/Excel download
      report_print.py              # /report/print — printable report page
      layout_page.py               # /layout — datastore layout recommendations, 3 strategies
    components/
      vm_table.py                  # create_vm_table() — AG Grid with inline editors
      workload_dialog.py           # WorkloadDialog — async multi-select dialog
      summary_stats.py             # build_summary_stats() — live metric cards
      dark_mode_toggle.py
      locale_toggle.py

  data/
    DRR.csv                        # Reference DRR ratios (28 workload categories)
    IOPS.csv                       # Default IOPS estimates by workload (fallback for RVTools)
```

**CANONICAL_COLUMNS (the DataFrame schema crossing pipeline stages):**

```python
CANONICAL_COLUMNS = [
    "vm_name", "os_name",
    "num_cpus", "memory_mib",              # Already extracted from both RVTools and LiveOptics
    "provisioned_mib", "in_use_mib",
    "datacenter", "cluster",
    "is_template", "is_powered_on",
    "source_format", "vm_description",
    "peak_iops", "avg_iops",               # Per-VM IOPS — exists in schema, populated for LiveOptics
    "peak_throughput_mbs", "avg_throughput_mbs",
    "peak_latency_ms", "avg_read_latency_ms", "avg_write_latency_ms",
    "iops_8k_equivalent",
]
```

**Critical architecture contracts (must not be violated):**

- `pipeline/` never imports from `ui/` — pipeline is fully testable without NiceGUI
- Session state lives in `app.storage.tab` as JSON-serializable `list[dict]`
- `classify_dataframe()` adds: `workload_category`, `workload_subcategory`, `classification_rule`, `classification_confidence`
- `calculate()` accepts `list[dict[str, Any]]` (row_data from session), returns `CalculationSummary`
- `generate_all_proposals()` accepts `CalculationSummary` + `PlacementConstraints`, returns `list[LayoutProposal]`

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UI Layer (NiceGUI)                                 │
│                                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐   │
│  │ /upload  │  │ /review  │  │ /report  │  │ /layout  │  │ /concerns   │   │
│  │ (exists) │  │ (exists) │  │ (exists) │  │ (exists) │  │   (NEW v4)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘   │
│       │             │             │              │                │          │
│  ┌────┴─────────────────────────────────────────────────────────┴──────┐    │
│  │                          /compute (NEW v4)                           │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└───────┬─────────────────────────────────────────────────────────────────────┘
        │  reads/writes session state
        v
┌─────────────────────────────────────────────────────────────────────────────┐
│                        State Layer (app.storage.tab)                         │
│                                                                              │
│   vm_data (list[dict])   project_name   storage_model   llm_ui_enabled      │
│   layout_proposals (NEW v3 — list[dict])                                     │
└───────┬─────────────────────────────────────────────────────────────────────┘
        │  session row_data fed to
        v
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Pipeline / Services Layer                               │
│                                                                              │
│  pipeline/ingestion.py          ← MODIFIED: per-VM IOPS via LiveOptics       │
│  pipeline/classification.py     ← MODIFIED: new OS-fallback rules            │
│  pipeline/calculation.py        ← UNCHANGED                                  │
│  pipeline/layout_engine.py      ← UNCHANGED                                  │
│  pipeline/health_checks.py      ← NEW: analyze DataFrame → HealthFinding[]   │
│  pipeline/compute_sizing.py     ← NEW: vCPU/RAM → ComputeSizingResult        │
│                                                                              │
│  services/pdf_report.py         ← UNCHANGED (initially)                     │
│  services/excel_report.py       ← MODIFIED: add concerns + compute sheets   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `pipeline/ingestion.py` | Format detection, dispatch to parser | UNCHANGED |
| `pipeline/parsers/liveoptics.py` | Extract per-VM IOPS from VM Performance sheet | ALREADY DONE — peak_iops, avg_iops in CANONICAL_COLUMNS |
| `pipeline/classification.py` | Rules-based VM workload matching | MODIFIED: OS-fallback rules, more patterns |
| `pipeline/calculation.py` | Required capacity math, workload grouping | UNCHANGED |
| `pipeline/health_checks.py` | Scan DataFrame for data quality/risk flags | NEW |
| `pipeline/compute_sizing.py` | Host count recommendations from vCPU+RAM | NEW |
| `pipeline/layout_engine.py` | BFD datastore placement strategies | UNCHANGED |
| `ui/pages/review.py` | AG Grid with inline workload editor | MODIFIED: per-VM IOPS column, filter/group/search UX |
| `ui/components/vm_table.py` | AG Grid column definitions | MODIFIED: add iops columns, column visibility toggle |
| `ui/pages/concerns.py` | Health check findings display | NEW |
| `ui/pages/compute.py` | Compute sizing recommendations display | NEW |
| `ui/state.py` | Tab-scoped session storage helpers | MODIFIED: add compute_result storage |

---

## v4.0 Feature Integration Map

### Feature 1: Per-VM IOPS in the Grid

**Status of data extraction:** The per-VM IOPS fields (`peak_iops`, `avg_iops`, `iops_8k_equivalent`) are **already extracted** and in `CANONICAL_COLUMNS`. For LiveOptics xlsx, `parse_liveoptics_xlsx()` joins the VM Performance sheet per-VM. For RVTools, these columns default to `NaN` (no performance data in RVTools exports).

**What is missing:** The IOPS columns are NOT shown in the AG Grid. The `create_vm_table()` in `vm_table.py` shows only: `vm_name`, `workload_category`, `workload_subcategory`, `drr`, `provisioned_mib`, `classification_confidence`. IOPS data is only shown in the detail bar (below-grid click panel).

**Integration approach:** Add IOPS columns to the AG Grid column definitions. They should default to hidden (using `hide: True` in AG Grid columnDef) and be toggleable via column visibility controls.

**Files modified:**

```
ui/components/vm_table.py          MODIFIED: add peak_iops, avg_iops, iops_8k_equivalent columnDefs
                                             add columnDefs with hide:true by default
                                             add sidebar with columnsToolPanel for visibility toggle
review.py                          MODIFIED: pass has_performance_data flag to create_vm_table (already done)
                                             update detail bar: when column is visible, remove from detail bar
```

**New column definitions (to add to vm_table.py):**

```python
{
    "field": "peak_iops",
    "headerName": t("columns.peak_iops"),
    "sortable": True,
    "filter": "agNumberColumnFilter",
    "hide": True,                  # Hidden by default; toggled via sidebar
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
{
    "field": "avg_iops",
    "headerName": t("columns.avg_iops"),
    "sortable": True,
    "filter": "agNumberColumnFilter",
    "hide": True,
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
{
    "field": "iops_8k_equivalent",
    "headerName": t("columns.iops_8k_eq"),
    "sortable": True,
    "filter": "agNumberColumnFilter",
    "hide": True,
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : '—'",
},
```

**AG Grid sidebar for column visibility (add to grid_options):**

```python
"sideBar": {
    "toolPanels": [
        {
            "id": "columns",
            "labelDefault": "Columns",
            "labelKey": "columns",
            "iconKey": "columns",
            "toolPanel": "agColumnsToolPanel",
            "toolPanelParams": {
                "suppressRowGroups": True,
                "suppressValues": True,
                "suppressPivots": True,
                "suppressPivotMode": True,
            }
        }
    ]
},
```

**No pipeline changes required** — data is already in the session row_data dict.

---

### Feature 2: Grid UX Enhancements

**Integration approach:** All changes are within `vm_table.py` column definitions and `grid_options`. No pipeline changes.

**What to add to `create_vm_table()`:**

| Enhancement | AG Grid Config Change |
|-------------|----------------------|
| Column grouping by workload | `"rowGroupPanelShow": "always"` in grid_options |
| Quick search / filter bar | `"quickFilterText"` reactive binding via `ui.input` above grid |
| Column visibility toggle | `"sideBar"` with `agColumnsToolPanel` (see above) |
| Better bulk actions | No grid change — button label/icon polish in `review.py` |
| num_cpus + memory_mib columns | Add hidden columnDefs, visible via sidebar |

**Adding CPU + memory columns (already in row_data from RVTools):**

```python
{
    "field": "num_cpus",
    "headerName": t("columns.num_cpus"),
    "sortable": True,
    "filter": "agNumberColumnFilter",
    "hide": True,
},
{
    "field": "memory_mib",
    "headerName": t("columns.memory_mib"),
    "sortable": True,
    "filter": "agNumberColumnFilter",
    "hide": True,
    ":valueFormatter": "params => params.value != null ? Math.round(params.value).toLocaleString() : ''",
},
```

**Quick search implementation in `review.py`:**

```python
search_input = ui.input(
    placeholder=t("review.search_placeholder"),
    on_change=lambda e: grid.run_grid_method("setGridOption", "quickFilterText", e.value),
).classes("w-64")
```

**Files modified:**

```
ui/components/vm_table.py          MODIFIED: add sidebar, rowGroupPanelShow, new hidden columns
ui/pages/review.py                 MODIFIED: add search input above grid
```

**No pipeline changes required.**

---

### Feature 3: Classification Rule Improvements

**Integration approach:** Changes are entirely within `pipeline/classification.py`, specifically the `build_default_rules()` function. No UI or pipeline structure changes.

**What is needed:** OS-based fallback rules to reduce "Unknown (Reducible)" VMs. When VM name has no matches, fall back to OS field alone.

**Current classification flow:**

```python
def classify_vm(vm_name: str, os_name: str, description: str, registry: RuleRegistry) -> tuple[str, str, str, str]:
    for rule in registry.rules_by_priority:
        if rule.matches(vm_name, os_name, description):
            return rule.category, rule.subcategory, rule.name, "rule"
    return "Unknown (Reducible)", "Unknown (Reducible)", "default", "default"
```

**New rules to add (OS-based fallbacks, lower priority than existing rules):**

```python
# Priority 900+ — OS-only fallbacks (checked only when no name-based rule matched)
ClassificationRule(
    name="Windows Server OS fallback",
    category="Virtual Machines",
    subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
    priority=900,
    os_patterns=_regex_patterns(r"windows server", r"microsoft windows server"),
    match_mode="any",
),
ClassificationRule(
    name="Linux OS fallback",
    category="Virtual Machines",
    subcategory="VMware / Hyper-V / KVM - No Database, File nor Email",
    priority=901,
    os_patterns=_regex_patterns(r"red hat", r"centos", r"ubuntu", r"debian", r"suse", r"oracle linux"),
    match_mode="any",
),
```

**Files modified:**

```
pipeline/classification.py         MODIFIED: add OS-fallback rules to build_default_rules()
                                             review priority ordering with new rules
```

**Pipeline contract maintained:** `classify_dataframe()` signature and return columns are unchanged. Only new rules are added.

---

### Feature 4: Health Check / Concerns Page

**Integration approach:** New pure pipeline module + new UI page. Follows the same pattern as `layout_engine.py` — accepts `pd.DataFrame` or `list[dict]`, returns typed result objects, no UI imports.

**New module: `pipeline/health_checks.py`**

This module scans the session VM DataFrame for issues in three categories:

1. **Data quality flags:** VMs with zero provisioned storage, zero IOPS when IOPS expected, empty OS names, very high or very low DRR values
2. **Sizing risks:** Total required capacity near typical PowerStore limits, no performance data for layout sizing
3. **VMware best practice violations:** Oversized VMs (>32 vCPUs typical), VMs without cluster assignment, powered-off VMs included in sizing

**Data model:**

```python
# pipeline/health_checks.py

from dataclasses import dataclass
from enum import StrEnum

class Severity(StrEnum):
    ERROR = "error"      # Must fix — affects sizing validity
    WARNING = "warning"  # Should review — may affect accuracy
    INFO = "info"        # Advisory — best practice note

class CheckCategory(StrEnum):
    DATA_QUALITY = "data_quality"
    SIZING_RISK = "sizing_risk"
    BEST_PRACTICE = "best_practice"

@dataclass(frozen=True)
class HealthFinding:
    """A single finding from a health check."""
    check_id: str           # Stable identifier, e.g. "zero_provisioned_storage"
    severity: Severity
    category: CheckCategory
    title: str              # Short label for display
    detail: str             # Full explanation
    affected_vms: list[str] # VM names affected (empty for aggregate checks)
    count: int              # Number of affected items

@dataclass(frozen=True)
class HealthCheckResult:
    """All findings from running health checks on a dataset."""
    findings: list[HealthFinding]
    total_vms: int
    errors: int
    warnings: int
    infos: int

def run_health_checks(row_data: list[dict[str, Any]]) -> HealthCheckResult:
    """Run all health checks and return consolidated findings."""
    ...
```

**Health checks to implement:**

| Check ID | Severity | Description |
|----------|----------|-------------|
| `zero_provisioned_storage` | ERROR | VMs with provisioned_mib = 0 |
| `no_os_name` | WARNING | VMs with empty os_name |
| `unknown_workload` | WARNING | VMs still classified as Unknown (Reducible) |
| `no_performance_data` | INFO | All VMs lack IOPS data (RVTools source) |
| `powered_off_vms` | INFO | VMs with is_powered_on = False included in sizing |
| `oversized_vm_cpu` | WARNING | VMs with num_cpus > 32 |
| `oversized_vm_memory` | WARNING | VMs with memory_mib > 1,048,576 (1 TB) |
| `no_cluster_assignment` | INFO | VMs without cluster name (can't be placed in cluster) |
| `high_drr_custom` | WARNING | VMs with manually overridden DRR > 10 (unusually optimistic) |
| `very_low_drr` | INFO | VMs with DRR < 1.2 (near incompressible — expected for some workloads) |

**New UI page: `ui/pages/concerns.py`**

```python
@ui.page("/concerns")
async def concerns_page() -> None:
    """Health check findings for the current dataset."""
    df_records = load_session_data()
    if df_records is None:
        # redirect to upload
        ...

    result = run_health_checks(df_records.to_dict(orient="records"))

    with layout("StorePredict - Concerns"):
        # Summary badge row: N errors, N warnings, N infos
        # Findings list grouped by category with severity icons
        # Affected VMs shown as inline chip list (clickable to filter review grid)
```

**Route registration in `main.py`:**

```python
import store_predict.ui.pages.concerns  # noqa: F401
```

**Navigation integration:** Add "Concerns" link to `layout.py` nav bar after "Review" (or surface it as a badge count on the nav icon so user knows issues exist without visiting).

**Files added/modified:**

```
pipeline/health_checks.py          NEW: HealthFinding, HealthCheckResult, run_health_checks()
ui/pages/concerns.py               NEW: /concerns page
main.py                            MODIFIED: import concerns page to register route
ui/layout.py                       MODIFIED: add /concerns nav link
```

**State:** No new state required. Health checks are computed on-demand from existing session row_data. If the dataset changes (user edits workloads in review), concerns page recomputes on next visit.

---

### Feature 5: Compute Sizing Page

**Integration approach:** New pure pipeline module + new UI page. The vCPU and RAM data is **already extracted** by both parsers (see `CANONICAL_COLUMNS`: `num_cpus`, `memory_mib`) and is in `CalculationSummary.total_cpus`, `total_memory_mib`, `avg_vm_cpus`, `avg_vm_memory_mib`.

**New module: `pipeline/compute_sizing.py`**

This module takes aggregate compute totals and returns host count recommendations for different Dell server configurations.

**Data model:**

```python
# pipeline/compute_sizing.py

from dataclasses import dataclass

@dataclass(frozen=True)
class HostConfig:
    """A Dell server host configuration option."""
    model: str                  # e.g. "PowerEdge R760"
    sockets: int                # e.g. 2
    cores_per_socket: int       # e.g. 28
    total_vcpus: int            # sockets * cores_per_socket * ht_factor
    ram_gib: int                # e.g. 512

@dataclass(frozen=True)
class ClusterSizingResult:
    """Host count recommendation for one host config."""
    host_config: HostConfig
    host_count_cpu: int         # Hosts needed to satisfy vCPU demand
    host_count_ram: int         # Hosts needed to satisfy RAM demand
    recommended_host_count: int # max(cpu, ram) + HA spare
    with_ha_spare: int          # recommended + 1 for N+1 HA
    vmsc_host_count: int        # vMSC: 2x recommended (active/active stretched)
    ap_host_count: int          # Active/Passive: recommended + 1 site standby
    vcpu_utilization_pct: float # vCPU fill factor at recommended count
    ram_utilization_pct: float  # RAM fill factor at recommended count
    notes: str                  # Any notable conditions

@dataclass(frozen=True)
class ComputeSizingResult:
    """Full compute sizing output."""
    total_vcpus: int
    total_ram_gib: float
    avg_vcpus_per_vm: float
    avg_ram_gib_per_vm: float
    vm_count: int
    has_compute_data: bool      # False for LiveOptics imports lacking vCPU/RAM
    sizing_options: list[ClusterSizingResult]
    overcommit_ratio: float     # vCPU:pCPU ratio used (default 4:1)
    ram_overcommit_ratio: float # RAM ratio (default 1.0 — no RAM overcommit)

def compute_sizing(
    total_vcpus: int,
    total_memory_mib: float,
    vm_count: int,
    host_configs: list[HostConfig] | None = None,
    overcommit_ratio: float = 4.0,
    ha_n_plus: int = 1,
) -> ComputeSizingResult:
    """Calculate host count recommendations for given compute totals."""
    ...
```

**Default host configurations (shipped as `data/HOST_CONFIGS.csv` or hardcoded initial list):**

| Model | Sockets | Cores/Socket | HT | Total vCPUs | RAM GiB |
|-------|---------|-------------|-----|-------------|---------|
| PowerEdge R760 | 2 | 28 | 2x | 112 | 512 |
| PowerEdge R760 | 2 | 32 | 2x | 128 | 1024 |
| PowerEdge R860 | 4 | 28 | 2x | 224 | 1536 |
| PowerEdge R960 | 4 | 32 | 2x | 256 | 2048 |

**Sizing math:**

```
hosts_for_vcpu  = ceil(total_vcpus / (host_vcpus * overcommit_ratio))
hosts_for_ram   = ceil(total_ram_gib / (host_ram_gib * ram_overcommit_ratio))
raw_host_count  = max(hosts_for_vcpu, hosts_for_ram)
with_ha         = raw_host_count + ha_n_plus
vmsc_count      = with_ha * 2          # Two identical sites for vMSC
ap_count        = with_ha + ceil(with_ha / 2)  # Active + Passive standby site
```

**New UI page: `ui/pages/compute.py`**

```python
@ui.page("/compute")
async def compute_page() -> None:
    """Compute sizing recommendations from vCPU and RAM totals."""
    df = load_session_data()
    if df is None:
        # redirect to upload
        ...

    # Aggregate compute data from session
    summary = calculate(df.to_dict(orient="records"))
    result = compute_sizing(
        total_vcpus=summary.total_cpus,
        total_memory_mib=summary.total_memory_mib,
        vm_count=summary.total_vms,
    )

    with layout("StorePredict - Compute Sizing"):
        # Data availability notice if RVTools has no vCPU/RAM
        # Aggregate metrics: total vCPUs, total RAM, avg per VM
        # Host sizing table: one row per HostConfig, columns: hosts needed, with HA, vMSC, A/P
        # Overcommit ratio input (reactive — adjusts host counts on change)
        # HA N+ input (reactive)
        # Toggle: show vMSC configuration (doubled site count)
        # Toggle: show Active/Passive configuration
```

**State:** Compute results are computed on-demand from session data. No new state keys required. The `CalculationSummary.total_cpus` and `total_memory_mib` fields are already computed.

**Route registration:**

```python
# main.py
import store_predict.ui.pages.compute  # noqa: F401
```

**Navigation:** Add "Compute" link to `layout.py` nav bar.

**Files added/modified:**

```
pipeline/compute_sizing.py         NEW: HostConfig, ComputeSizingResult, compute_sizing()
ui/pages/compute.py                NEW: /compute page
main.py                            MODIFIED: import compute page to register route
ui/layout.py                       MODIFIED: add /compute nav link
```

---

## Updated System Architecture with v4.0 Features

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               UI Layer (NiceGUI)                                 │
│                                                                                  │
│  /upload    /review    /report    /layout    /concerns(NEW)    /compute(NEW)      │
│     │           │          │          │              │                │           │
│     │     AG Grid UX       │          │          HealthCheck      ComputeResult   │
│     │     (MODIFIED):      │          │          findings          display        │
│     │     + IOPS cols      │          │                                           │
│     │     + search bar     │          │                                           │
│     │     + col sidebar    │          │                                           │
└─────┼───────────┼──────────┼──────────┼──────────────┼────────────────┼──────────┘
      │           │          │          │              │                │
      ↓           ↓          ↓          ↓              ↓                ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         State Layer (app.storage.tab)                            │
│                                                                                  │
│   vm_data (list[dict])     project_name     storage_model     llm_ui_enabled     │
│   layout_proposals                                                               │
│   (no new state keys needed for v4.0 — compute and health run from vm_data)      │
└─────┬───────────────────────────────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Pipeline / Services Layer                                  │
│                                                                                  │
│  UNCHANGED:                          NEW for v4.0:                               │
│  pipeline/ingestion.py               pipeline/health_checks.py                   │
│  pipeline/parsers/liveoptics.py      pipeline/compute_sizing.py                   │
│  pipeline/calculation.py                                                          │
│  pipeline/layout_engine.py                                                        │
│                                                                                  │
│  MODIFIED for v4.0:                                                               │
│  pipeline/classification.py  ←── OS-fallback rules (900+ priority range)         │
│                                                                                  │
│  MODIFIED for v4.0 (optional, later):                                             │
│  services/excel_report.py    ←── add Concerns sheet + Compute sheet              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## New vs Modified Components

| Module | Status | Change Scope |
|--------|--------|--------------|
| `pipeline/health_checks.py` | NEW | HealthFinding, HealthCheckResult, run_health_checks() |
| `pipeline/compute_sizing.py` | NEW | HostConfig, ComputeSizingResult, compute_sizing() |
| `ui/pages/concerns.py` | NEW | /concerns page — health findings grouped by category |
| `ui/pages/compute.py` | NEW | /compute page — host count table with HA/vMSC/A-P toggles |
| `pipeline/classification.py` | MODIFIED | Add OS-fallback rules at priority 900+ in build_default_rules() |
| `ui/components/vm_table.py` | MODIFIED | Add IOPS + CPU + memory columnDefs (hidden by default), add sideBar, add rowGroupPanelShow |
| `ui/pages/review.py` | MODIFIED | Add search input above grid |
| `ui/layout.py` | MODIFIED | Add /concerns and /compute nav links |
| `main.py` | MODIFIED | Import concerns and compute pages to register routes |
| `services/excel_report.py` | MODIFIED (optional) | Add Concerns and Compute sheets |

**Unchanged:**

- `pipeline/ingestion.py` — per-VM IOPS already extracted in v3.0
- `pipeline/parsers/rvtools.py` — num_cpus and memory_mib already extracted
- `pipeline/parsers/liveoptics.py` — num_cpus, memory_mib, IOPS all already extracted
- `pipeline/calculation.py` — already sums total_cpus and total_memory_mib
- `pipeline/layout_engine.py`
- `pipeline/layout_models.py`
- `ui/pages/upload.py`
- `ui/pages/report.py`
- `ui/pages/layout_page.py`
- All `services/*.py` except excel_report.py (optional)

---

## Data Flows

### Per-VM IOPS in Grid Flow

```
File uploaded (LiveOptics xlsx)
    -> parse_liveoptics_xlsx() joins VM Performance sheet per-VM
    -> peak_iops, avg_iops, iops_8k_equivalent populated in CANONICAL_COLUMNS DataFrame
    -> classify_dataframe() adds workload columns
    -> save_session_data() serializes to app.storage.tab['vm_data']
    -> /review page loads row_data from session
    -> create_vm_table(row_data, ...) — row_data already contains iops fields
    -> AG Grid renders hidden IOPS columns
    -> User clicks "Columns" sidebar → shows/hides peak_iops, avg_iops, iops_8k_eq columns
```

For RVTools imports, the IOPS columns contain `null` (NaN serialized to None). The column formatter renders `null` as `—` to avoid blank cells looking broken.

### Health Check Flow

```
User navigates to /concerns
    -> concerns_page() calls load_session_data() -> row_data list[dict]
    -> run_health_checks(row_data) -> HealthCheckResult
    -> Findings rendered: severity icon + title + detail + affected VM count
    -> Click on finding -> links to /review with pre-applied filter
```

### Compute Sizing Flow

```
User navigates to /compute
    -> compute_page() calls load_session_data() -> df
    -> calculate(df.to_dict()) -> CalculationSummary (total_cpus, total_memory_mib)
    -> has_compute_data = summary.total_cpus > 0
    -> compute_sizing(total_vcpus, total_memory_mib, vm_count) -> ComputeSizingResult
    -> Table rendered: one row per HostConfig
    -> Overcommit ratio input: on_change -> recompute sizing -> update table
    -> vMSC toggle: show/hide vmsc_host_count column
    -> A/P toggle: show/hide ap_host_count column
```

---

## Recommended Build Order

Dependencies dictate this sequence:

### Phase 1: Grid UX + Per-VM IOPS Columns (no pipeline work)

**Rationale:** Entirely UI changes to `vm_table.py` and `review.py`. Zero pipeline risk. The IOPS data is already in row_data — it just needs to be surfaced. This delivers immediate user value (can see IOPS per VM) while being the lowest-risk change. AG Grid sidebar and search input are additive; no existing functionality is altered.

**Steps:**

1. Update `vm_table.py`: add hidden IOPS column defs, add `sideBar` with columns tool panel
2. Update `vm_table.py`: add hidden `num_cpus` and `memory_mib` column defs
3. Update `vm_table.py`: add `rowGroupPanelShow: "always"` for workload grouping
4. Update `review.py`: add quick search input above grid
5. Update i18n YAML with new column header keys

**Dependencies:** None — uses existing row_data.

---

### Phase 2: Classification Rule Improvements

**Rationale:** Pure pipeline change with no UI side effects. Adds OS-fallback rules to `classification.py`. Must be done before the health check phase, because health checks will flag "Unknown (Reducible)" VMs — reducing unknowns first makes the health check signal more actionable. No new dependencies.

**Steps:**

1. Audit current Unknown (Reducible) rates on test datasets
2. Add OS-pattern rules at priority 900+ (Windows Server, Linux distros, macOS, Solaris)
3. Add VM name pattern rules for commonly missed workloads (backup agents, monitoring VMs, etc.)
4. Run test suite — `classify_dataframe()` signature and output columns are unchanged
5. Update test fixtures if expected classifications change

**Dependencies:** None. Self-contained.

---

### Phase 3: Health Check Module + Concerns Page

**Rationale:** New pure pipeline module following the established `layout_engine.py` pattern. No changes to existing pipeline modules. The new `ui/pages/concerns.py` follows the same page structure as `layout_page.py`. Do this before compute sizing because health checks are simpler (no new math, just DataFrame scanning) and validate the new-page pattern.

**Steps:**

1. Create `pipeline/health_checks.py` with `HealthFinding`, `HealthCheckResult`, `run_health_checks()`
2. Implement 10 health check functions (see check table above)
3. Write tests: one test per check function, verify finding severity and affected_vms
4. Create `ui/pages/concerns.py` with findings display
5. Register route in `main.py`
6. Add /concerns nav link to `layout.py`
7. Add i18n keys for all finding titles and detail strings

**Dependencies:** Phase 2 (so Unknown classifications are already reduced before health checks flag them).

---

### Phase 4: Compute Sizing Module + Page

**Rationale:** New pure pipeline module + new UI page. The data (`total_cpus`, `total_memory_mib`) already exists in `CalculationSummary`. The compute math is straightforward but has the most user-facing complexity (toggles, overcommit ratio inputs, reactive table). Build last of the four features so the simpler patterns (health checks, grid UX) have already been validated.

**Steps:**

1. Create `pipeline/compute_sizing.py` with `HostConfig`, `ComputeSizingResult`, `compute_sizing()`
2. Hardcode initial host config list (4 PowerEdge configs)
3. Write tests: verify host count math at various vCPU/RAM totals
4. Create `ui/pages/compute.py` with host sizing table
5. Add overcommit ratio input with reactive recompute
6. Add vMSC and Active/Passive column toggles
7. Register route in `main.py`
8. Add /compute nav link to `layout.py`
9. Add i18n keys for all UI strings

**Dependencies:** Phase 1 (nav patterns validated), Phase 3 (page structure pattern established).

---

## Component Boundary Rules (maintained from prior milestones)

| Rule | Why |
|------|-----|
| `pipeline/` never imports from `ui/` | Keeps pipeline testable without NiceGUI |
| `health_checks.py` accepts `list[dict]` not `pd.DataFrame` | Consistent with `calculate()` pattern; JSON-serializable input |
| `compute_sizing.py` accepts scalar totals not a DataFrame | Decouples from session format; easier to test |
| New pages call `calculate()` rather than accessing totals directly | Reuses existing aggregation logic; single source of truth |
| Health findings do not reference session state | Pipeline is stateless; findings are computed fresh on each page visit |
| Compute page does not persist results to session | Results are deterministic from vm_data; recomputing is cheaper than cache invalidation |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adding logic to the UI page that belongs in the pipeline

**What goes wrong:** `concerns.py` iterates the row_data and builds finding strings inline.
**Why wrong:** Untestable without NiceGUI; duplicates logic if Excel export also needs findings.
**Do this instead:** `run_health_checks()` in `pipeline/health_checks.py`; `concerns.py` only renders `HealthFinding` objects.

### Anti-Pattern 2: Adding IOPS columns as always-visible

**What goes wrong:** IOPS columns are added to the AG Grid without `hide: True`.
**Why wrong:** The grid becomes unreadably wide for RVTools imports where IOPS is all `—`. Users who don't have LiveOptics data see a broken-looking table.
**Do this instead:** Default `hide: True` on all new columns. User enables via sidebar. The `has_performance_data` flag can pre-show IOPS columns when data is present.

### Anti-Pattern 3: Compute sizing that bypasses `calculate()`

**What goes wrong:** `compute.py` reads `vm_data` from session and sums `num_cpus` itself.
**Why wrong:** `calculate()` already does this aggregation into `CalculationSummary.total_cpus`; duplicating the logic creates a divergence bug when DRR or workload changes.
**Do this instead:** Call `calculate(load_session_data().to_dict(orient="records"))` in the compute page, then pass `summary.total_cpus` and `summary.total_memory_mib` to `compute_sizing()`.

### Anti-Pattern 4: Health checks as blocking pipeline step

**What goes wrong:** `run_health_checks()` is called in `upload.py` after classification and its results stored in session.
**Why wrong:** Health check results go stale when the user edits workloads in the review grid. They should always reflect the current state of the data.
**Do this instead:** Run health checks on-demand when the user visits `/concerns`. No caching in session.

### Anti-Pattern 5: Nav links without route guards

**What goes wrong:** Nav links to `/concerns` and `/compute` appear even before a file is uploaded.
**Why wrong:** Clicking them before upload shows an error/empty state, which is confusing.
**Do this instead:** Nav links to data-dependent pages (`/review`, `/report`, `/layout`, `/concerns`, `/compute`) should check `load_session_data() is not None` and redirect to `/upload` if no data — the same guard already in `review.py`.

---

## Integration Points Summary

| Feature | New Files | Modified Files | Pipeline Changes |
|---------|-----------|----------------|-----------------|
| Per-VM IOPS in grid | none | `vm_table.py` | none (data already present) |
| Grid UX enhancements | none | `vm_table.py`, `review.py` | none |
| Classification improvements | none | `classification.py` | rules-only, signature unchanged |
| Health checks | `health_checks.py`, `concerns.py` | `main.py`, `layout.py` | new pure module |
| Compute sizing | `compute_sizing.py`, `compute.py` | `main.py`, `layout.py` | new pure module |

---

## Sources

- Verified against source: `src/store_predict/pipeline/parsers/columns.py` — CANONICAL_COLUMNS includes num_cpus, memory_mib, peak_iops, avg_iops (HIGH confidence)
- Verified against source: `src/store_predict/pipeline/calculation.py` — CalculationSummary.total_cpus and total_memory_mib already computed (HIGH confidence)
- Verified against source: `src/store_predict/pipeline/parsers/rvtools.py` and `liveoptics.py` — num_cpus, memory_mib extracted from both formats (HIGH confidence)
- Verified against source: `src/store_predict/ui/components/vm_table.py` — IOPS columns not in grid columnDefs (HIGH confidence)
- AG Grid Community v34 sidebar API: sideBar with agColumnsToolPanel is standard Community feature (HIGH confidence — used in v3.0 layout_page.py with AG Grid v34)
- NiceGUI `grid.run_grid_method("setGridOption", "quickFilterText", ...)` is the documented way to set reactive grid options from Python (MEDIUM confidence — verified against NiceGUI AG Grid docs pattern)

---

*Architecture research for: StorePredict v4.0 — compute sizing, health checks, per-VM IOPS, grid UX, classification improvements*
*Researched: 2026-02-22*
