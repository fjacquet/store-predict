# Changelog

All notable changes to StorePredict are documented here.

## [Unreleased]

### Phase 4: UI — Upload & Review Pages (COMPLETE)

- Session state module for per-tab DataFrame serialization (`ui/state.py`)
- Upload page with file dropzone, project name input, pipeline integration
- AG Grid VM table component with inline workload dropdown (ADR-007)
- Multi-select workload dialog for assigning multiple workload types (ADR-009)
- Summary statistics cards (Total VMs, Provisioned, Avg DRR, Effective Capacity)
- Review page wiring all components: table, dialog, stats, DRR recalculation
- Dark mode toggle with persistent user preference via `app.storage.user` (ADR-008)
- Navigation header with Home, Upload, and Review links
- Cell change handler: inline workload dropdown updates DRR and stats
- Row click handler: multi-select dialog applies conservative (lowest) DRR
- Per-tab session isolation for upload data, per-user storage for preferences (ADR-008)

### Phase 3: Workload Classification Engine

- Classification engine with 29 priority-ordered rules covering all 28 DRR subcategories
- ClassificationRule dataclass with pattern matching on VM name and OS field
- RuleRegistry with first-match-wins evaluation and confidence tracking
- Substring matching (CADSRVSQL001 -> SQL) with false positive prevention
- OS-based fallback rules (Windows Server -> Virtual Machines)
- classify_dataframe() for bulk DataFrame classification
- 0% Unknown rate on 594 real LiveOptics VMs (target was <20%)
- 28 unit tests + 11 integration tests with real sample data

### Phase 2: File Ingestion Pipeline

- RVTools .xlsx parser (vInfo tab)
- LiveOptics .xlsx and .csv parsers (VMs tab)
- Format auto-detection based on sheet names and column headers
- Column alias resolution for name variations
- Template VM filtering
- Unified ingest_file() orchestrator
- 29 ingestion tests with real sample files

### Phase 1: Project Foundation & DRR Table

- Python project structure with src layout
- DRR table service loading 28 workload categories from CSV
- Data models (VM, FileFormat, WorkloadCategory)
- NiceGUI app skeleton with page routing
- ruff + mypy configuration
- pytest setup with 14 initial tests
- Dockerfile + docker-compose.yml
