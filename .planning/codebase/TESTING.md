# Testing Patterns

**Analysis Date:** 2026-02-23

## Test Framework

**Runner:**
- pytest 8.0+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
- Test paths: `tests/`
- Default coverage: `--cov=store_predict --cov-report=term-missing --cov-report=xml`

**Coverage:**
- Omitted from coverage: `src/store_predict/ui/*`, `src/store_predict/main.py`, `src/store_predict/logging_config.py`
- View coverage: `rtk pytest --cov=store_predict`
- Target: Not explicitly enforced, but 158+ tests across pipeline, classification, calculation, PDF, i18n, validation, performance, log sanitization

**Run Commands:**
```bash
rtk pytest                          # Run all tests
rtk pytest tests/test_classifier.py -k "test_sql_detection"  # Single test
rtk pytest --cov=store_predict      # With coverage report
```

## Test File Organization

**Location:**
- Tests co-located with source in dedicated `tests/` directory
- Fixtures in `tests/fixtures/` (CSV/XLSX test data)
- Shared fixtures in `tests/conftest.py`

**Naming:**
- File pattern: `test_<module>.py` (e.g., `test_classification.py`, `test_calculation.py`)
- Test function pattern: `test_<behavior>()` with no parameters
- Test class pattern: `Test<Feature>` with grouped related tests (e.g., `TestRuleMatching`, `TestMultipleVMs`, `TestEdgeCases`)

**Structure:**
```
tests/
├── conftest.py                    # Shared pytest fixtures
├── fixtures/                      # Test data files (CSV, XLSX)
│   ├── liveoptics_sample.csv
│   └── ...
├── test_classification.py         # Classification engine tests
├── test_calculation.py            # Calculation service tests
├── test_health_checks.py          # Health check engine tests
├── test_pdf_report.py             # PDF generation tests
├── test_ingestion.py              # File parsing & format detection
└── ... (29 test files, 158+ tests)
```

## Test Structure

**Suite Organization:**
```python
from __future__ import annotations

import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)

class TestRuleMatching:
    """Individual pattern matching tests."""

    def test_sql_substring_match(self) -> None:
        """FR-3.3: CADSRVSQL001 must match SQL rule via substring."""
        result = _registry().classify("CADSRVSQL001", "Microsoft Windows Server 2019 (64-bit)")
        assert result.category == "Database"
        assert result.subcategory == "Microsoft SQL"
        assert result.confidence == "rule_match"

    def test_oracle_match(self) -> None:
        result = _registry().classify("ORACLE-PROD-01", "")
        assert result.category == "Database"
        assert result.subcategory == "Oracle"
```

**Patterns:**
- No setup/teardown for most tests — use real objects and fixtures
- Module-level helper functions (prefixed with `_`) build test data
- Class-scoped tests use `self` but have no `setup_method()` — state is immutable
- Type hints on all test functions: `def test_name(self) -> None:`

## Mocking

**Framework:** NOT USED

**Philosophy:**
- Tests use real objects only, no `unittest.mock`
- Test with actual implementations to catch integration bugs
- Use fixtures to provide preconfigured real objects

**What to Mock:**
- Nothing in unit tests — if you want to mock, it's an integration test or design issue
- File paths in fixtures allow testing real file I/O with sample data

**What NOT to Mock:**
- Classification rules, DRR tables, calculators — test with real rules
- DataFrame operations — test with real pandas
- File parsers — test with real fixture files

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def drr_table(sample_drr_path: Path) -> DRRTable:
    """DRRTable loaded from the real DRR.csv."""
    return DRRTable.from_csv(sample_drr_path)

@pytest.fixture
def make_summary() -> Callable[[], CalculationSummary]:
    """Factory fixture that returns a callable producing a minimal CalculationSummary.

    Returns a zero-argument factory so tests can call ``make_summary()`` to
    get a fresh CalculationSummary with realistic data.
    """
    def _factory() -> CalculationSummary:
        vm_calcs = [
            VMCalculation(
                vm_name=f"VM-{i}",
                workload_category="Database/Microsoft SQL",
                provisioned_mib=10240.0,
                in_use_mib=5120.0,
                drr=5.0,
                required_mib=2048.0,
            )
            for i in range(3)
        ]
        # ... build complete summary
        return CalculationSummary(...)
    return _factory
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Module-specific fixtures: top of test file or in conftest with scope
- Factory helpers: module-level `_<name>()` functions that return test data

**Sample files:**
- `tests/fixtures/liveoptics_sample.csv` — CSV test data
- `samples/rvtools.xlsx`, `samples/live-optics.xlsx` — Real customer data (optional, skipped if missing)

## Coverage

**Requirements:** Not explicitly enforced in CI

**Actual coverage:**
- 158+ tests across all major components
- Omitted: UI pages, main.py, logging_config.py
- Core pipeline fully tested: classification, calculation, ingestion, health checks

**View Coverage:**
```bash
rtk pytest --cov=store_predict
```

## Test Types

**Unit Tests (majority):**
- Single function/class in isolation
- Use fixtures for dependencies
- Example: `test_sql_substring_match()` tests classification rule matching only
- Run in < 1 second typically

**Integration Tests:**
- Multiple components working together
- Example: `test_detect_format()` and `test_rvtools_column_count()` test ingestion pipeline
- Example: `test_pdf_generates_bytes()` tests PDF generation with real ReportLab
- Run in < 5 seconds typically

**E2E Tests:**
- Not explicitly defined, but some tests exercise full pipeline
- Example: `test_calculate()` in calculation tests

**Fixture-based tests:**
- Tests that skip if fixture data unavailable: `pytest.skip("samples/rvtools.xlsx not available")`
- Allows CI to run without customer sample files

## Common Patterns

**Assertion Patterns:**
```python
# Simple assertions
assert result.total_vms == 1
assert len(result.vm_calculations) == 1

# Float comparisons (floating-point tolerance)
assert vm.required_mib == pytest.approx(2000.0)
assert result.weighted_avg_drr == pytest.approx(2.5)

# Substring matches in errors
with pytest.raises(IngestionError, match="Unsupported file type"):
    detect_format(unsupported_file)

# Collection membership
assert result.category == "Database"
assert "SQL" in result.subcategory
```

**Async Testing:**
Not applicable — store-predict is synchronous Python

**Error Testing:**
```python
def test_detect_unsupported_extension(self, tmp_path: Path) -> None:
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("some content")
    with pytest.raises(IngestionError, match="Unsupported file type"):
        detect_format(txt_file)

def test_csv_binary_content_rejected(self) -> None:
    content = b"\xFF\xFE\x00\x00" + b"\x00" * 100
    with pytest.raises(IngestionError, match="valid CSV"):
        validate_upload(content, "broken.csv")
```

**Edge Case Testing:**
```python
def test_none_input_returns_no_data(self) -> None:
    result = run_health_checks(None)
    assert result.has_data is False
    assert result.findings == ()
    assert result.total_vms_checked == 0

def test_empty_dataframe_returns_no_data(self) -> None:
    result = run_health_checks(pd.DataFrame())
    assert result.has_data is False
```

**Parametrized Tests:**
Not heavily used in codebase — prefer explicit test methods for clarity

**Test Data Builders:**
```python
def _row(
    vm_name: str = "VM-1",
    workload_category: str = "Database/Microsoft SQL",
    provisioned_mib: float = 10000.0,
    in_use_mib: float = 5000.0,
    drr: float = 5.0,
) -> dict:
    """Helper to build a row dict matching session-state format."""
    return {
        "vm_name": vm_name,
        "workload_category": workload_category,
        "provisioned_mib": provisioned_mib,
        "in_use_mib": in_use_mib,
        "drr": drr,
    }

# Usage
rows = [_row(provisioned_mib=10000, drr=5.0)]
result = calculate(rows)
```

## Type Checking for Tests

**Config:**
- `pyproject.toml` has mypy override for `tests.*`: `disallow_untyped_defs = false`
- Allows test functions to omit return types in some cases, but `-> None:` is preferred
- Run type check: `rtk mypy src/`

**Test type hints:**
- All test functions should have `-> None:` return type
- Fixture parameters are typed: `def test_name(self, drr_table: DRRTable) -> None:`
- Helps catch refactoring errors early

## PDF Testing Gotcha

**Important:** ReportLab uses CIDFont/FlateDecode encoding — text strings are NOT searchable in raw PDF bytes.

**Solution:**
To test locale-specific PDF content, compare FR output ≠ EN output bytes, not string presence:
```python
def test_layout_page_locale_differs(self) -> None:
    """Confirm FR and EN PDFs have different byte content."""
    en_bytes = generate_report_pdf(summary, locale="en")
    fr_bytes = generate_report_pdf(summary, locale="fr")
    assert en_bytes != fr_bytes  # Locale changes PDF content
    assert len(en_bytes) > 0
    assert len(fr_bytes) > 0
```

---

*Testing analysis: 2026-02-23*
