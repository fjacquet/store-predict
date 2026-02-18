# Pitfalls Research — StorePredict

## Critical Pitfalls

### 1. openpyxl + NumPy Version Incompatibility
**Risk:** `numpy.short` AttributeError when reading xlsx files with numeric data.
**Mitigation:** Pin compatible versions in pyproject.toml. Test xlsx parsing in CI with exact dependency versions. Use `openpyxl>=3.1.2` with `numpy>=1.24,<2.0` or verify NumPy 2.x compatibility.

### 2. RVTools Column Name Variations
**Risk:** RVTools column names change between versions and localizations:
- English: "VM Name", "OS according to VMware Tools", "Provisioned MiB"
- Older versions: "VM", "Guest OS", "Provisioned MB"
- Localized versions: entirely different column names (German, French)
**Mitigation:** Use fuzzy column matching — normalize headers (lowercase, strip whitespace), match against known aliases. Fail gracefully with clear error if no match.

### 3. DRR.csv Embedded Newlines and Junk Rows
**Risk:** Observed directly — the PostgreSQL entry in DRR.csv has an embedded newline in the "Application/Use case" field. Trailing rows may contain empty/junk data.
**Mitigation:** Read with `quoting=csv.QUOTE_ALL`, strip empty rows, validate each row has 3 fields. Load DRR.csv with pandas `read_csv(sep=';', skipinitialspace=True)` and drop rows where Workload Category is NaN.

### 4. NiceGUI File Upload Memory Limits
**Risk:** Large RVTools exports (10k+ VMs) can be 50-100MB. NiceGUI default upload limit may reject them. Full file loaded into memory.
**Mitigation:** Configure `ui.upload(max_file_size=100_000_000)`. Use openpyxl `read_only=True` mode to stream large files. Consider chunked reading for very large datasets.

### 5. Division by Zero in DRR Calculations
**Risk:** If a workload somehow maps to DRR=0 or if no workload is selected for a VM.
**Mitigation:** Validate DRR > 0 at CSV load time. Default unclassified VMs to "Unknown (Reducible)" with DRR=5. Never allow empty workload selection.

## Moderate Pitfalls

### 6. LiveOptics Wrong File Type Uploaded
**Risk:** LiveOptics ZIP exports contain multiple xlsx files (VMWARE, GENERAL, AIR, PERF). User might upload the wrong one (e.g., GENERAL instead of VMWARE). The main `live-optics.xlsx` is actually the VMWARE export.
**Mitigation:** Detect file type by checking for expected tabs (VMs, VM Performance). Show clear error: "This looks like a LiveOptics GENERAL export. Please upload the VMWARE export instead."

### 7. PDF Generation with French Characters
**Risk:** ReportLab default fonts don't support French accented characters (é, è, à, ç, etc.) or special chars (€, ², etc.).
**Mitigation:** Register a Unicode font (e.g., DejaVu Sans or Noto Sans) at app startup. Bundle font file in Docker image. Test with real French VM names.

### 8. NiceGUI Session State with Multiple Users
**Risk:** If two users upload files simultaneously, their data could leak between sessions.
**Mitigation:** NiceGUI creates isolated state per browser tab by default. Store uploaded DataFrame in `app.storage.tab` or a per-client dictionary keyed by `client.id`. Never use module-level globals for user data.

### 9. Docker Temp File Cleanup
**Risk:** Uploaded xlsx files accumulate in container temp directory, eventually filling disk.
**Mitigation:** Process uploaded file in memory (BytesIO), never write to disk. If disk needed, use tempfile with cleanup. Set Docker tmpfs mount for /tmp.

### 10. Tailwind CSS Conflicts with NiceGUI's Quasar Components
**Risk:** NiceGUI uses Quasar UI framework internally. Tailwind utility classes can conflict with Quasar's own styling (especially for buttons, inputs, tables).
**Mitigation:** Use Tailwind for layout (flex, grid, spacing, colors) but let Quasar handle interactive components (buttons, selects, tables). Test visual output with both frameworks active.

## Minor Pitfalls

### 11. vInfo Tab Naming in RVTools
**Risk:** Tab might be named "vInfo" or "tabvInfo" depending on export method.
**Mitigation:** Try both names, fall back to first sheet if neither found.

### 12. VMs with Zero Storage
**Risk:** Template VMs, powered-off VMs with no disks → Provisioned = 0 MiB.
**Mitigation:** Filter out VMs with Provisioned ≤ 0. Show count of filtered VMs in UI.

### 13. Duplicate VM Names
**Risk:** Multiple VMs can share the same name (different clusters, datacenters).
**Mitigation:** Use VM Name + Datacenter/Cluster as composite key, or just display all rows (user will see duplicates in the table).

### 14. CSV Encoding Issues
**Risk:** LiveOptics CSV exports may use different encodings (UTF-8, UTF-8-BOM, Latin-1).
**Mitigation:** Try UTF-8 first, fall back to Latin-1. Use `chardet` for detection if needed.

### 15. openpyxl read_only Mode Limitations
**Risk:** `read_only=True` doesn't support some features (merged cells, cell styles). Some RVTools exports use merged cells in headers.
**Mitigation:** Try `read_only=True` first, fall back to normal mode if header parsing fails.

### 16. Customer Data in Logs
**Risk:** VM names, hostnames, IPs in uploaded files are customer-confidential. Logging DataFrame content would leak PII.
**Mitigation:** Never log DataFrame contents. Log only metadata (row count, column names, file size). Sanitize error messages.

### 17. Large VM Counts Impact UI Performance
**Risk:** 5000+ VMs in a single export → AG Grid in NiceGUI may lag with editable cells + multi-select dropdowns.
**Mitigation:** Enable AG Grid pagination (50-100 rows per page). Consider server-side row model for very large datasets.
