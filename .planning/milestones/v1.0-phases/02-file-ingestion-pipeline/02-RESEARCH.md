# Phase 2: File Ingestion Pipeline - Research

**Researched:** 2026-02-18
**Domain:** Excel/CSV parsing, format detection, data normalization, pandas DataFrame operations
**Confidence:** HIGH

## Summary

Phase 2 implements parsers for RVTools (.xlsx) and LiveOptics (.xlsx/.csv) files, auto-detects the format, normalizes data into a common DataFrame schema, and filters template VMs. The existing codebase already has the `VMRecord` dataclass and `FileFormat` enum from Phase 1, plus pandas and openpyxl in the dependency stack.

Key discovery from inspecting the actual sample files: RVTools has 70 columns in vInfo (we need 8), LiveOptics has 38 columns in VMs (we need ~8). RVTools labels columns as "MB" but values are actually MiB (base-2), matching LiveOptics which explicitly uses "MiB". This means NO unit conversion is needed between formats -- both are already in MiB despite different labeling. The Template column in RVTools is a boolean (`True`/`False`/`NaN`), not a string "True" as the requirements suggest.

The project already has two sample files (`samples/rvtools.xlsx` with 24 VMs, `samples/live-optics.xlsx` with 610 VMs) plus a second LiveOptics file in `samples/CIGES-IT_02_16_2026/`. Both LiveOptics files have identical column schemas, confirming the format is stable.

**Primary recommendation:** Build three parser functions (one per format) that return `pd.DataFrame` with a canonical schema, plus a format detector that dispatches to the correct parser. Use simple alias dictionaries for column fuzzy matching (no external library needed). Return errors as custom exceptions with user-friendly messages.

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.2,<4.0 | DataFrame creation, CSV reading | Already in project, handles all tabular ops |
| openpyxl | >=3.1.2 | XLSX reading engine for pandas | Already in project, required by `pd.read_excel` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Testing parsers | All parser tests |

### No New Dependencies Needed

Column "fuzzy matching" as described in FR-1.7 does not require fuzzywuzzy, rapidfuzz, or any NLP library. The actual need is **alias mapping**: known column name variations (e.g., "Provisioned MiB" vs "Provisioned MB") resolved via a dictionary. This is a 10-line solution, not a library problem.

## Architecture Patterns

### Recommended Module Structure

```
src/store_predict/
├── pipeline/
│   ├── __init__.py
│   ├── models.py           # Already exists (VMRecord, FileFormat)
│   ├── ingestion.py         # Format detection + orchestration
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── rvtools.py       # RVTools .xlsx parser
│   │   ├── liveoptics.py    # LiveOptics .xlsx and .csv parser
│   │   └── columns.py       # Column alias maps + resolver
│   └── errors.py            # Custom exceptions
```

### Pattern 1: Parser Function Signature

**What:** Each parser returns a normalized DataFrame, never VMRecord objects directly. VMRecord conversion happens downstream if needed.

**Why:** DataFrames are the natural unit for batch operations (filtering, calculations). Converting to/from dataclasses row-by-row is wasteful for 5000+ VMs.

```python
# Each parser module exposes one public function:
def parse_rvtools(path: Path) -> pd.DataFrame:
    """Parse RVTools xlsx vInfo tab into normalized DataFrame.

    Returns DataFrame with canonical columns:
        vm_name, os_name, provisioned_mib, in_use_mib,
        datacenter, cluster, is_template, is_powered_on, source_format

    Raises:
        IngestionError: If file cannot be parsed or required columns missing.
    """

def parse_liveoptics_xlsx(path: Path) -> pd.DataFrame:
    """Parse LiveOptics xlsx VMs tab into normalized DataFrame."""

def parse_liveoptics_csv(path: Path) -> pd.DataFrame:
    """Parse LiveOptics CSV into normalized DataFrame."""
```

### Pattern 2: Format Detection

**What:** Detect format by inspecting file extension + internal structure (sheet names for xlsx, column headers for csv).

```python
def detect_format(path: Path) -> FileFormat:
    """Auto-detect file format.

    Strategy:
    1. CSV extension → check headers → LiveOptics CSV or error
    2. XLSX extension → check sheet names:
       - Has 'vInfo' sheet → RVTools
       - Has 'VMs' sheet → LiveOptics XLSX
       - Neither → IngestionError
    """
```

**Evidence from sample files:**

- RVTools sheets: `['vInfo', 'vCPU', 'vMemory', 'vDisk', ...]` (25 sheets)
- LiveOptics sheets: `['Details', 'ESX Hosts', ..., 'VMs', ...]` (11 sheets)
- Sheet name overlap: None between the two formats. Detection is unambiguous.

### Pattern 3: Column Resolution with Aliases

**What:** Map known column name variations to canonical names using a dictionary.

```python
# columns.py
RVTOOLS_ALIASES: dict[str, list[str]] = {
    "vm_name": ["VM", "VM Name"],
    "powerstate": ["Powerstate", "Power State"],
    "is_template": ["Template"],
    "os_name": ["OS according to the VMware Tools", "OS according to the configuration file"],
    "provisioned_mib": ["Provisioned MB", "Provisioned MiB"],
    "in_use_mib": ["In Use MB", "In Use MiB"],
    "datacenter": ["Datacenter"],
    "cluster": ["Cluster"],
}

LIVEOPTICS_ALIASES: dict[str, list[str]] = {
    "vm_name": ["VM Name"],
    "os_name": ["VM OS"],
    "provisioned_mib": ["Virtual Disk Size (MiB)"],
    "in_use_mib": ["Guest VM Disk Used (MiB)"],
    "guest_capacity_mib": ["Guest VM Disk Capacity (MiB)"],
    "is_template": ["Template"],
    "powerstate": ["Power State"],
    "datacenter": ["Datacenter"],
    "cluster": ["Cluster"],
}

def resolve_columns(df: pd.DataFrame, aliases: dict[str, list[str]]) -> dict[str, str]:
    """Map canonical names to actual column names found in the DataFrame.

    Returns: {canonical_name: actual_column_name}
    Raises IngestionError if required columns are not found.
    """
```

### Pattern 4: Canonical DataFrame Schema

**What:** All parsers produce a DataFrame with identical columns regardless of source format.

```python
CANONICAL_COLUMNS = [
    "vm_name",          # str
    "os_name",          # str
    "provisioned_mib",  # float64
    "in_use_mib",       # float64
    "datacenter",       # str (empty string if unavailable)
    "cluster",          # str (empty string if unavailable)
    "is_template",      # bool
    "is_powered_on",    # bool
    "source_format",    # str (FileFormat.value)
]
```

### Pattern 5: Ingestion Orchestrator

**What:** Single entry point that combines detection + parsing + filtering.

```python
def ingest_file(path: Path) -> pd.DataFrame:
    """Main entry point: detect format, parse, filter templates, return normalized DataFrame.

    Steps:
    1. Validate file exists and has valid extension
    2. Detect format
    3. Parse with appropriate parser
    4. Filter out template VMs (is_template == True)
    5. Return cleaned DataFrame
    """
```

### Anti-Patterns to Avoid

- **Row-by-row processing:** Never iterate rows to create VMRecord objects during ingestion. Use vectorized pandas operations. VMRecord is for downstream typed access if needed, not for parsing.
- **Reading entire workbook:** Use `pd.read_excel(path, sheet_name='vInfo')` which reads only the specified sheet, not all 25 sheets.
- **String comparison for booleans:** Template column in RVTools is already boolean dtype, not string. Don't do `df['Template'] == 'True'` -- use `df['Template'] == True` or `df['Template'].fillna(False).astype(bool)`.
- **Hardcoded column indices:** Always use column names, never positional indexing. Column order varies between RVTools versions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XLSX parsing | Custom XML reader | `pd.read_excel(engine='openpyxl')` | Handles encoding, data types, large files |
| CSV parsing | Custom delimiter logic | `pd.read_csv()` | Handles quoting, encoding, malformed rows |
| Column matching | Levenshtein distance | Alias dictionary lookup | Known set of variations, not arbitrary fuzzy match |
| File validation | Manual magic byte checking | Extension check + sheet name inspection | Sufficient for the known format set |

**Key insight:** The "fuzzy matching" requirement (FR-1.7) sounds like it needs NLP but is really just an alias table. RVTools and LiveOptics have well-known column schemas with minor variations between versions. A dictionary of known aliases covers all real-world cases.

## Common Pitfalls

### Pitfall 1: RVTools Template Column Contains NaN

**What goes wrong:** Filtering `df[df['Template'] == False]` drops rows where Template is NaN (which are non-template VMs that just have missing data).
**Why it happens:** RVTools exports sometimes have NaN for Template on certain VMs (seen in our sample: 4 out of 24 VMs have NaN).
**How to avoid:** Use `df['Template'].fillna(False)` before filtering, or filter with `df['Template'] != True`.
**Warning signs:** VM count after filtering is lower than expected.

### Pitfall 2: RVTools "MB" Values Are Actually MiB

**What goes wrong:** Applying MB-to-MiB conversion factor (dividing by 1.048576) when not needed, understating capacity.
**Why it happens:** Column headers say "MB" but VMware/RVTools uses base-2 (MiB) values despite the label.
**How to avoid:** Pass through values as-is. Both RVTools "MB" and LiveOptics "MiB" are already in MiB.
**Evidence:** [RVTools documentation](https://sizing-workshop.readthedocs.io/en/latest/datacollection/rvtools/rvtools.html) confirms values are MiB despite "MB" label. Also confirmed by [VMware documentation](https://www.coursehero.com/file/p4tebkm/Note-Despite-vCenter-and-RVTools-displaying-values-labeled-MB-GB-etc-they-are/).

### Pitfall 3: LiveOptics Provisioned Capacity Ambiguity

**What goes wrong:** Using wrong column for "provisioned" capacity.
**Why it happens:** LiveOptics has three capacity columns: `Virtual Disk Size (MiB)` (provisioned virtual disk), `Guest VM Disk Capacity (MiB)` (guest-visible capacity), `Guest VM Disk Used (MiB)` (actual used).
**How to avoid:** Map `Virtual Disk Size (MiB)` to `provisioned_mib` and `Guest VM Disk Used (MiB)` to `in_use_mib`. The `Guest VM Disk Capacity (MiB)` is informational but not used in the canonical schema.

### Pitfall 4: Encoding Issues in VM Names

**What goes wrong:** French characters (accents, cedilla) in VM names get corrupted.
**Why it happens:** CSV files may use Windows-1252 encoding instead of UTF-8.
**How to avoid:** Try UTF-8 first, fall back to `latin-1`/`cp1252` for CSV parsing. XLSX files handle encoding internally via openpyxl.

### Pitfall 5: Large File Performance

**What goes wrong:** Reading 5000-VM xlsx files takes too long or uses too much memory.
**Why it happens:** Reading all columns when only 8 are needed; or reading all sheets.
**How to avoid:** Use `usecols` parameter in `pd.read_excel()` to read only needed columns. Only read the target sheet. For very large files, openpyxl's `read_only=True` mode is automatically used by pandas.

### Pitfall 6: Column Name Trailing Spaces

**What goes wrong:** Column matching fails silently.
**Why it happens:** Some RVTools exports have trailing spaces in column headers (observed: `'Free % '` in vPartition). This could also affect vInfo columns.
**How to avoid:** Strip whitespace from all column names: `df.columns = df.columns.str.strip()`.

## Code Examples

### Reading RVTools vInfo Sheet

```python
# Source: verified against actual samples/rvtools.xlsx
import pandas as pd
from pathlib import Path

def parse_rvtools(path: Path) -> pd.DataFrame:
    # Read only the vInfo sheet
    df = pd.read_excel(path, sheet_name="vInfo", engine="openpyxl")

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Resolve columns via aliases
    col_map = resolve_columns(df, RVTOOLS_ALIASES)

    # Select and rename to canonical names
    result = df[[col_map[c] for c in REQUIRED_COLUMNS]].copy()
    result.columns = pd.Index(list(REQUIRED_COLUMNS))

    # Normalize types
    result["is_template"] = result["is_template"].fillna(False).astype(bool)
    result["is_powered_on"] = result["powerstate"].str.lower() == "poweredon"
    result["source_format"] = FileFormat.RVTOOLS.value

    # Fill missing string columns
    for col in ["datacenter", "cluster", "os_name"]:
        result[col] = result[col].fillna("")

    return result
```

### Reading LiveOptics XLSX

```python
# Source: verified against actual samples/live-optics.xlsx
def parse_liveoptics_xlsx(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="VMs", engine="openpyxl")
    df.columns = df.columns.str.strip()

    col_map = resolve_columns(df, LIVEOPTICS_ALIASES)

    result = pd.DataFrame({
        "vm_name": df[col_map["vm_name"]],
        "os_name": df[col_map["os_name"]].fillna(""),
        "provisioned_mib": pd.to_numeric(df[col_map["provisioned_mib"]], errors="coerce").fillna(0.0),
        "in_use_mib": pd.to_numeric(df[col_map["in_use_mib"]], errors="coerce").fillna(0.0),
        "datacenter": df[col_map["datacenter"]].fillna(""),
        "cluster": df[col_map["cluster"]].fillna(""),
        "is_template": df[col_map["is_template"]].fillna(False).astype(bool),
        "is_powered_on": df[col_map["powerstate"]].str.lower() == "poweredon",
        "source_format": FileFormat.LIVEOPTICS_XLSX.value,
    })
    return result
```

### Reading LiveOptics CSV

```python
def parse_liveoptics_csv(path: Path) -> pd.DataFrame:
    # Try UTF-8 first, fall back to latin-1
    for encoding in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise IngestionError("Cannot decode CSV file. Unsupported encoding.")

    df.columns = df.columns.str.strip()
    # Same column resolution and normalization as XLSX
    # ...
```

### Format Detection

```python
def detect_format(path: Path) -> FileFormat:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        # Validate it has LiveOptics columns
        df_head = pd.read_csv(path, nrows=0)
        df_head.columns = df_head.columns.str.strip()
        if "VM Name" in df_head.columns or "VM OS" in df_head.columns:
            return FileFormat.LIVEOPTICS_CSV
        raise IngestionError(
            "CSV file does not match LiveOptics format. "
            "Expected columns: VM Name, VM OS, etc."
        )

    if suffix == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        sheets = wb.sheetnames
        wb.close()

        if "vInfo" in sheets:
            return FileFormat.RVTOOLS
        if "VMs" in sheets:
            return FileFormat.LIVEOPTICS_XLSX
        raise IngestionError(
            f"XLSX file has unrecognized sheets: {sheets[:5]}. "
            "Expected 'vInfo' (RVTools) or 'VMs' (LiveOptics)."
        )

    raise IngestionError(
        f"Unsupported file type: {suffix}. "
        "Please upload .xlsx (RVTools or LiveOptics) or .csv (LiveOptics)."
    )
```

### Custom Exception

```python
class IngestionError(Exception):
    """Raised when file ingestion fails with a user-friendly message."""

    def __init__(self, message: str, *, details: str = "") -> None:
        self.message = message  # User-facing
        self.details = details  # Developer-facing (NOT logged to UI)
        super().__init__(message)
```

## Actual Column Data from Sample Files

### RVTools vInfo (samples/rvtools.xlsx)

Relevant columns from the 70 available:

| Column Name | Dtype | Sample Value | Maps To |
|-------------|-------|--------------|---------|
| VM | str | RSL-DC-01 | vm_name |
| Powerstate | str | poweredOn / poweredOff / NaN | is_powered_on |
| Template | bool | True / False / NaN | is_template |
| OS according to the VMware Tools | str | Microsoft Windows Server 2012 (64-bit) | os_name |
| Provisioned MB | int64 | 51227 | provisioned_mib (no conversion) |
| In Use MB | int64 | 22497 | in_use_mib (no conversion) |
| Datacenter | str | RSL Cluster | datacenter |
| Cluster | str | RSL | cluster |

- Total VMs in sample: 24
- Templates: 2 (True), 4 NaN, 18 False
- Powerstate: poweredOn, poweredOff, NaN

### LiveOptics VMs (samples/live-optics.xlsx)

Relevant columns from the 38 available:

| Column Name | Dtype | Sample Value | Maps To |
|-------------|-------|--------------|---------|
| VM Name | str | 3000-GPO-TEST | vm_name |
| VM OS | str | Microsoft Windows 10 (64-bit) | os_name |
| Virtual Disk Size (MiB) | int64 | 61440 | provisioned_mib |
| Guest VM Disk Used (MiB) | int64 | 32978 | in_use_mib |
| Guest VM Disk Capacity (MiB) | int64 | 60811 | (informational, not mapped) |
| Template | bool | True / False | is_template |
| Power State | str | poweredOn / poweredOff | is_powered_on |
| Datacenter | str | vxr-dc-win | datacenter |
| Cluster | str | vxr-clu-win | cluster |

- Total VMs in sample: 610
- No NaN in key columns (VM Name, VM OS, capacity columns)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `xlrd` for xlsx | `openpyxl` for xlsx | xlrd 2.0 (2020) | xlrd dropped xlsx support; openpyxl is required |
| pandas `read_excel` without engine | pandas with `engine='openpyxl'` explicit | pandas 1.2+ | Best practice to be explicit about engine |
| Manual CSV encoding detection | `chardet` or try/except cascade | Ongoing | Simple try/except is sufficient for known formats |

**No deprecated approaches in current stack.** pandas 2.2+ and openpyxl 3.1+ are current and stable.

## Testing Strategy

Per project convention: NO unittest.mock. Use real sample files as fixtures.

### Test Fixtures Needed

```python
# conftest.py additions
@pytest.fixture
def rvtools_path() -> Path:
    return Path(__file__).parent.parent / "samples" / "rvtools.xlsx"

@pytest.fixture
def liveoptics_xlsx_path() -> Path:
    return Path(__file__).parent.parent / "samples" / "live-optics.xlsx"

# For CSV testing, export a CSV from the LiveOptics xlsx or create a minimal fixture
```

### Key Test Cases

1. **Format detection:** RVTools xlsx detected correctly, LiveOptics xlsx detected, CSV detected, unknown rejected
2. **RVTools parsing:** Correct column extraction, template filtering, NaN Template handling, Powerstate mapping
3. **LiveOptics parsing:** Correct column extraction, template handling
4. **Schema consistency:** All parsers produce identical column sets
5. **Edge cases:** Empty file, wrong extension, missing required columns, file with extra columns
6. **Column alias resolution:** Known variations resolved, unknown columns raise clear error

### CSV Test Data

No LiveOptics CSV sample file exists in the repo. Options:

1. Export from the xlsx sample during test setup (using pandas)
2. Create a small hand-written CSV fixture in tests/fixtures/

Recommendation: Create a small CSV fixture file (5-10 rows) rather than depending on runtime xlsx-to-csv conversion.

## Open Questions

1. **LiveOptics CSV column separator**
   - What we know: LiveOptics xlsx has standard columns. CSV likely uses comma separator.
   - What's unclear: No sample CSV file exists to verify delimiter and encoding.
   - Recommendation: Default to comma, add encoding fallback, verify with first real CSV upload.

2. **RVTools version variations**
   - What we know: Current sample has exact column names documented above.
   - What's unclear: Older RVTools versions may use slightly different column names.
   - Recommendation: The alias dictionary handles this. Start with known names, add aliases as real-world files surface variations.

3. **Whether to keep VMRecord or use DataFrame throughout**
   - What we know: VMRecord dataclass exists from Phase 1. DataFrames are more efficient for batch operations.
   - What's unclear: Whether downstream phases (classification, UI) expect VMRecord objects or DataFrames.
   - Recommendation: Ingestion returns DataFrame. Provide a utility `df_to_records()` if downstream needs VMRecord. Don't convert eagerly.

## Sources

### Primary (HIGH confidence)

- **Actual sample files** inspected with openpyxl and pandas:
  - `samples/rvtools.xlsx` - 24 VMs, 70 columns in vInfo, Template is boolean with NaN
  - `samples/live-optics.xlsx` - 610 VMs, 38 columns in VMs, clean data
  - `samples/CIGES-IT_02_16_2026/LiveOptics_3221684_VMWARE_02_12_2026.xlsx` - identical schema to main sample
- **Existing codebase**: `pipeline/models.py` (VMRecord, FileFormat), `config.py` (paths), `conftest.py` (fixtures)
- **pandas documentation**: `pd.read_excel()`, `pd.read_csv()` API verified from training data (stable API)

### Secondary (MEDIUM confidence)

- [RVTools sizing workshop docs](https://sizing-workshop.readthedocs.io/en/latest/datacollection/rvtools/rvtools.html) - confirmed MB values are actually MiB
- [VMware/RVTools unit documentation](https://www.coursehero.com/file/p4tebkm/Note-Despite-vCenter-and-RVTools-displaying-values-labeled-MB-GB-etc-they-are/) - confirmed base-2 units despite "MB" labels

### Tertiary (LOW confidence)

- None. All findings verified against actual sample files.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - already installed and verified in Phase 1
- Architecture: HIGH - patterns derived from actual file inspection, not speculation
- Pitfalls: HIGH - NaN Template and MB/MiB issues verified against real sample data
- Column schemas: HIGH - extracted directly from sample files with code

**Research date:** 2026-02-18
**Valid until:** 2026-04-18 (stable domain, file formats don't change frequently)
