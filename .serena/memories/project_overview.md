# StorePredict — Project Overview

## Purpose
Full-Python web tool for Dell pre-sales engineers. Analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv) to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays. Users upload a file, review auto-classified VMs, adjust workload types, and export a one-page PDF sizing report.

## Tech Stack
- **Language:** Python 3.14
- **UI:** NiceGUI with Tailwind CSS
- **Data:** pandas, openpyxl
- **PDF:** ReportLab (Platypus, Vera TTF fonts)
- **Testing:** pytest (no unittest.mock — real objects only)
- **Linting:** ruff, mypy
- **Package manager:** uv
- **Deployment:** Docker Compose (single container)
- **Docs:** MkDocs with GitHub Pages

## Architecture (3-stage pipeline)
1. **Ingestion** — Parse uploaded file, detect format, extract VM list with storage metrics
2. **Classification** — Match VMs to workload categories using rules-based pattern matching
3. **Calculation** — Apply DRR coefficients, compute Required Capacity = Provisioned / DRR

## Codebase Structure
```
src/store_predict/
├── main.py                     # NiceGUI app entry point
├── config.py                   # Config constants (DRR_CSV_PATH)
├── pipeline/
│   ├── models.py               # Data models (VM, FileFormat, WorkloadCategory)
│   ├── errors.py               # IngestionError
│   ├── ingestion.py            # Format detection + orchestration
│   ├── classification.py       # ClassificationRule, RuleRegistry, classify_dataframe
│   ├── calculation.py          # VMCalculation, CalculationSummary, calculate()
│   └── parsers/
│       ├── columns.py          # Column alias resolution
│       ├── rvtools.py          # RVTools .xlsx parser
│       └── liveoptics.py       # LiveOptics .xlsx/.csv parser
├── services/
│   ├── drr_table.py            # DRR reference CSV loader
│   └── pdf_report.py           # PDF report generator (ReportLab)
└── ui/
    ├── layout.py               # Shared layout context manager (nav bar)
    ├── state.py                # Session state (app.storage.tab/user)
    ├── pages/
    │   ├── upload.py           # /upload — file dropzone + pipeline
    │   ├── review.py           # /review — AG Grid + workload dialog
    │   └── report.py           # /report — summary + PDF download
    └── components/
        ├── vm_table.py         # AG Grid VM table
        ├── workload_dialog.py  # Multi-select workload dialog
        ├── summary_stats.py    # Summary statistics cards
        └── dark_mode_toggle.py # Dark/light mode toggle
tests/                          # pytest tests (106 total)
samples/                        # DRR.csv + sample data files
.planning/                      # GSD planning docs
docs/                           # MkDocs documentation
```

## Key Design Decisions
- Pipeline modules have zero UI imports (clean separation)
- DRR table loaded from CSV (not hardcoded)
- Multi-workload VMs use lowest (most conservative) DRR
- DRR=0 guarded with max(drr, 0.1)
- Session data: app.storage.tab (per-tab), app.storage.user (preferences)
- Page routes registered via module import side-effect
