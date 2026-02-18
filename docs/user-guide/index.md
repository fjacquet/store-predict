# User Guide

## Overview

StorePredict helps pre-sales engineers size PowerStore arrays by analyzing VMware workload exports and predicting Data Reduction Ratios (DRR).

## Workflow

```mermaid
graph LR
    A[Upload File] --> B[Review Classifications]
    B --> C[Generate Report]
    C --> D[Download PDF]
```

### 1. Upload

Upload an RVTools (.xlsx) or LiveOptics (.xlsx/.csv) export file. StorePredict auto-detects the format and extracts VM information.

**Supported formats:**

| Format | Extension | Source |
|--------|-----------|--------|
| RVTools | .xlsx | vInfo tab |
| LiveOptics | .xlsx | VMs tab |
| LiveOptics | .csv | VMs export |

### 2. Review Classifications

Each VM is automatically classified into a workload category (Database, VDI, Virtual Machines, etc.) with an associated DRR. You can:

- Review auto-detected workload types
- Override workload classification per VM
- Assign multiple workload types (lowest/most conservative DRR applies)
- Sort and filter the VM table

### 3. Generate Report

View sizing summary with:

- Total VMs, total provisioned capacity
- Weighted average DRR
- Required capacity after data reduction
- Breakdown by workload category

### 4. Download PDF

Export a one-page PDF sizing report suitable for customer presentations.

## DRR Categories

The Data Reduction Ratio depends on workload type. Common examples:

| Workload | DRR | Effect |
|----------|-----|--------|
| Database (SQL, Oracle) | 5:1 | High compression |
| VDI Full Clone | 8:1 | Very high dedup |
| VDI Linked Clone | 1:1 | Already deduped |
| Virtual Machines (general) | 5:1 | Standard |
| Unknown (Reducible) | 5:1 | Conservative default |

See `samples/DRR.csv` for the complete reference table.
