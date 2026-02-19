---
phase: 03-workload-classification-engine
plan: 01
subsystem: classification
tags: [regex, pattern-matching, pandas, dataclass, drr]

# Dependency graph
requires:
  - phase: 02-file-ingestion-pipeline
    provides: "DataFrame with vm_name, os_name columns from ingest_file()"
  - phase: 01-project-foundation
    provides: "DRRTable service with category/subcategory lookup"
provides:
  - "ClassificationRule dataclass for defining pattern-matching rules"
  - "ClassificationResult dataclass for classification output"
  - "RuleRegistry with priority-ordered first-match-wins evaluation"
  - "build_default_rules() returning 29 rules covering all 28 DRR subcategories"
  - "classify_dataframe() for bulk DataFrame classification"
affects: [04-user-review-ui, 05-calculation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns: [priority-ordered-rule-registry, frozen-dataclass-rules, compiled-regex-patterns]

key-files:
  created:
    - src/store_predict/pipeline/classification.py
    - tests/test_classification.py
  modified: []

key-decisions:
  - "Reordered PostgreSQL/MySQL rules before Microsoft SQL to prevent PGSQL matching SQL pattern"
  - "Used word boundary regex for SAP to avoid GISAPP false positive"
  - "Included CIT pattern for Citrix (26 genuine Citrix VMs in sample data)"
  - "Default Citrix to Full Clone / MCS (DRR=8, optimistic); user can override"
  - "Default Web Servers to Content included (DRR=5, conservative)"

patterns-established:
  - "Rule priority tiers: 100-199 Database, 200-299 App, 300-399 Infra, 400-499 Logging, 900-949 OS fallback, 999 Default"
  - "Specific-before-generic: rules with substring overlap (PGSQL contains SQL) get lower priority numbers"
  - "NaN os_name handling: explicit pd.notna() check before str() conversion"

# Metrics
duration: 7min
completed: 2026-02-18
---

# Phase 3 Plan 1: Workload Classification Engine Summary

**Priority-ordered rule registry with 29 classification rules covering all 28 DRR subcategories, substring matching on VM name/OS, and false positive prevention for ORA/EX/SAP patterns**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-18T20:56:35Z
- **Completed:** 2026-02-18T21:03:35Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Classification engine with ClassificationRule, ClassificationResult, RuleRegistry classes
- 29 default rules covering all 28 DRR subcategories from DRR.csv
- classify_dataframe() adds 4 classification columns to ingestion DataFrame
- 28 unit tests covering pattern matching, priority ordering, false positives, OS fallback, case insensitivity, and DataFrame integration
- Every rule's category/subcategory verified against real DRR.csv via test

## Task Commits

Each task was committed atomically:

1. **Task 1: Create classification engine module** - `ce9e128` (feat)
2. **Task 2: Create unit tests for classification rules** - `13434df` (test)

## Files Created/Modified
- `src/store_predict/pipeline/classification.py` - Classification engine: rules, registry, DataFrame classifier
- `tests/test_classification.py` - 28 unit tests for classification rules and integration

## Decisions Made
- Reordered PostgreSQL (priority 102) and MySQL (priority 101) before Microsoft SQL (priority 103) because PGSQL and MYSQL contain "SQL" substring -- without reordering, these would incorrectly match the generic SQL rule
- Used `\bSAP\b` word boundary regex plus "SAP-" and "SAP_" literal patterns to prevent "GISAPP" false positive while still matching "SAP-APP-01"
- Included "CIT" as Citrix pattern per research recommendation (26 genuinely Citrix VMs in sample)
- OS fallback confidence mapped to priority range 900-998, distinct from rule_match (<900) and default (999)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed priority ordering for PostgreSQL/MySQL vs Microsoft SQL**
- **Found during:** Task 2 (test_postgresql_match failing)
- **Issue:** PGSQL-PRIMARY matched Microsoft SQL rule (priority 101) before PostgreSQL (priority 105) because "PGSQL" contains "SQL"
- **Fix:** Moved PostgreSQL to priority 102 and MySQL to priority 101, before Microsoft SQL at priority 103
- **Files modified:** src/store_predict/pipeline/classification.py
- **Verification:** test_postgresql_match passes; PGSQL correctly classifies as PostgreSQL
- **Committed in:** 13434df (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness -- without it, PostgreSQL VMs would be misclassified as Microsoft SQL. No scope creep.

## Issues Encountered
None beyond the priority ordering fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Classification engine ready for integration with ingestion pipeline
- classify_dataframe() accepts DataFrame from ingest_file() directly
- Phase 4 (user review UI) can use classification results for display and override
- 71 total tests passing (43 existing + 28 new)

---
*Phase: 03-workload-classification-engine*
*Completed: 2026-02-18*
