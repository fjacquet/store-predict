# Milestones — StorePredict

## v1.0 — MVP Sizing Tool

**Shipped:** 2026-02-19
**Phases:** 1-7 (22 plans)
**Source:** 2,840 LOC (30 modules) + 2,097 LOC tests (145 passing)

### Key Accomplishments

1. Full ingestion pipeline — Parses RVTools .xlsx, LiveOptics .xlsx/.csv with auto-detection and column alias resolution
2. Rules-based classification engine — 29 priority-ordered rules, 0% unknown rate on 594 real VMs
3. Interactive review UI — AG Grid with inline editing, bulk workload update, filtered selection, editable DRR
4. One-page PDF sizing report — ReportLab with Totals/Averages/Performance sections, French character support
5. LiveOptics performance sizing — Peak IOPS, 8K equivalent IOPS, throughput metrics with correct normalization
6. Production-ready deployment — Docker Compose, GitHub Actions CI/CD, MkDocs documentation

### Known Gaps

- No milestone audit performed (UAT passed 9/10 tests, 1 skipped)
- Company name prefix stripping not fully implemented (classification still works via substring matching)

### Archives

- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
