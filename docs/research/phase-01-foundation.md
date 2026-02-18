# Phase 1: Project Foundation & DRR Table - Research

**Researched:** 2026-02-18
**Domain:** Python project scaffolding, NiceGUI web framework, CSV parsing, data models
**Confidence:** HIGH

## Summary

Phase 1 establishes the project skeleton: Python package structure, NiceGUI app entry point, DRR reference data service, typed data models, and tooling (ruff, mypy, pytest, Docker). The project starts from an empty codebase -- no Python files exist yet.

**Critical finding:** NiceGUI is now at version 3.x (latest 3.4.x as of Feb 2026), NOT 2.x as referenced in CLAUDE.md. NiceGUI 3.0 introduced breaking changes including Tailwind CSS 4 upgrade, removal of the auto-index client, and restructured upload event arguments. The project MUST target NiceGUI 3.x to use current, maintained code. Additionally, pandas 3.0 is now current.

**Primary recommendation:** Use NiceGUI >=3.4, pandas >=2.2 (pin <4.0 for stability), Python 3.12+. Structure the project with clean pipeline/services/ui separation from day one. Load DRR.csv with careful handling of embedded newlines and junk rows.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nicegui | >=3.4,<4.0 | Web UI framework | Current stable, Tailwind 4, Python-first web UIs |
| pandas | >=2.2,<4.0 | DataFrame operations, CSV parsing | Industry standard for tabular data |
| openpyxl | >=3.1.2 | XLSX file reading | Required by pandas for xlsx, well-maintained |
| reportlab | >=4.0 | PDF generation | Lightweight, no system deps, precise layout control |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Test framework | All testing |
| pytest-cov | >=5.0 | Coverage reporting | Enforce >80% coverage on pipeline/services |
| ruff | >=0.9 | Linting + formatting | All code quality checks |
| mypy | >=1.10 | Static type checking | Strict mode for all src/ |
| pandas-stubs | >=2.2 | Type stubs for pandas | mypy compatibility with pandas |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NiceGUI 2.x | NiceGUI 3.x | 3.x is current; 2.x is unmaintained. Use 3.x. |
| WeasyPrint | ReportLab | WeasyPrint adds 200-400MB Docker deps. ReportLab is 5MB. |
| csv stdlib | pandas read_csv | pandas handles quoting/newlines better and we need DataFrames anyway |

### Installation

```bash
uv venv .venv && source .venv/bin/activate
uv pip install "nicegui>=3.4,<4.0" "pandas>=2.2,<4.0" "openpyxl>=3.1.2" "reportlab>=4.0"
uv pip install "pytest>=8.0" "pytest-cov>=5.0" "ruff>=0.9" "mypy>=1.10" "pandas-stubs>=2.2"
```

## Architecture Patterns

### Recommended Project Structure

```text
store-predict/
  src/
    store_predict/
      __init__.py              # Package version
      main.py                  # NiceGUI app entry point
      config.py                # Settings (paths, defaults)

      pipeline/                # Pure business logic (NO UI imports)
        __init__.py
        models.py              # VM dataclass, FileFormat enum, WorkloadCategory

      services/                # Stateful services
        __init__.py
        drr_table.py           # Load/cache DRR reference data from CSV

      ui/                      # NiceGUI pages and components
        __init__.py
        pages/
          __init__.py
          upload.py            # Placeholder upload page (Phase 1: just skeleton)
        layout.py              # Shared layout (header, nav)

  tests/
    __init__.py
    conftest.py                # Shared fixtures
    test_drr_table.py          # DRR service tests
    test_models.py             # Data model tests

  samples/
    DRR.csv                    # Reference data (already exists)

  pyproject.toml
  Dockerfile
  docker-compose.yml
  CLAUDE.md
```

### Pattern 1: DRR Table as Immutable Service

**What:** Load DRR.csv once at startup, expose as an immutable lookup service.
**When to use:** Always -- DRR data is reference data, not user-mutable per session.
**Example:**

```python
# services/drr_table.py
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DRREntry:
    category: str
    subcategory: str
    ratio: float


class DRRTable:
    """Immutable DRR reference data loaded from CSV."""

    def __init__(self, entries: list[DRREntry]) -> None:
        self._entries = entries
        self._lookup: dict[tuple[str, str], float] = {
            (e.category, e.subcategory): e.ratio for e in entries
        }

    @classmethod
    def from_csv(cls, path: Path) -> DRRTable:
        df = pd.read_csv(
            path,
            sep=";",
            names=["category", "subcategory", "ratio"],
            skiprows=1,  # Skip header row
            quoting=csv.QUOTE_ALL,
            engine="python",
        )
        # Drop rows with missing category or ratio
        df = df.dropna(subset=["category"])
        df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
        df = df.dropna(subset=["ratio"])
        # Strip whitespace from string fields
        df["category"] = df["category"].str.strip()
        df["subcategory"] = df["subcategory"].str.strip()

        entries = [
            DRREntry(
                category=row["category"],
                subcategory=row["subcategory"],
                ratio=float(row["ratio"]),
            )
            for _, row in df.iterrows()
        ]
        return cls(entries)

    def get_ratio(self, category: str, subcategory: str) -> float:
        return self._lookup.get((category, subcategory), 5.0)

    def get_conservative_ratio(self, workloads: list[tuple[str, str]]) -> float:
        """Return the minimum (most conservative) DRR for multiple workloads."""
        if not workloads:
            return 5.0
        return min(self.get_ratio(c, s) for c, s in workloads)

    @property
    def categories(self) -> list[str]:
        return sorted(set(e.category for e in self._entries))

    @property
    def entries(self) -> list[DRREntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
```

### Pattern 2: Typed Data Models

**What:** Use frozen dataclasses and enums for all pipeline data structures.
**When to use:** All data flowing through the pipeline.
**Example:**

```python
# pipeline/models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FileFormat(Enum):
    RVTOOLS = "rvtools"
    LIVEOPTICS_XLSX = "liveoptics_xlsx"
    LIVEOPTICS_CSV = "liveoptics_csv"


@dataclass(frozen=True)
class VMRecord:
    """Normalized VM record from any input format."""
    vm_name: str
    os_name: str
    provisioned_mib: float
    in_use_mib: float
    source_format: FileFormat
    datacenter: str = ""
    cluster: str = ""
    is_template: bool = False
    is_powered_on: bool = True
```

### Pattern 3: NiceGUI 3.x App Skeleton

**What:** Minimal NiceGUI app using `@ui.page` decorator and `ui.run()`.
**When to use:** The main.py entry point.
**Example:**

```python
# main.py
from nicegui import ui


@ui.page("/")
def index() -> None:
    ui.label("StorePredict").classes("text-3xl font-bold")
    ui.label("Upload RVTools or LiveOptics export to begin.")


def main() -> None:
    ui.run(
        title="StorePredict",
        port=8080,
        storage_secret="change-me-in-production",
        reload=False,
    )


if __name__ == "__main__":
    main()
```

**NiceGUI 3.x notes:**

- `@ui.page('/')` decorator still works as before
- `.classes()` uses Tailwind CSS 4 syntax (mostly backward-compatible but borders/spacing may differ)
- `ui.run()` invoked from `python -m store_predict.main` works fine
- Do NOT use `[project.scripts]` entry points -- known bug in NiceGUI 3.0+
- Upload events now return `FileUpload` objects with `.read()`, `.text()`, `.save()` methods

### Anti-Patterns to Avoid

- **Business logic in UI handlers:** Pipeline code must live in pipeline/ or services/, never in ui/
- **Global mutable state:** Use per-session dicts, not module-level globals for user data
- **Hardcoded DRR values:** Always load from CSV via DRRTable service
- **Importing ui in pipeline/:** The pipeline/ package must have zero imports from ui/ (NFR-2.4)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with embedded newlines | Custom line-by-line parser | `pandas.read_csv(quoting=csv.QUOTE_ALL, engine="python")` | Handles quoting, encoding, edge cases |
| Type checking for DataFrames | Manual type assertions | `pandas-stubs` + mypy | Community-maintained stubs, catches real bugs |
| Dev tooling config | Separate config files | Single `pyproject.toml` | ruff, mypy, pytest all read from pyproject.toml |
| Docker Python setup | Manual venv in Docker | `python:3.12-slim` + `uv pip install` | Standard pattern, minimal image |

**Key insight:** The DRR.csv has exactly the kind of edge cases (embedded newlines, junk rows) that hand-rolled parsers get wrong. Use pandas with proper quoting configuration.

## Common Pitfalls

### Pitfall 1: DRR.csv Embedded Newline in PostgreSQL Entry

**What goes wrong:** Lines 7-8 of DRR.csv contain a newline inside a quoted field (`"\nPostgreSQL"`). Naive line-by-line reading splits this into two broken records.
**Why it happens:** The CSV was likely edited in Excel which inserted a line break inside a cell.
**How to avoid:** Use `pd.read_csv()` with `quoting=csv.QUOTE_ALL` and `engine="python"`. Verify loaded entry count equals 30 (the expected number of workload categories).
**Warning signs:** Getting 29 or 31 entries instead of 30; PostgreSQL entry missing or malformed.

### Pitfall 2: DRR.csv Trailing Junk Rows

**What goes wrong:** Lines 31-35 contain empty rows and a partial entry ("Unknown (Reducible);;"). These become NaN rows in the DataFrame.
**Why it happens:** Spreadsheet artifacts when CSV was exported.
**How to avoid:** `df.dropna(subset=["category"])` followed by `df.dropna(subset=["ratio"])`. The stray row on line 35 has category but no ratio, so the ratio dropna catches it.
**Warning signs:** Entry count > 30; entries with NaN ratios.

### Pitfall 3: NiceGUI 3.x Tailwind CSS 4 Changes

**What goes wrong:** Tailwind 4 changed default border and line-height behavior. Elements may look different than Tailwind 3 examples.
**Why it happens:** NiceGUI 3.0 upgraded from Tailwind 3 to 4.
**How to avoid:** For Phase 1, keep styling minimal. Test visual output in browser. Note that `border` utility now requires explicit `border-solid` in some cases.
**Warning signs:** Missing borders, unexpected spacing.

### Pitfall 4: NiceGUI Upload Event API Changed in 3.0

**What goes wrong:** Code written for NiceGUI 2.x `UploadEventArguments.content` (bytes) breaks. In 3.x, upload events provide a `FileUpload` object with `.read()`, `.text()`, `.save()` methods.
**Why it happens:** Breaking API change in NiceGUI 3.0.
**How to avoid:** Use the new `FileUpload` API: `e.file.read()` to get bytes.
**Warning signs:** AttributeError on upload event handling.

### Pitfall 5: mypy Strict Mode with pandas

**What goes wrong:** pandas operations return `Any` types without stubs; mypy strict rejects them.
**Why it happens:** pandas is complex; stubs don't cover everything.
**How to avoid:** Install `pandas-stubs`. For uncovered cases, use targeted `# type: ignore[...]` with specific error codes. Add mypy overrides for test files.
**Warning signs:** Hundreds of mypy errors from pandas usage.

### Pitfall 6: Python 3.12 vs System Python

**What goes wrong:** System may have Python 3.14 (as detected on this machine), but Docker and CI should target 3.12.
**Why it happens:** Dev machine Python version differs from deployment target.
**How to avoid:** Pin `requires-python = ">=3.12"` in pyproject.toml. Use `python:3.12-slim` in Dockerfile. Use `uv` for local virtual environment and package management (fast, handles Python version pinning).
**Warning signs:** Code works locally but fails in Docker due to version differences.

## Code Examples

### pyproject.toml (Complete for Phase 1)

```toml
[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "store-predict"
version = "0.1.0"
description = "PowerStore DRR sizing pre-sales tool"
requires-python = ">=3.12"
dependencies = [
    "nicegui>=3.4,<4.0",
    "pandas>=2.2,<4.0",
    "openpyxl>=3.1.2",
    "reportlab>=4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.9",
    "mypy>=1.10",
    "pandas-stubs>=2.2",
]
docs = [
    "mkdocs",
    "mkdocs-material",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
    "RUF",  # ruff-specific
]

[tool.ruff.lint.isort]
known-first-party = ["store_predict"]

[tool.mypy]
strict = true
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
plugins = []

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = "nicegui.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "reportlab.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=store_predict --cov-report=term-missing"
```

### Dockerfile (Phase 1 Minimal)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
COPY src/ src/
COPY samples/DRR.csv samples/DRR.csv

RUN uv venv .venv && . .venv/bin/activate && uv pip install --no-cache .

EXPOSE 8080

CMD [".venv/bin/python", "-m", "store_predict.main"]
```

### docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - STORAGE_SECRET=change-me-in-production
    restart: unless-stopped
```

### conftest.py (Test Fixtures)

```python
# tests/conftest.py
from pathlib import Path

import pytest

from store_predict.services.drr_table import DRRTable


@pytest.fixture
def sample_drr_path() -> Path:
    return Path(__file__).parent.parent / "samples" / "DRR.csv"


@pytest.fixture
def drr_table(sample_drr_path: Path) -> DRRTable:
    return DRRTable.from_csv(sample_drr_path)
```

### DRR Table Test Examples

```python
# tests/test_drr_table.py
from store_predict.services.drr_table import DRRTable


def test_drr_table_loads_30_entries(drr_table: DRRTable) -> None:
    """DRR.csv should produce exactly 30 workload categories."""
    assert len(drr_table) == 30


def test_postgresql_entry_parsed_correctly(drr_table: DRRTable) -> None:
    """PostgreSQL entry has embedded newline in CSV -- must parse correctly."""
    ratio = drr_table.get_ratio("Database", "PostgreSQL")
    assert ratio == 1.5


def test_unknown_reducible_default(drr_table: DRRTable) -> None:
    """Unknown (Reducible) has DRR = 5."""
    ratio = drr_table.get_ratio("Unknown (Reducible)", "Unknown (Reducible)")
    assert ratio == 5.0


def test_missing_category_returns_default(drr_table: DRRTable) -> None:
    """Unknown category/subcategory returns default DRR of 5.0."""
    ratio = drr_table.get_ratio("NonExistent", "Nothing")
    assert ratio == 5.0


def test_conservative_ratio_returns_minimum(drr_table: DRRTable) -> None:
    """Multi-workload uses the lowest (most conservative) DRR."""
    ratio = drr_table.get_conservative_ratio([
        ("Database", "Oracle"),       # DRR = 5
        ("Database", "DB2"),          # DRR = 1.5
    ])
    assert ratio == 1.5


def test_conservative_ratio_empty_returns_default(drr_table: DRRTable) -> None:
    """Empty workload list returns default DRR = 5.0."""
    ratio = drr_table.get_conservative_ratio([])
    assert ratio == 5.0


def test_all_ratios_positive(drr_table: DRRTable) -> None:
    """All DRR values must be > 0 (prevent division by zero)."""
    for entry in drr_table.entries:
        assert entry.ratio > 0, f"{entry.category}/{entry.subcategory} has ratio {entry.ratio}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NiceGUI 2.x | NiceGUI 3.x (3.4+) | Oct 2025 | Tailwind 4, new upload API, no auto-index |
| Tailwind CSS 3 | Tailwind CSS 4 (via NiceGUI 3) | Oct 2025 | Border/spacing defaults changed |
| pandas 2.x | pandas 3.0 available | 2025 | API stable; pin >=2.2,<4.0 for safety |
| setup.py/setup.cfg | pyproject.toml | Standard since 2023 | All config in one file |

**Deprecated/outdated:**

- NiceGUI `ui.open()` -- removed in 3.0, use `ui.navigate.to()` instead
- NiceGUI `ui.element.tailwind` API -- removed in 3.0, use `.classes()` with Tailwind utilities
- NiceGUI `UploadEventArguments.content` (bytes) -- replaced with `FileUpload` object
- NiceGUI `nicegui.testing.conftest` import -- use `pytest_plugins = ["nicegui.testing.plugin"]`

## Open Questions

1. **NiceGUI 3.x upload event exact API**
   - What we know: `FileUpload` object with `.read()`, `.text()`, `.save()`, `.size()` methods
   - What's unclear: Exact import path and event argument structure for single-file upload
   - Recommendation: Phase 1 only needs skeleton page; verify upload API in Phase 2 when implementing ingestion

2. **pandas-stubs coverage for 3.0**
   - What we know: pandas-stubs exists for 2.x; pandas 3.0 is new
   - What's unclear: Whether pandas-stubs fully covers pandas 3.0
   - Recommendation: Pin pandas >=2.2,<4.0 to allow either; use pandas-stubs >=2.2

3. **DRR.csv PostgreSQL field exact content**
   - What we know: Lines 7-8 show `"` then `PostgreSQL"` with embedded newline
   - What's unclear: Whether the leading newline is intentional or artifact
   - Recommendation: Strip whitespace from subcategory field after loading; test for "PostgreSQL" match

## Sources

### Primary (HIGH confidence)

- DRR.csv direct inspection -- verified 35 lines, embedded newline, trailing junk
- [NiceGUI 3.0.0 release notes](https://github.com/zauberzeug/nicegui/releases/tag/v3.0.0) -- all breaking changes documented
- [NiceGUI PyPI](https://pypi.org/project/nicegui/) -- current version 3.4.x confirmed
- [mypy configuration docs](https://mypy.readthedocs.io/en/stable/config_file.html) -- strict mode flags
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) -- pyproject.toml format
- Project `.planning/research/` files -- ARCHITECTURE.md, STACK.md, PITFALLS.md, FEATURES.md

### Secondary (MEDIUM confidence)

- [NiceGUI upload docs](https://nicegui.io/documentation/upload) -- current API reference
- [NiceGUI entry point issue #5411](https://github.com/zauberzeug/nicegui/issues/5411) -- `[project.scripts]` bug confirmed
- [pandas read_csv docs](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html) -- quoting/delimiter options

### Tertiary (LOW confidence)

- NiceGUI 3.x upload event argument exact structure -- verified from release notes but not from live code testing

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH -- versions verified against PyPI, breaking changes documented
- Architecture: HIGH -- project structure validated against prior research and NiceGUI patterns
- Pitfalls: HIGH -- DRR.csv issues verified by direct file inspection; NiceGUI 3.0 changes from release notes
- Code examples: MEDIUM -- based on documented APIs but not runtime-tested

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable domain, 30 days)
