# Technical Research

Research documents produced during project development. Each document captures domain analysis, technology decisions, and findings from investigating sample data.

## Phase Research

| Phase | Topic | Key Findings |
|-------|-------|-------------|
| [Phase 1](phase-01-foundation.md) | Project Foundation | Python stack, NiceGUI, DRR.csv parsing quirks |
| [Phase 2](phase-02-ingestion.md) | File Ingestion | RVTools "MB" = MiB, Template NaN pitfall, column aliases |
| [Phase 3](phase-03-classification.md) | Workload Classification | 28 DRR categories, false positive patterns (ORA/SAP/EX), OS fallback strategy |
| [Phase 4](phase-04-ui.md) | UI Upload & Review Pages | AG Grid table, session storage split, multi-workload dialog, dark mode |
| [Phase 5](phase-05-calculation.md) | Calculation & PDF Report | ReportLab Platypus, Vera fonts, weighted avg DRR, BytesIO PDF |
| [Phase 6](phase-06-polish.md) | Polish, Docs & Deployment | Docker hardening, file validation, CI/CD, MkDocs, performance tests |

## Sample Data Analysis

- **RVTools sample:** 24 VMs, 70 columns in vInfo tab
- **LiveOptics sample:** 610 VMs, 38 columns in VMs tab
- **DRR reference:** 28 valid categories, semicolon-delimited CSV with parsing quirks

## Key Technical Findings

### RVTools "MB" values are MiB

Despite column headers saying "MB", RVTools uses base-2 (MiB) values. No unit conversion needed between RVTools and LiveOptics formats.

### VM Naming Conventions

Corporate VM names embed functional keywords: `CADSRVSQL001` (SQL), `CITADM-01` (Citrix), `CIGES-FAZ` (FortiAnalyzer). Classification relies on substring matching against these patterns.

### False Positive Patterns

- "ORA" matches LORADB (LoRa radio protocol database) — use "ORACLE" instead
- "SAP" matches GISAPP (GIS application server) — use word-boundary match
- "EX" matches EXTRANET — use "EXCHANGE" instead
- "ABAC" is Swiss Abacus ERP, not SAP ABAP
