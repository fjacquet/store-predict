# Requirements — StorePredict v1.0

## Functional Requirements

### FR-1: File Ingestion
- **FR-1.1:** Accept RVTools .xlsx uploads — parse vInfo tab, extract columns: VM, Powerstate, Template, OS according to the VMware Tools, Provisioned MB, In Use MB, Datacenter, Cluster
- **FR-1.2:** Accept LiveOptics .xlsx uploads — parse VMs tab, extract columns: VM Name, VM OS, Guest VM Disk Capacity (MiB), Guest VM Disk Used (MiB), Virtual Disk Size (MiB)
- **FR-1.3:** Accept LiveOptics .csv uploads — same columns as VMs tab
- **FR-1.4:** Auto-detect file format (RVTools vs LiveOptics) based on sheet names and column headers
- **FR-1.5:** Normalize data into a common DataFrame format: vm_name, os_name, provisioned_mib, in_use_mib, datacenter, cluster, source_format
- **FR-1.6:** Filter out template VMs (RVTools Template="True")
- **FR-1.7:** Handle column name variations with fuzzy matching (aliases for known column names)
- **FR-1.8:** Show clear error message if file format is unrecognized or required columns are missing

### FR-2: DRR Reference Table
- **FR-2.1:** Load DRR reference data from semicolon-delimited CSV file (samples/DRR.csv)
- **FR-2.2:** Handle CSV parsing edge cases: embedded newlines, trailing empty rows, missing values
- **FR-2.3:** Provide 30 workload categories with ratios from 1 to 8
- **FR-2.4:** Default unclassified VMs to "Unknown (Reducible)" with DRR = 5

### FR-3: Workload Classification
- **FR-3.1:** Auto-classify each VM by matching VM name and OS field against pattern rules
- **FR-3.2:** Classification rules ordered by priority: Database > Application > Infrastructure > OS fallback > Default
- **FR-3.3:** Use substring matching (not word boundary) — "CADSRVSQL001" must match "SQL"
- **FR-3.4:** Display classification confidence indicator (matched rule name)

### FR-4: User Review & Override
- **FR-4.1:** Display classified VMs in an editable data table (AG Grid) with columns: VM Name, OS, Detected Workload, DRR, Provisioned, In Use
- **FR-4.2:** Allow user to change workload type via dropdown (single-select from DRR categories)
- **FR-4.3:** Support multi-select workload types per VM via edit dialog (e.g., SQL + File Server)
- **FR-4.4:** When multiple workloads selected, use the lowest (most conservative) DRR
- **FR-4.5:** Table supports sorting, filtering, pagination (50-100 rows per page)
- **FR-4.6:** Show summary statistics updated in real-time as user edits

### FR-5: Capacity Calculation
- **FR-5.1:** Calculate per-VM required capacity: `required_mib = provisioned_mib / drr`
- **FR-5.2:** Calculate totals: total_provisioned, total_in_use, total_required, weighted_average_drr
- **FR-5.3:** Group results by workload category with subtotals
- **FR-5.4:** Display results in summary cards and breakdown table

### FR-6: PDF Report Export
- **FR-6.1:** Generate one-page PDF with StorePredict branding
- **FR-6.2:** Include: project name, date, total VMs, total provisioned, weighted avg DRR, required capacity
- **FR-6.3:** Include workload breakdown table: Category, VM count, Provisioned, DRR, Required
- **FR-6.4:** Support French characters (accents, special chars) in VM names and text
- **FR-6.5:** Download triggered from the report page

### FR-7: User Interface
- **FR-7.1:** Three-page flow: Upload → Review → Report
- **FR-7.2:** NiceGUI with Tailwind CSS styling
- **FR-7.3:** Navigation between pages (stepper or tabs)
- **FR-7.4:** Project name input field (used in PDF header)
- **FR-7.5:** Responsive layout (works on laptop screens)

## Non-Functional Requirements

### NFR-1: Deployment
- **NFR-1.1:** Docker Compose deployment — single container
- **NFR-1.2:** App serves on port 8080 by default
- **NFR-1.3:** No external database required — all state in-memory per session

### NFR-2: Code Quality
- **NFR-2.1:** Python 3.12+, typed with mypy strict mode
- **NFR-2.2:** Linting with ruff, formatting with ruff format
- **NFR-2.3:** pytest with >80% coverage on pipeline/ and services/
- **NFR-2.4:** Pipeline package has zero imports from UI package

### NFR-3: Documentation
- **NFR-3.1:** MkDocs documentation site
- **NFR-3.2:** GitHub Actions deployment to GitHub Pages
- **NFR-3.3:** Diagrams in Mermaid format (not ASCII art)

### NFR-4: Performance
- **NFR-4.1:** Handle xlsx files with up to 5000 VMs without timeout
- **NFR-4.2:** PDF generation under 5 seconds

### NFR-5: Security
- **NFR-5.1:** Validate uploaded file type (xlsx/csv only)
- **NFR-5.2:** Never log DataFrame contents (VM names, IPs are customer-confidential)
- **NFR-5.3:** Per-session data isolation (no cross-user data leakage)

## Out of Scope (v1)
- ML-based classification (v2)
- Multi-page detailed PDF report (v2)
- Co-branding / custom logos (v2)
- SIOKit binary format
- PowerStore model recommendation
- Real-time data collection
- User authentication
- Data persistence between sessions
