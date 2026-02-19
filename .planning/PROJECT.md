# StorePredict

## What This Is

A web-based tool for pre-sales engineers that analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv) to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays. It classifies VMs by workload category, applies the appropriate DRR coefficient, parses LiveOptics performance data (IOPS, throughput), and generates a one-page PDF sizing report with capacity and performance metrics for customer proposals.

## Core Value

Accurately predict real-world PowerStore DRR per workload instead of relying on vendor marketing ratios, so pre-sales engineers can deliver honest, defensible sizing to customers.

## Requirements

### Validated

- Import RVTools .xlsx files (vInfo tab) — v1.0
- Import LiveOptics .xlsx/.csv files (VMs tab + VM Performance) — v1.0
- Auto-classify VMs by workload category using 29 rules-based patterns — v1.0
- DRR lookup table with 28 workload categories from DRR.csv — v1.0
- Editable AG Grid table with inline workload dropdown and bulk update — v1.0
- Multi-select workload types with conservative (lowest) DRR — v1.0
- Editable DRR column for custom overrides — v1.0
- Calculate required PowerStore capacity with Totals/Averages sections — v1.0
- LiveOptics performance sizing: Peak IOPS, 8K Eq. IOPS, throughput — v1.0
- One-page PDF report with VM statistics, performance summary, workload breakdown — v1.0
- Docker Compose deployment with health check and env-var secrets — v1.0
- MkDocs documentation with GitHub Actions deployment — v1.0
- GitHub Actions CI (ruff, mypy, pytest) — v1.0
- 145 tests passing, file validation, log sanitization — v1.0

### Active

(None — planning next milestone)

### Out of Scope

- ML-based classification — rules-based covers 100% of sample VMs, ML deferred
- Multi-page detailed PDF report — one-page synthesis sufficient for pre-sales
- Co-branding (Dell partner logos) — neutral StorePredict branding
- SIOKit (.siokit) binary format — focus on xlsx/csv exports
- PowerStore model recommendation — capacity-only sizing in v1
- Real-time data collection — tool works with exported files only
- User authentication — internal tool, single-user sessions
- Data persistence between sessions — in-memory per tab

## Context

Shipped v1.0 with 2,840 LOC Python (30 modules) + 2,097 LOC tests.
Tech stack: NiceGUI 3.7.1, pandas, openpyxl, ReportLab, AG Grid 34.2.0.
Docker Compose deployment, MkDocs on GitHub Pages, GitHub Actions CI.
UAT: 9/10 tests passed, 1 skipped (description-based classification fallback).

## Constraints

- **Tech stack:** NiceGUI + Tailwind CSS (full Python)
- **Data processing:** pandas + openpyxl
- **PDF generation:** ReportLab Platypus with Vera fonts
- **Deployment:** Docker Compose, single container, port 8080
- **Documentation:** MkDocs with Material theme + Mermaid diagrams
- **Code quality:** ruff + mypy strict + pytest (145 tests)
- **CI/CD:** GitHub Actions (lint, test, docs deploy)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Python (NiceGUI) over React+FastAPI | Single language, simpler deployment, native Tailwind | Good |
| NiceGUI over Streamlit | More UI control, AG Grid integration, Tailwind support | Good |
| Rules-based classification first | 29 rules cover 100% of sample VMs, no ML training data needed | Good |
| Conservative DRR for multi-workload VMs | Pre-sales needs defensible numbers | Good |
| Docker Compose deployment | Simple, fits internal tool usage | Good |
| AG Grid with `:` prefix for JS functions | NiceGUI convention, required for getRowId/valueFormatter | Good |
| NaN → None (not empty string) | Prevents downstream float("") errors in JSON chain | Good |
| 8K IOPS = throughput/8 only | Avoids double-counting with avg_iops | Good |
| Hottest VM peak, not sum of peaks | Sum of peaks is statistically meaningless | Good |
| Editable DRR column | Pre-sales needs custom overrides for edge cases | Good |
| Totals/Averages report layout | Clearer grouping for pre-sales readability | Good |

---
*Last updated: 2026-02-19 after v1.0 milestone*
