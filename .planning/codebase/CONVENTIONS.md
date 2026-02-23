# Coding Conventions

**Analysis Date:** 2026-02-23

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `classification.py`, `drr_table.py`, `pdf_report.py`
- Private/internal modules use leading underscore: `_patterns()` (helper functions)
- Test files follow pattern: `test_<module>.py`

**Functions:**
- Use snake_case: `strip_company_prefix()`, `classify_dataframe()`, `run_health_checks()`
- Private functions use single leading underscore: `_patterns()`, `_regex_patterns()`, `_row()`
- Single-letter loop variables allowed in simple contexts; avoid shadowing `t()` i18n import (use `wt` instead)

**Variables:**
- Use snake_case throughout: `vm_name`, `provisioned_mib`, `workload_category`
- Constants at module/class level use UPPER_SNAKE_CASE: `_XLSX_MAGIC`, `_LARGE_VM_THRESHOLD_MIB`, `DEFAULT_DRR`, `APP_PORT`
- Data class attributes use snake_case: `required_mib`, `total_provisioned_mib`, `weighted_avg_drr`

**Types:**
- Dataclasses preferred for immutable value objects (use `frozen=True`): `@dataclass(frozen=True) class VMCalculation`
- Enums use StrEnum or Enum with UPPER_SNAKE_CASE values: `class FileFormat(Enum)`, `class Severity(StrEnum)`
- Type hints required on all functions and class attributes (strict mypy)

## Code Style

**Formatting:**
- Tool: `ruff` with 120-character line length
- Python version: 3.12 minimum
- Auto-format with: `rtk ruff format .`

**Linting:**
- Tool: `ruff` with strict rules
- Enabled rules: E (pycodestyle errors), W (warnings), F (pyflakes), I (isort), N (pep8-naming), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify), TCH (flake8-type-checking), RUF (ruff-specific)
- Run with: `rtk ruff check .`

## Import Organization

**Order (enforced by isort):**
1. `from __future__ import annotations` (always first if present)
2. Standard library imports
3. Third-party imports (pandas, openpyxl, pydantic, etc.)
4. Local application imports from `store_predict`

**Example:**
```python
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from store_predict.config import COMPANY_PREFIX_PATTERNS
from store_predict.pipeline.errors import IngestionError

if TYPE_CHECKING:
    from store_predict.services.drr_table import DRRTable
```

**Path Aliases:**
- Use absolute imports from `store_predict` root: `from store_predict.pipeline.classification import ...`
- Use `TYPE_CHECKING` guards to avoid circular imports for type hints only: `if TYPE_CHECKING: from store_predict.services.drr_table import DRRTable`
- Use local imports to break circular dependencies: `from store_predict.config import StorageModel  # local import avoids circular at module level`

## Error Handling

**Patterns:**
- Custom exception `IngestionError` has `message` (user-facing) and `details` (developer-facing)
- Raise with context: `raise IngestionError("User message") from err` to preserve stack
- Validation errors re-raise with exception chaining: `raise IngestionError("File invalid") from err`
- No bare `except:` — always specify exception type
- DataFrame operations check for empty/None states before processing

**Example:**
```python
try:
    content[:1024].decode("utf-8")
except UnicodeDecodeError as err:
    raise IngestionError("File does not appear to be a valid CSV file") from err
```

## Logging

**Framework:** Python standard `logging` module

**Configuration:**
- Setup via `logging_config.py:setup_logging()` — sets level and standard formatter
- Logger name: `"store_predict"`
- Handler: StreamHandler with format: `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`

**Security Constraints:**
- NEVER log DataFrame contents, VM names, IP addresses, hostnames, or customer-identifiable data
- Log only metadata: counts, format types, timing, error messages, check IDs
- This prevents accidental data leakage in production logs

## Comments

**When to Comment:**
- Complex business logic (e.g., weighted average DRR calculation)
- Non-obvious algorithm choices (e.g., BFD placement strategy)
- Security or data handling notes (e.g., "NEVER log VM names")
- Edge cases and workarounds (e.g., embedded newlines in DRR CSV)
- Do NOT comment obvious code

**Module docstrings:**
- Always present at module top
- Describe purpose, dependencies, and entry points
- Example: `"""Classification engine for VM-to-DRR category mapping. Rules-based pattern matching on VM name and OS field."""`

**Class docstrings:**
- Required for dataclasses and service classes
- One-line summary + attributes explanation if non-obvious

**Function docstrings:**
- Use Google-style format (Args, Returns, Raises)
- Include rationale for complex functions
- Example:
  ```python
  def classify_dataframe(
      df: pd.DataFrame, rules: RuleRegistry
  ) -> pd.DataFrame:
      """Classify all VMs in a DataFrame using the rule registry.

      Args:
          df: Input DataFrame with vm_name and os_name columns.
          rules: RuleRegistry with compiled classification rules.

      Returns:
          DataFrame with added workload_category column.

      Raises:
          ValueError: If required columns are missing.
      """
  ```

## Function Design

**Size:**
- Prefer single-responsibility functions under 30 lines
- Helper functions use leading underscore if private to module: `_row()`, `_make_active_df()`
- Factory functions return callables for test fixtures: `make_summary() -> Callable[[], CalculationSummary]`

**Parameters:**
- Use positional args for required inputs
- Use keyword-only args for options (after `*`) in complex functions
- Avoid long parameter lists — use dataclasses instead

**Return Values:**
- Prefer immutable dataclasses for complex returns: `@dataclass(frozen=True) class CalculationSummary`
- Return tuples for simple multi-value returns: `tuple[str, ...]`
- Use `None` explicitly when no return value, not early returns everywhere
- Type annotations are mandatory: `def calculate(...) -> CalculationSummary:`

## Module Design

**Exports:**
- Use `__all__` list in public modules: `__all__ = ["CalculationSummary", "VMCalculation", "calculate"]`
- Modules may have internal helper functions (prefixed with `_`) not in `__all__`

**Barrel Files:**
- Not used in `store_predict` — import directly from source modules
- Parsers have central import: `from store_predict.pipeline.parsers import parse_rvtools, parse_liveoptics_xlsx`

**Pure pipeline modules:**
- Core business logic has zero UI imports — marked in docstring: `"""Pure pipeline module with zero UI imports."""`
- Session/UI-aware code in `src/store_predict/ui/pages/` and `src/store_predict/ui/state.py`
- Separation enables testability without mocking

**i18n Integration:**
- All user-facing strings use `t()` from `store_predict.i18n`
- New i18n keys go in both `src/store_predict/i18n/locales/en.yaml` and `fr.yaml`
- Data class attributes for i18n keys are just key strings: `title: str  # i18n key, e.g. "health.zero_provisioned.title"`

**Data/Reference:**
- DRR reference loaded from `samples/DRR.csv` (CSV, not hardcoded)
- Sample data in `samples/` is real customer data — never commit additional without anonymization
- Configuration via `store_predict.config` module using Path and StrEnum

---

*Convention analysis: 2026-02-23*
