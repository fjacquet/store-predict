# Architecture Decision Records

ADRs document key technical decisions made during StorePredict development.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-nicegui-framework.md) | Use NiceGUI for web framework | Accepted | 2026-02-18 |
| [002](002-drr-csv-reference.md) | DRR ratios from CSV, not hardcoded | Accepted | 2026-02-18 |
| [003](003-alias-not-fuzzy-matching.md) | Column alias dictionaries, not fuzzy matching | Accepted | 2026-02-18 |
| [004](004-dataframe-not-dataclass.md) | DataFrame as pipeline data format, not dataclass | Accepted | 2026-02-18 |
| [005](005-conservative-drr.md) | Most conservative DRR for multi-workload VMs | Accepted | 2026-02-18 |
| [006](006-no-mocks-testing.md) | Real objects and sample data for tests, no mocks | Accepted | 2026-02-18 |
| [007](007-aggrid-vm-table.md) | AG Grid for VM review table | Accepted | 2026-02-18 |
| [008](008-session-storage-split.md) | Tab storage for data, user storage for preferences | Accepted | 2026-02-18 |
| [009](009-dialog-multi-workload.md) | Dialog for multi-workload assignment | Accepted | 2026-02-18 |
| [010](010-nicegui-3x.md) | Target NiceGUI 3.x, not 2.x | Accepted | 2026-02-19 |
| [011](011-substring-matching.md) | Substring matching for VM classification | Accepted | 2026-02-19 |
| [012](012-priority-ordered-rules.md) | Priority-ordered rule registry with first-match-wins | Accepted | 2026-02-19 |
| [013](013-weighted-average-drr.md) | Weighted average DRR, not simple mean | Accepted | 2026-02-19 |
| [014](014-drr-guard.md) | DRR guard with max(drr, 0.1) | Accepted | 2026-02-19 |
| [015](015-canonical-dataframe-schema.md) | Canonical DataFrame schema (9 columns) | Accepted | 2026-02-19 |
| [016](016-template-filter-orchestrator.md) | Template VM filtering at orchestrator level | Accepted | 2026-02-19 |
| [017](017-rvtools-mb-as-mib.md) | RVTools "MB" values treated as MiB, no conversion | Accepted | 2026-02-19 |
| [018](018-openpyxl-read-only-detection.md) | openpyxl read_only mode for format detection | Accepted | 2026-02-19 |
| [019](019-shared-liveoptics-helper.md) | Shared _build_liveoptics_df helper (DRY) | Accepted | 2026-02-19 |
| [020](020-dark-mode-user-storage.md) | Dark mode in app.storage.user (per-user) | Accepted | 2026-02-19 |
| [021](021-dual-workload-edit.md) | Dual workload edit mechanism (dropdown + dialog) | Accepted | 2026-02-19 |
| [022](022-stats-clear-rebuild.md) | Stats container clear-and-rebuild pattern | Accepted | 2026-02-19 |
| [023](023-page-routes-side-effects.md) | Page routes via module import side-effects | Accepted | 2026-02-19 |
| [024](024-workload-dialog-props.md) | WorkloadDialog persistent + use-chips props | Accepted | 2026-02-19 |
| [025](025-reportlab-platypus.md) | PDF with ReportLab Platypus, not WeasyPrint | Accepted | 2026-02-19 |
| [026](026-vera-ttf-fonts.md) | Vera TTF fonts for French characters | Accepted | 2026-02-19 |
| [027](027-pdf-in-memory-bytesio.md) | PDF in-memory via BytesIO, no temp files | Accepted | 2026-02-19 |
| [028](028-ui-table-report-page.md) | ui.table for report page, not AG Grid | Accepted | 2026-02-19 |
| [029](029-three-layer-architecture.md) | Three-layer architecture (pipeline → services → ui) | Accepted | 2026-02-19 |
| [030](030-docker-single-container.md) | Docker Compose single-container deployment | Accepted | 2026-02-19 |
| [031](031-magic-byte-validation.md) | Server-side file validation with magic bytes | Accepted | 2026-02-19 |
| [032](032-log-sanitization.md) | Log sanitization — never log DataFrame contents | Accepted | 2026-02-19 |
| [033](033-context-manager-layout.md) | Context manager for shared layout | Accepted | 2026-02-19 |
| [034](034-sap-word-boundary.md) | SAP word boundary pattern (exception to substring matching) | Accepted | 2026-02-19 |
| [035](035-postgres-mysql-before-sql.md) | PostgreSQL/MySQL rules before generic SQL | Accepted | 2026-02-19 |
| [036](036-citrix-full-clone-default.md) | Citrix VMs default to Full Clone (DRR=8) | Accepted | 2026-02-19 |
| [037](037-fortinet-os-field-detection.md) | FortiNet detection via OS field | Accepted | 2026-02-19 |
| [038](038-mkdocs-material.md) | MkDocs with Material theme for documentation | Accepted | 2026-02-19 |
| [039](039-uv-package-manager.md) | uv for Python package management | Accepted | 2026-02-19 |
| [040](040-pyproject-single-config.md) | pyproject.toml as single configuration file | Accepted | 2026-02-19 |
| [041](041-strict-mypy-type-checking.md) | Strict mypy with TYPE_CHECKING guards | Accepted | 2026-02-19 |
| [042](042-web-server-content-included-default.md) | Web servers default to content included (DRR=5) | Accepted | 2026-02-19 |
| [043](043-i18n-architecture-t-wrapper-yaml.md) | i18n architecture — per-call locale via t() wrapper with YAML files | Accepted | 2026-02-20 |
| [044](044-language-switch-page-reload.md) | Language switch via full page reload | Accepted | 2026-02-20 |
| [045](045-echart-for-web-charts.md) | ECharts (NiceGUI ui.echart) for interactive web charts | Accepted | 2026-02-20 |
| [046](046-pdf-charts-page-two.md) | PDF charts on a dedicated second page | Accepted | 2026-02-20 |
| [047](047-sankey-reportlab-strategy.md) | Sankey diagram strategy for PDF (ReportLab constraint) | Proposed | 2026-02-20 |
