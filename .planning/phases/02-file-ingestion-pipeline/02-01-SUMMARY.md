---
phase: 02-file-ingestion-pipeline
plan: 01
subsystem: ingestion
tags: [pandas, openpyxl, rvtools, liveoptics, parser, xlsx, csv]

requires:
  - phase: 01-project-foundation
    provides: "FileFormat enum, VMRecord dataclass, project config"
provides:
  - "parse_rvtools function for RVTools xlsx files"
  - "parse_liveoptics_xlsx function for LiveOptics xlsx files"
  - "parse_liveoptics_csv function for LiveOptics csv files"
  - "resolve_columns alias resolution utility"
  - "IngestionError custom exception"
  - "CANONICAL_COLUMNS schema definition"
affects: [02-02, 03-classification-engine]

tech-stack:
  added: [openpyxl]
  patterns: [column-alias-resolution, canonical-schema-normalization]

key-files:
  created:
    - src/store_predict/pipeline/errors.py
    - src/store_predict/pipeline/parsers/__init__.py
    - src/store_predict/pipeline/parsers/columns.py
    - src/store_predict/pipeline/parsers/rvtools.py
    - src/store_predict/pipeline/parsers/liveoptics.py
  modified: []

key-decisions:
  - "Column alias resolution via dict lookup, not regex pattern matching"
  - "Shared _build_liveoptics_df helper to avoid code duplication between xlsx and csv parsers"
  - "pandas import kept at runtime (not TYPE_CHECKING) in parser modules since DataFrame is constructed"
  - "columns.py uses TYPE_CHECKING for pandas since it only appears in type annotations"

patterns-established:
  - "Canonical schema: all parsers output identical 9-column DataFrames"
  - "Column resolution: resolve_columns(df, aliases, required) pattern for format normalization"
  - "IngestionError with user-facing message + developer details for all parse failures"

duration: 5min
completed: 2026-02-18
---

# Phase 02 Plan 01: Core Parsers Summary

**RVTools and LiveOptics parsers with column alias resolution producing canonical 9-column DataFrames**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-18T19:54:32Z
- **Completed:** 2026-02-18T19:59:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Column alias resolution infrastructure handles known column name variations across RVTools and LiveOptics formats
- parse_rvtools reads vInfo sheet, produces 24-row canonical DataFrame from sample
- parse_liveoptics_xlsx reads VMs sheet, produces 610-row canonical DataFrame from sample
- parse_liveoptics_csv with UTF-8/Latin-1 encoding fallback
- Template NaN pitfall handled (fillna(False).astype(bool))
- IngestionError with user-facing message and developer details

## Task Commits

Each task was committed atomically:

1. **Task 1: Column resolution infrastructure and IngestionError** - `645a6fc` (feat)
2. **Task 2: RVTools and LiveOptics parsers** - `f0fd9c7` (feat)

## Files Created/Modified
- `src/store_predict/pipeline/errors.py` - IngestionError custom exception
- `src/store_predict/pipeline/parsers/__init__.py` - Package with re-exports
- `src/store_predict/pipeline/parsers/columns.py` - CANONICAL_COLUMNS, alias maps, resolve_columns
- `src/store_predict/pipeline/parsers/rvtools.py` - parse_rvtools for RVTools xlsx
- `src/store_predict/pipeline/parsers/liveoptics.py` - parse_liveoptics_xlsx and parse_liveoptics_csv

## Decisions Made
- Column alias resolution uses dict lookup (first match wins) rather than regex -- simpler and sufficient for known formats
- Shared _build_liveoptics_df helper avoids duplicating DataFrame construction between xlsx and csv parsers
- pandas kept as runtime import in parser modules (constructs DataFrames), but moved to TYPE_CHECKING in columns.py (annotation only)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three parser functions importable from store_predict.pipeline.parsers
- Canonical schema verified with real sample data (24 RVTools VMs, 610 LiveOptics VMs)
- Ready for 02-02 (format detection/orchestrator) and 03 (classification engine)

---
*Phase: 02-file-ingestion-pipeline*
*Completed: 2026-02-18*
