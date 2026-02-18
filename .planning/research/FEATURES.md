# Features Research — StorePredict

**Confidence:** HIGH (verified against actual sample files)

## LiveOptics .xlsx Structure (Verified)

**Source:** `samples/live-optics.xlsx` — 11 sheets, 610 VMs in sample

### VMs Tab (Primary — 38 columns)

Key columns for ingestion:

- **VM Name** (col B) — e.g., "3000-GPO-TEST", "CADSRVSQL001", "ANSIBLE-01-T"
- **VM OS** (col F) — e.g., "Microsoft Windows Server 2019 (64-bit)", "Oracle Linux 9 (64-bit)"
- **Guest VM Disk Capacity (MiB)** (col P) — total guest-visible disk
- **Guest VM Disk Used (MiB)** (col Q) — actual used space
- **Virtual Disk Size (MiB)** (col S) — provisioned virtual disk size
- **Virtual Disk Used (MiB)** (col T) — used virtual disk space
- **IsRunning** (col D) — "TRUE"/"FALSE"
- **Power State** (col E) — "poweredOn"/"poweredOff"
- **Datacenter** (col Y), **Cluster** (col AA)

### VM Performance Tab (35 columns — Phase 3 enrichment)

- Peak/Avg IOPS, KB/sec, read/write latency
- VM IO Classification (Standard/High/etc.)
- Useful for future ML classification enhancement

### Other Tabs Available

- ESX Hosts, ESX Performance, Host Devices, VM Disks, Custom Attributes, ESX Licenses, Host Disks, Host Network Adapters

## RVTools .xlsx Structure (Verified from samples/rvtools.xlsx)

### vInfo Tab (71 columns — verified)

Key columns for ingestion:

- **VM** (col A) — VM display name (NOT "VM Name")
- **Powerstate** (col B) — "poweredOn"/"poweredOff"
- **Template** (col C) — "True"/"False" (filter out templates)
- **OS according to the VMware Tools** (col 65) — guest OS string
- **OS according to the configuration file** (col 64) — configured OS
- **Provisioned MB** (col 37) — total provisioned storage (NOT MiB)
- **In Use MB** (col 38) — actual used storage (NOT MiB)
- **Datacenter** (col 61), **Cluster** (col 62), **Host** (col 63)

**Confirmed differences from LiveOptics:**

- Column "VM" not "VM Name"
- Units are "MB" not "MiB"
- OS column is "OS according to the VMware Tools" (verbose)
- 25 sheets total (vInfo, vCPU, vMemory, vDisk, vPartition, etc.)
- German/localized paths observed in sample ("Erkannte virtuelle Maschinen")

## DRR.csv Parsing (Verified — 4 Issues Found)

**Source:** `samples/DRR.csv` — semicolon-delimited, 30 workload categories

Issues discovered:

1. **Embedded newline** in line 7-8: PostgreSQL entry has a line break in the "Application/Use case" field
2. **Trailing empty rows** after the data
3. **Stray entry** on line 35 (partial/empty data)
4. **No header row** explicitly marked — first row is data, needs manual column names

**Parsing strategy:**

```python
df = pd.read_csv(path, sep=';', names=['category', 'subcategory', 'ratio'],
                 skiprows=1, quoting=csv.QUOTE_ALL)
df = df.dropna(subset=['category'])
df['ratio'] = pd.to_numeric(df['ratio'], errors='coerce')
df = df.dropna(subset=['ratio'])
```

## Classification Patterns (Verified from 610 real VMs)

### VM Naming Conventions Observed

- **SITE-FUNCTION-NUM:** `CADSRVSQL001`, `ARBAZ-AADC`, `OIK_CADSRVSQL002`
- **Descriptive:** `Backup-VeeamOne`, `3000-prj-Mfiles`
- **Product names:** `ANSIBLE-01-T`, `ZABBIX-02-P`
- **Site prefixes:** `ARCHIAD-DC1`, `CIGES-WSUS`

### Key Classification Insight

**Embedded keywords** are common — "CADSRVSQL001" contains "SQL" without word boundaries. Pattern matching must use substring search, not whole-word:

```python
# ✅ Correct: substring match
re.compile(r"(?i)SQL")  # matches "CADSRVSQL001"

# ❌ Wrong: word boundary match
re.compile(r"(?i)\bSQL\b")  # misses "CADSRVSQL001"
```

### Classification Rule Priority (from DRR.csv categories)

1. **Database keywords** (highest priority): SQL, MSSQL, Oracle, ORA, PostgreSQL, MySQL, SAP, HANA, MongoDB
2. **Application keywords**: Exchange, SharePoint, Citrix, VDI, Desktop, Veeam, Backup
3. **Infrastructure keywords**: DC, AADC (Active Directory), DNS, DHCP, WSUS
4. **OS-based fallback**: Windows Server → Virtual Machines, Linux → Virtual Machines
5. **Default**: Unknown (Reducible), DRR = 5

## Editable VM Table (NiceGUI AG Grid)

### AG Grid Community in NiceGUI

- `ui.aggrid()` wraps AG Grid Community edition
- Supports: sorting, filtering, pagination, inline cell editing
- Column definitions with `editable: True` for cell-level editing

### Multi-Select Workload Pattern

AG Grid Community doesn't natively support multi-select dropdowns in cells. Recommended approach:

1. **Primary column:** Single-select dropdown showing detected workload
2. **Action button:** "Edit" button per row opens a `ui.dialog()` with `ui.select(multiple=True)`
3. **Display:** Multi-select values shown as comma-separated in the cell

```python
# Single-select dropdown in AG Grid
column_defs = [
    {'field': 'vm_name', 'headerName': 'VM Name'},
    {'field': 'os_name', 'headerName': 'OS'},
    {'field': 'workload', 'headerName': 'Workload', 'editable': True,
     'cellEditor': 'agSelectCellEditor',
     'cellEditorParams': {'values': workload_categories}},
    {'field': 'drr', 'headerName': 'DRR'},
]
```

### Multi-Select Dialog Pattern

```python
async def edit_workloads(vm_name: str, current_workloads: list[str]):
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Workloads for {vm_name}')
        select = ui.select(options=all_workloads, multiple=True, value=current_workloads)
        ui.button('Save', on_click=lambda: dialog.submit(select.value))
    result = await dialog
    # Update session state with multi-select result
```

## PDF Report Layout (One Page)

### Recommended Structure

```
+--------------------------------------------------+
|  [StorePredict Logo]     Sizing Report            |
|  Project: {project_name}    Date: {date}          |
+--------------------------------------------------+
|  SUMMARY                                          |
|  Total VMs: {count}                               |
|  Total Provisioned: {X} TiB                       |
|  Weighted Avg DRR: {Y}:1                          |
|  Required Capacity: {Z} TiB                       |
+--------------------------------------------------+
|  WORKLOAD BREAKDOWN                               |
|  Category          | VMs | Prov.  | DRR | Req.   |
|  Database/SQL      |  12 | 2.4 TB | 5:1 | 0.5 TB |
|  Virtual Machines  |  45 | 8.1 TB | 5:1 | 1.6 TB |
|  VDI Full Clone    |   8 | 1.2 TB | 8:1 | 0.2 TB |
|  ...               |     |        |     |        |
+--------------------------------------------------+
|  Generated by StorePredict v1.0                   |
+--------------------------------------------------+
```

### ReportLab Implementation

- Use `SimpleDocTemplate` with A4/Letter page size
- `Table` + `TableStyle` for workload breakdown
- Register Unicode font (DejaVu Sans) for French characters
- Include summary metrics as `Paragraph` elements with custom styles

## Roadmap Implications

1. **DRR.csv parsing first** — feeds classification engine and validation dropdown values
2. **LiveOptics ingestion before RVTools** — have verified sample data for LiveOptics; RVTools needs a real sample
3. **Single-select workload in v1** — covers most cases; multi-select adds dialog complexity
4. **VM Performance integration deferred** — nice-to-have, not sizing-critical

## Open Questions

- RVTools vInfo column names need verification against an actual .xlsx export
- NiceGUI `ui.upload()` max file size behavior with 50MB+ files needs testing
- Whether LiveOptics CSV exports use same column names as .xlsx VMs tab
