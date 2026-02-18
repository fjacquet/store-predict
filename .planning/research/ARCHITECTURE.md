# Architecture Research — StorePredict

**Domain:** Data processing web tool (file upload, classify, calculate, export PDF)

## High-Level Data Flow

```
User Browser
    |
    v
NiceGUI UI Layer (pages, components, event handlers)
    |
    v
Session Controller (per-user state, orchestrates pipeline)
    |
    +---> Ingestion Service (parse RVTools/LiveOptics)
    |         |
    |         v
    |     Raw DataFrame
    |
    +---> Classification Engine (rules registry, pattern matching)
    |         |
    |         v
    |     Classified DataFrame (with workload_category column)
    |
    +---> Calculation Service (apply DRR, compute required capacity)
    |         |
    |         v
    |     Results DataFrame + summary metrics
    |
    +---> PDF Export Service (render one-page report)
              |
              v
          PDF bytes -> download
```

## Recommended Project Structure

```
store-predict/
  src/
    store_predict/
      __init__.py
      main.py                    # Entry point: ui.run(), app config
      config.py                  # Settings (paths, defaults)

      # --- UI Layer ---
      ui/
        __init__.py
        pages/
          __init__.py
          upload.py              # File upload page
          review.py              # VM classification review/edit table
          report.py              # Results summary + PDF download
        components/
          __init__.py
          vm_table.py            # Editable AG Grid table component
          workload_selector.py   # Multi-select workload dropdown
          summary_card.py        # Capacity summary card
          file_dropzone.py       # Upload dropzone with format detection
        layout.py                # Shared layout (header, nav, footer)

      # --- Business Logic (no UI imports) ---
      pipeline/
        __init__.py
        ingestion.py             # File parsing: RVTools, LiveOptics xlsx/csv
        classification.py        # Rules engine + pattern matching
        calculation.py           # DRR application, capacity math
        models.py                # Data classes / TypedDicts for pipeline data

      # --- Services ---
      services/
        __init__.py
        drr_table.py             # Load/cache DRR reference data from CSV
        pdf_export.py            # PDF generation (ReportLab)
        session.py               # Per-session state management

      # --- Reference Data ---
      data/
        drr_default.csv          # Default DRR table (shipped with app)

  tests/
    __init__.py
    conftest.py                  # Shared fixtures (sample DataFrames, temp files)
    test_ingestion.py
    test_classification.py
    test_calculation.py
    test_drr_table.py
    test_pdf_export.py
    test_pipeline_integration.py
    fixtures/
      rvtools_sample.xlsx
      liveoptics_sample.xlsx
      liveoptics_sample.csv

  samples/                       # Real customer data (gitignored additions)
  docs/                          # MkDocs source
  Dockerfile
  docker-compose.yml
  pyproject.toml
  CLAUDE.md
```

**Critical boundary:** `pipeline/` has zero imports from `ui/`. The entire data pipeline is testable without NiceGUI and enables future headless/batch mode.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `ui/pages/` | Render pages, handle user events | `services/session.py`, `ui/components/` |
| `ui/components/` | Reusable UI widgets | Pages (parent), session state |
| `pipeline/ingestion` | Parse xlsx/csv to normalized DataFrame | Called by session controller |
| `pipeline/classification` | Apply rules to classify VMs | Called by session controller, uses `drr_table` |
| `pipeline/calculation` | Apply DRR coefficients, compute capacity | Called by session controller |
| `services/drr_table` | Load, cache, serve DRR reference data | Used by classification + calculation |
| `services/pdf_export` | Generate PDF from results | Called by report page |
| `services/session` | Per-user state (uploaded data, classifications, overrides) | Used by all pages |

## Key Patterns

### Pattern 1: Pipeline as Pure Functions

Each pipeline stage is a pure function: DataFrame in, DataFrame out. No side effects, no UI coupling.

```python
# pipeline/ingestion.py
def detect_format(file_path: Path) -> FileFormat: ...
def parse_rvtools(file_path: Path) -> pd.DataFrame: ...
def parse_liveoptics_xlsx(file_path: Path) -> pd.DataFrame: ...
def ingest(file_path: Path) -> pd.DataFrame:
    fmt = detect_format(file_path)
    parsers = {FileFormat.RVTOOLS: parse_rvtools, ...}
    return parsers[fmt](file_path)
```

### Pattern 2: Rule Registry for Classification

Ordered list of `ClassificationRule` dataclasses with `matches(vm_name, os_name) -> bool`. Rules evaluated in priority order; first match wins.

```python
@dataclass
class ClassificationRule:
    name: str
    category: str
    subcategory: str
    vm_name_patterns: list[re.Pattern]
    os_patterns: list[re.Pattern]
    match_mode: str = "any"  # "any" = vm_name OR os, "all" = both required
    priority: int = 100      # Lower = higher priority
```

### Pattern 3: Per-Session State via Server-Side Dict

DataFrames aren't serializable into NiceGUI's storage. Keep them in a server-side dict keyed by session UUID.

```python
@dataclass
class SessionState:
    file_name: str = ""
    raw_df: pd.DataFrame | None = None
    classified_df: pd.DataFrame | None = None
    user_overrides: dict[str, list[str]] = field(default_factory=dict)
    results_df: pd.DataFrame | None = None

_sessions: dict[str, SessionState] = {}
```

### Pattern 4: DRR Table as Injectable Service

```python
class DRRTable:
    @classmethod
    def from_csv(cls, path: Path) -> "DRRTable": ...
    def get_ratio(self, category: str, subcategory: str) -> float: ...
    def get_conservative_ratio(self, workloads: list[tuple[str, str]]) -> float:
        return min(self.get_ratio(c, s) for c, s in workloads) if workloads else 5.0
```

### Pattern 5: NiceGUI Page Routing

```python
@ui.page("/")
def index():
    with layout("Upload"):
        upload.render()

@ui.page("/review")
def review_page():
    with layout("Review"):
        review.render()

@ui.page("/report")
def report_page():
    with layout("Report"):
        report.render()
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Instead |
|-------------|---------|---------|
| Business logic in UI event handlers | Untestable, can't reuse for batch mode | UI calls pipeline functions |
| Global mutable DataFrames | Multi-user race conditions | Per-session state dict |
| Hardcoded DRR values | Unmaintainable, values change | DRRTable service from CSV |
| Monolithic main.py | Unmanageable past 200 lines | Structured pages/pipeline modules |

## Data Flow Stages

1. **Ingestion** → Normalized DataFrame: vm_name, os_name, provisioned_mib, in_use_mib, source_format
2. **Classification** → DataFrame + workload_category, workload_subcategory, drr_ratio, classification_rule
3. **User Review** → Editable AG Grid, user overrides applied
4. **Calculation** → required = provisioned / drr (conservative min for multi-workload). Summary metrics.
5. **PDF Export** → One-page PDF with branding, summary, workload breakdown table

## Docker Architecture

Single container. NiceGUI uses uvicorn internally — no reverse proxy needed for v1.

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - STORAGE_SECRET=change-me
    restart: unless-stopped
```

## Testing Strategy

| Type | What | Priority |
|------|------|----------|
| Unit | Each classification rule, format detection, DRR calculations, edge cases | HIGH |
| Integration | Full pipeline with sample files, override flow, PDF generation | HIGH |
| UI | Manual testing of 3 pages — no automated UI tests in v1 | LOW |

## Scalability (v1 = small team, in-process everything)

In-process dict for sessions, synchronous processing, synchronous PDF — all correct for an internal tool used by 1-5 people. Do not over-engineer.
