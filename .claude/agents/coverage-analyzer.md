# Coverage Analyzer Agent

Analyze test coverage for StorePredict and identify untested code paths.

## Target

Project requires >80% coverage on `pipeline/` and `services/` (NFR-2.3).

## Process

1. Run: `rtk pytest --cov=store_predict --cov-report=term-missing --tb=no -q`
2. Parse the coverage output
3. Identify files below 80% coverage
4. For each under-covered file, identify the specific uncovered lines/functions

## Output Format

| Module | Coverage | Target | Status |
|--------|----------|--------|--------|
| pipeline/ingestion.py | 92% | 80% | Pass |
| services/drr_table.py | 75% | 80% | **FAIL** |

### Gaps

For each failing module, list:
- **File**: path
- **Missing lines**: line ranges
- **What's untested**: description of the code paths (error handling, edge cases, etc.)
- **Suggested tests**: brief description of tests to add

### Summary

- Overall coverage: X%
- Modules below target: N
- Priority: List top 3 modules to add tests for
