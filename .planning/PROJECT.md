# StorePredict

## What This Is

A web-based tool for pre-sales engineers that analyzes VMware workload exports (RVTools .xlsx, LiveOptics .xlsx/.csv) to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays. It classifies VMs by workload type, applies the appropriate DRR coefficient, and generates a one-page PDF sizing report for customer proposals.

## Core Value

Accurately predict real-world PowerStore DRR per workload instead of relying on vendor marketing ratios, so pre-sales engineers can deliver honest, defensible sizing to customers.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Import RVTools .xlsx files (vInfo tab: VM Name, OS, Provisioned/Used storage)
- [ ] Import LiveOptics .xlsx files (VMs tab: VM Name, VM OS, disk sizes)
- [ ] Import LiveOptics .csv files
- [ ] Auto-classify VMs by workload category using rules-based pattern matching (VM Name + OS field)
- [ ] DRR lookup table matching workload categories to reduction ratios (from DRR.csv reference data)
- [ ] Editable validation form — table where user can override detected workload type per VM
- [ ] Multi-select workload types per VM (e.g., SQL + File Server on same VM)
- [ ] Conservative DRR calculation for multi-workload VMs (use lowest ratio among selected types)
- [ ] Calculate required PowerStore capacity: Provisioned / DRR pondéré
- [ ] One-page PDF report with StorePredict branding (total capacity, DRR moyen, required capacity, top workloads)
- [ ] Docker Compose deployment (single container, NiceGUI app)
- [ ] MkDocs documentation hosted via GitHub Pages (GitHub Actions)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ML-based classification — deferred to v2, rules-based sufficient for v1
- Multi-page detailed PDF report — v1 is synthesis one-pager, detail in v2
- Co-branding (Dell partner logos) — v1 uses neutral StorePredict branding
- SIOKit (.siokit) binary format — focus on xlsx/csv exports from LiveOptics
- PowerStore model recommendation — v1 calculates capacity only, not specific model sizing
- Real-time data collection — tool works with exported files only

## Context

- **Source data formats:**
  - RVTools: .xlsx with vInfo tab containing VM Name, OS according to VMware Tools, Provisioned MiB, In Use MiB
  - LiveOptics: .xlsx with VMs tab (VM Name, VM OS, Virtual Disk Size, Guest VM Disk Capacity/Used), VM Performance tab (IOPS, throughput), also available as .csv
  - LiveOptics ZIP exports contain multiple .xlsx files (VMWARE, GENERAL, AIR, PERF)
- **DRR reference table:** 30 workload categories with ratios from 1 (incompressible: encrypted, compressed, PACS) to 8 (VDI full clone). Default "Unknown (Reducible)" = 5.
- **Classification signals:** VM Name patterns (SQL, Oracle, VDI, SAP, Exchange, etc.), OS field (Windows Server vs Desktop), Guest Hostname patterns
- **Sample data available:** `samples/DRR.csv`, `samples/live-optics.xlsx`, `samples/CIGES-IT_02_16_2026.zip`
- **Frontend reference:** Raidy project at `/Users/fjacquet/Projects/raidy` uses React/TS/Tailwind — StorePredict uses same design philosophy but full Python stack

## Constraints

- **Tech stack (frontend):** NiceGUI with Tailwind CSS — full Python, native Tailwind support
- **Tech stack (backend):** Python with FastAPI patterns (NiceGUI handles both UI and API)
- **Data processing:** openpyxl/pandas for xlsx parsing
- **PDF generation:** Python library (ReportLab or WeasyPrint)
- **Deployment:** Docker Compose, single container
- **Documentation:** MkDocs with GitHub Actions for GitHub Pages
- **Code quality:** Biome-equivalent Python tooling (ruff, mypy)
- **Testing:** pytest with good coverage
- **CI/CD:** GitHub Actions (lint, test, build, docs deploy)

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Python (NiceGUI) over React+FastAPI | Single language to maintain, simpler deployment, Tailwind CSS support native | — Pending |
| NiceGUI over Streamlit | Tailwind CSS support, more UI control, same Python simplicity | — Pending |
| Rules-based classification first, ML in v2 | Faster to ship, pattern matching covers 80%+ of cases, ML needs labeled data | — Pending |
| Conservative DRR for multi-workload VMs | Pre-sales needs defensible numbers — better to under-promise than over-promise | — Pending |
| Docker Compose deployment | Self-hosted, simple, fits internal tool usage pattern | — Pending |

---
*Last updated: 2026-02-18 after initialization*
