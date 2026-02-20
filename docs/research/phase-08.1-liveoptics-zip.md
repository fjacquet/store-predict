# Phase 08.1: LiveOptics ZIP Extraction - Research

**Researched:** 2026-02-20
**Domain:** Python zipfile stdlib, upload validation, pipeline pre-processing
**Confidence:** HIGH

## Summary

LiveOptics exports its data package as a ZIP archive containing a single XLSX file named `LiveOptics_<ID>_VMWARE_<DD>_<MM>_<YYYY>.xlsx`. This phase inserts a pure pre-processing step in the upload handler — before validation — that detects a `.zip` upload, extracts the XLSX bytes in memory, and passes them through the existing pipeline unchanged. The Python `zipfile` stdlib is sufficient; no third-party library is needed.

## Key Findings

### In-Memory Extraction via BytesIO

Open the ZIP from raw upload bytes using `io.BytesIO`. `zf.read(member_name)` returns bytes directly — no temp files, no disk I/O, no cleanup burden.

```python
import io, zipfile

with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    xlsx_bytes = zf.read("LiveOptics_99999_VMWARE_15_02_2026.xlsx")
```

### Zip Bomb Protection via Central Directory

The ZIP central directory stores uncompressed sizes for all members. Reading `info.file_size` is O(n_members), not O(bytes) — checking it before extraction is essentially free and safe.

```python
total_uncompressed = sum(info.file_size for info in zf.infolist())
if total_uncompressed > 50 * 1024 * 1024:
    raise IngestionError("ZIP content exceeds the 50 MiB limit.")
```

### Filename Pattern with re.search

Use `re.search` (not `re.match`) because ZIP members may have directory prefixes like `exports/LiveOptics_...xlsx`. `re.match` would fail to match such paths.

```python
_LIVEOPTICS_PATTERN = re.compile(
    r"LiveOptics_\d+_VMWARE_\d{2}_\d{2}_\d{4}\.xlsx"
)
matches = [name for name in zf.namelist() if _LIVEOPTICS_PATTERN.search(name)]
```

### Integration Point in Upload Handler

Call the extractor in `_handle_upload` after `await e.file.read()` and before `validate_upload()`. Update both `content` and `filename` to avoid the extension mismatch that would fail validation.

```python
filename = e.file.name
content = await e.file.read()

if filename.lower().endswith(".zip"):
    content = extract_liveoptics_from_zip(content)
    filename = filename.replace(".zip", ".xlsx")

validate_upload(content, filename)
```

### ZIP and XLSX Share the Same Magic Bytes

Both `.zip` and `.xlsx` files start with `PK\x03\x04`. Reuse the existing `_XLSX_MAGIC` constant in `validation.py` for ZIP validation — do not create a duplicate constant. Add a comment explaining this identity.

### In-Memory Test Fixtures

Build ZIP fixtures in memory for tests — no files on disk needed. Use `ZIP_DEFLATED` to be realistic.

```python
def make_test_zip(member_name: str, member_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, member_bytes)
    return buf.getvalue()
```

## Anti-Patterns

- **Extracting to disk first:** `zf.read(name)` returns bytes directly. Writing to a temp file just to read it back is unnecessary I/O.
- **Raising raw `zipfile.BadZipFile` to the UI:** Always wrap in `IngestionError` so the existing `except IngestionError` handler in `upload.py` catches it and shows a friendly `ui.notify()`.
- **Forgetting to update `filename` after extraction:** After replacing ZIP bytes with XLSX bytes, `validate_upload` still sees the original `.zip` extension and rejects it. Update `filename` to end in `.xlsx` before calling validation.

## Dependencies

No new dependencies. All functionality uses Python stdlib (`zipfile`, `io`, `re`). Also update the NiceGUI upload widget `accept` prop to include `.zip` so the browser file picker allows it.
