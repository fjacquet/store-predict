# Pitfalls Research — StorePredict v4.0: Compute Sizing, Health Checks, Per-VM IOPS, AG Grid UX

**Domain:** Adding compute sizing, health checks, per-VM IOPS display, and AG Grid UX improvements to an existing NiceGUI/pandas VMware sizing tool
**Researched:** 2026-02-22
**Confidence:** HIGH (most pitfalls verified against live codebase inspection + NiceGUI community discussions + official AG Grid docs)

---

## Critical Pitfalls

### Pitfall 1: AG Grid Row Grouping Requires Enterprise — NiceGUI Only Ships Community

**What goes wrong:**
A developer designs the VM grid grouped by workload category (the obvious UX for "group by workload") and writes `rowGroupPanelShow` or `groupDefaultExpanded` AG Grid options. The grid silently fails or throws a JavaScript error in the browser console: `ag-grid-enterprise has not been loaded`. NiceGUI's built-in `ui.aggrid` bundles AG Grid Community edition only. This is a confirmed limitation in NiceGUI discussions as of 2024.

**Why it happens:**
AG Grid's row grouping, pivot, and tree data features are Enterprise-only. The NiceGUI documentation does not prominently flag this. Developers see grouping in the AG Grid docs and assume it is universally available.

**How to avoid:**
Implement "grouping" as a pure-Python filtering approach: maintain a category filter chip set (`ui.chip_set` or `ui.select`) above the grid, then re-render grid rows in-place using `grid.run_grid_method('setGridOption', 'rowData', filtered_rows)`. This achieves the grouping UX without Enterprise. The third-party `nicegui-aggrid-enterprise` package exists but adds a paid license dependency — avoid for this internal tool.

**Warning signs:**

- Planning documents use the phrase "group by workload" without noting the Enterprise constraint
- Any `rowGroup: true` appears in column definitions
- Browser console errors about enterprise modules not loaded

**Phase to address:**
Grid UX phase — first task, before any column definitions are written.

---

### Pitfall 2: `CANONICAL_COLUMNS` Is the Schema Contract — Columns Dropped at Return

**What goes wrong:**
Both `parse_rvtools` and `_build_liveoptics_df` end with `return result[CANONICAL_COLUMNS]`. If a developer adds a new column to the parser result DataFrame without also adding it to `CANONICAL_COLUMNS` in `columns.py`, the column is silently dropped on return. Downstream code that tries to read it from the session DataFrame gets `KeyError` at runtime — only triggered when a user uploads a file, not in unit tests that mock data.

**Why it happens:**
`CANONICAL_COLUMNS` acts as a whitelist schema enforcer. Developers add columns to the parser but forget to register them in the central list. The column exists during parsing but is stripped at the final return statement.

**How to avoid:**
Before adding any new column: add it to `CANONICAL_COLUMNS` in `columns.py` first, then handle it in both `parse_rvtools` AND `_build_liveoptics_df`. Write a test that parses a real sample file and asserts the new column is present and non-null in the returned DataFrame. Note: `num_cpus` and `memory_mib` are already in `CANONICAL_COLUMNS` and already parsed by both parsers — they just are not displayed in the grid. The Compute Sizing page does NOT need parser changes, only a new page reading from session state.

**Warning signs:**

- A column appears correctly during parsing unit tests but is `None`/missing in the session-loaded DataFrame
- `KeyError` errors triggered during upload but not in isolated unit tests
- A column was added to one parser (RVTools) but not the other (LiveOptics path)

**Phase to address:**
Compute Sizing phase (ingestion verification step). Confirm `num_cpus` and `memory_mib` round-trip through session state before building the compute page UI.

---

### Pitfall 3: Session State Round-Trip Corrupts Typed Data — NaN, bool, int Become Unreliable

**What goes wrong:**
`save_session_data` converts the DataFrame to `list[dict]`, replacing `float('nan')` with `None` for JSON safety. When the Compute Sizing page reads `num_cpus` from session, it may find `None` (was NaN), `0` (legitimate zero), or a float (was int if JSON coerced it). A compute formula like `total_vcpus = sum(row['num_cpus'] for row in rows)` crashes on `None + int`. Memory values stored as float may return as int if the original value was a whole number.

**Why it happens:**
JSON serialization collapses Python numeric types. `pandas.to_dict` emits `float('nan')` which JSON cannot represent, so the NaN-to-None conversion in `save_session_data` is correct — but every consumer must handle `None`. Additionally, `memory_mib` uses the alias `"Memory MB"` which could be in MB rather than MiB depending on the RVTools version, creating silent unit errors.

**How to avoid:**
Always use `pd.to_numeric(val, errors='coerce').fillna(0)` when reading compute columns from session. Verify units: add a sanity check that flags if `memory_mib` values are suspiciously small (< 64 MiB for a production VM) or suspiciously large, which would indicate a unit mismatch.

**Warning signs:**

- Compute totals return `None` or `NaN` for some VMs
- Memory numbers are wrong by a factor of 1024 (unit mismatch)
- `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`

**Phase to address:**
Compute Sizing page — validate all numeric reads from session with explicit null-safe coercion.

---

### Pitfall 4: `getRowId` Uses VM Name — Duplicate Names Cause Silent Edit Corruption

**What goes wrong:**
The existing AG Grid uses `":getRowId": "params => params.data.vm_name"` — VM name is the row identity key. The `cellValueChanged` handler updates the session DataFrame using VM name as a lookup key. If two VMs have the same name (common in RVTools exports that include templates, clones, or multi-datacenter environments), `getRowId` produces duplicate keys. AG Grid logs warnings, and edits to one VM silently update the wrong row in session state. Adding per-VM IOPS also exposes the join ambiguity: `perf_df.merge(result, on='vm_name', how='left')` produces duplicate rows for repeated names.

**Why it happens:**
VM names are not guaranteed unique in VMware exports. RVTools includes templates (`is_template = True`) and powered-off clones that share base names. The existing classification pipeline works without uniqueness because it processes all rows independently. IOPS join and grid editing both require uniqueness.

**How to avoid:**
Add a stable integer `row_index` column during ingestion (position in the parsed DataFrame) and update `getRowId` to use it: `":getRowId": "params => String(params.data.row_index)"`. For the IOPS merge, deduplicate `perf_df` on `vm_name` before merging (take max IOPS for duplicates). Add a test with a synthetic DataFrame containing duplicate VM names to verify merge produces exactly the same row count as input.

**Warning signs:**

- AG Grid browser console warning: "Duplicate id 'VM-NAME' detected from getRowId callback"
- IOPS values appear on wrong VMs after upload
- Row count after merge exceeds input row count (`len(result_after_merge) > len(original)`)

**Phase to address:**
Per-VM IOPS phase (must fix before Grid UX work, as Grid UX depends on correct row identity).

---

### Pitfall 5: Health Check Must Read Session State, Not Re-Run Classification

**What goes wrong:**
A developer builds the Health Check / Concerns page by re-running `classify()` on VM data. This creates a second classification pass, which may produce different results if the user has edited workload assignments in the Review grid. The health check then reports "Unknown" VMs that the user already reclassified, and flags DRR concerns based on stale data. The pre-sales engineer looks incompetent presenting a health check that contradicts the review they just completed.

**Why it happens:**
It is tempting to treat health check as a pure pipeline analysis stage that feeds the same input as classification. The correct design: health check reads from `load_session_data()` (which contains the user-edited DataFrame) and derives concerns from current state.

**How to avoid:**
The Health Check page must always call `df = load_session_data()` as its first data step. Never import `classify()` or `parse_rvtools()` into the health check page. Run concern-detection logic on the already-classified, user-edited DataFrame. The file is not stored in session — only the processed records are — so re-parsing is not even possible without re-upload.

**Warning signs:**

- Health check shows "Unknown" VMs that the user fixed in the Review page
- The health check page imports anything from `pipeline/classification.py` or `pipeline/parsers/`
- Concern count differs from what the Review grid shows for "Unknown Reducible" VMs

**Phase to address:**
Health Check page — enforce session-as-source-of-truth from the first line of the page function.

---

### Pitfall 6: Compute Sizing Includes Powered-Off VMs and Templates — Inflates Host Count

**What goes wrong:**
The Compute Sizing page sums all vCPUs from the DataFrame including powered-off VMs, templates, and VMs with 0 vCPUs. This inflates the total vCPU count and produces more ESXi hosts than needed — embarrassing the pre-sales engineer when the customer asks why 40% of their VMs "don't exist in production."

**Why it happens:**
Raw RVTools exports include all VMs regardless of power state. The existing parser populates `is_powered_on` (from the Powerstate column) and `is_template` (from the Template column). Both fields are in `CANONICAL_COLUMNS` and survive session round-trip. The compute calculation will naturally include all rows unless explicitly filtered.

**How to avoid:**
Before compute sizing calculations, filter to `is_powered_on == True` and `is_template == False`. Expose a UI toggle "Include powered-off VMs" (default: off) with a warning tooltip. Log the count of excluded VMs so users see what was filtered. Display `"Sizing based on N powered-on VMs (M powered-off excluded)"` prominently.

**Warning signs:**

- Compute page host count seems very high relative to the customer's reported environment size
- The total vCPU count exactly matches `len(df)` × average vCPU — no filtering occurred
- Templates appear in the VM count on the compute page

**Phase to address:**
Compute Sizing logic — add the filter step as the first operation, test with a fixture that includes powered-off VMs and templates.

---

### Pitfall 7: i18n Keys Added to One Locale File But Not Both

**What goes wrong:**
New pages (Compute Sizing, Health Check) add 20-30 new translation keys. The developer adds them to `fr.yaml` (primary locale) but forgets `en.yaml`. When a user switches to English, `t("compute.title")` returns the raw key string `"compute.title"` rather than raising an exception — `python-i18n` silently falls back to the key on missing translations. The bug is invisible during development unless the EN locale is explicitly tested.

**Why it happens:**
`python-i18n` silently falls back to returning the key when a translation is missing. There is no CI check that both locale files contain identical key sets. With French as the primary locale, developers write French first and may not notice the EN file is behind.

**How to avoid:**
Add a pytest test that loads both `en.yaml` and `fr.yaml`, flattens their key sets, and asserts `set(en_keys) == set(fr_keys)`. This is a trivial YAML load and set comparison. Run it as part of the existing test suite so it blocks CI if keys diverge.

**Warning signs:**

- UI shows key strings like `"compute.host_count"` in English mode
- One locale file is significantly shorter than the other
- New pages were merged without touching both YAML files

**Phase to address:**
Every feature phase. Add the locale parity test to CI before the first new-page PR merges.

---

### Pitfall 8: Stretch Cluster / vMSC Sizing Requires Site Data That RVTools Does Not Reliably Provide

**What goes wrong:**
The Compute Sizing page adds a "Stretch Cluster (vMSC)" toggle. Correct vMSC sizing requires each site to carry 100% of workload capacity. But RVTools does not provide host-to-site assignment — only VM-to-datacenter at the VM level. Many customers have single-datacenter RVTools exports even in stretched environments. Without site data, the compute page silently produces a non-stretched calculation that appears to work but is wrong.

**Why it happens:**
vMSC requires host-level topology awareness. RVTools' `vInfo` tab gives VM-to-datacenter assignment but not host-to-site assignment. The `datacenter` column exists in `CANONICAL_COLUMNS` at the VM level, but for vMSC the question is which hosts are at which site — not which VMs.

**How to avoid:**
When the vMSC toggle is active, check whether `datacenter` values in the DataFrame contain at least two distinct non-empty values. If not, display a warning: "Stretch cluster sizing requires VMs in two datacenters. Only one datacenter found in this export — showing single-site calculation." When two datacenters exist, treat each as a site and size each site for 100% of total workload.

**Warning signs:**

- The vMSC toggle produces the same result as standard sizing (no difference in host count)
- All VMs have the same `datacenter` value in the session DataFrame
- No datacenter validation logic exists before the vMSC calculation branch

**Phase to address:**
Compute Sizing — vMSC/stretch cluster feature. Build datacenter validation before the calculation branch, not after.

---

### Pitfall 9: `cellValueChanged` Does Not Fire When Cell Value Is Unchanged

**What goes wrong:**
Any state update logic attached to `cellValueChanged` (totals refresh, health check flag update, filter state sync) silently fails when a user clicks the same workload classification twice (no actual change). AG Grid Community v23+ only fires `cellValueChanged` on actual value changes. Reactive UI elements driven by this event go stale without any error.

**Why it happens:**
AG Grid changed this behavior in v23 — `cellValueChanged` used to fire on every edit stop, now only on actual value change. The NiceGUI `ui.aggrid` inherits this behavior. The existing `vm_table.py` uses `on("cellValueChanged", ..., args=["colId", "data", "newValue"])` which is correct for the current use case but fragile for new dependent state.

**How to avoid:**
Use `cellEditingStopped` for actions that must run on every edit attempt regardless of value change. For reactive grid updates (updating totals when a classification changes), trigger the update from `cellValueChanged` but also provide a manual "Recalculate" button as a recovery path. Never use `cellValueChanged` as the sole trigger for critical state updates.

**Warning signs:**

- Totals or health check flags do not update when a user re-selects the same workload category
- A developer uses `on("cellValueChanged", ...)` for filtering, search highlighting, or concern re-computation
- Reactive state updates only when a value actually changes, not when editing stops

**Phase to address:**
Grid UX improvements phase — document the event model in the component before implementing search/filter.

---

### Pitfall 10: LiveOptics IOPS "Adding Peaks" Inflates Requirements by Up to 40%

**What goes wrong:**
The per-VM IOPS column shows each VM's `peak_iops`. If a pre-sales engineer sums all peak IOPS to get a "total storage IOPS requirement," the number can be 30-40% higher than the true concurrent peak. All VMs are never at peak simultaneously. This leads to over-sizing PowerStore arrays and losing deals on price. LiveOptics' own documentation explicitly flags this as a known methodology issue.

**Why it happens:**
LiveOptics captures per-VM peaks at different points in time. The existing codebase already uses `iops_8k_equivalent` (derived from average throughput) for sizing, which is more accurate. Showing raw `peak_iops` in the grid without an explanatory tooltip creates a trap for engineers who add up what they see.

**How to avoid:**
When displaying per-VM IOPS in the grid, show `avg_iops` as the primary column and `peak_iops` as secondary (or hidden by default). Add `headerTooltip` in the AG Grid column definition explaining that peaks are not concurrent. The capacity calculation already uses average-based metrics — do not change the calculation, only add the display with appropriate context. Add a health check flag if `sum(peak_iops)` across all VMs is more than 2x the `iops_8k_equivalent` aggregate — this signals a very spiky environment.

**Warning signs:**

- The grid shows only `peak_iops` with no `avg_iops` column
- No disclaimer or tooltip on IOPS columns
- The IOPS total visible in the grid does not match the IOPS number used in the calculation summary

**Phase to address:**
Per-VM IOPS phase — design column headers and tooltips before grid implementation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode host specs (cores, RAM per host) for compute sizing | Faster to ship | Every customer uses different hardware; tool becomes wrong for most environments | Never — always expose as editable input fields with sensible defaults |
| Access `app.storage.tab["new_key"]` directly in page code | Less boilerplate | Key typos cause silent None returns; impossible to refactor key names safely | Never — add typed getter/setter helpers in `state.py` for every new session key |
| Copy-paste `vm_table.py` for compute page column layout | Faster initial development | Two diverging AG Grid configurations; bug fixes in one don't apply to the other | Never — extend `create_vm_table()` with optional column parameters |
| Skip `is_powered_on` filter in compute sizing "for now" | Simpler code | Over-sized compute recommendations that embarrass pre-sales | Never |
| Add health check rules as ad-hoc if/else in the page function | Fast to prototype | Rules become untestable; impossible to add new rules without touching page code | Prototype only; extract to `pipeline/concerns.py` before merge |
| Use `functools.cache` on health check results | Performance gain | Health check returns stale results after user edits workload in Review page | Never — health check must read live session state each render |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| AG Grid + NiceGUI locale | Using the `localeText` option before the locale CDN script has loaded | Use `defer` attribute on the `<script>` tag (already done in `vm_table.py`) and verify locale fires after grid initialization |
| AG Grid + NiceGUI event args | Passing no `args=` filter to `grid.on()` — AG Grid event objects include GridContext with circular references that crash NiceGUI's JSON serialization | Always specify `args=["colId", "data", "newValue"]` or the minimal set needed (existing pattern in `vm_table.py`) |
| pandas `merge` + duplicate VM names | Left join produces more rows than input when `vm_name` is not unique | Always assert `len(result) == original_len` after merge in tests; deduplicate `perf_df` on `vm_name` first |
| `app.storage.tab` + new page | Adding new session keys directly in page code | Add typed getter/setter helpers to `state.py` for every new session key; never access `app.storage.tab["key"]` with raw string keys in page code |
| ReportLab PDF + new compute/health data | Testing PDF content by searching for text strings in raw bytes | Use the existing pattern: compare FR vs EN PDF byte output; never use `b"text" in pdf_bytes` |
| i18n `t()` + loop variable name | Using `t` as a loop variable shadows the `t()` import | Use `wt`, `entry`, or `item` as loop variables (existing convention documented in CLAUDE.md) |
| NiceGUI `ui.refreshable` + AG Grid | Wrapping AG Grid in a `@ui.refreshable` function causes full grid re-creation on every state change, destroying row selection and sort state | Use `grid.run_grid_method('setGridOption', 'rowData', new_rows)` to update data in-place |
| Health check page + session navigation | Navigating to health check before uploading causes unhandled AttributeError on `df` operations | Every new page must start with `df = load_session_data(); if df is None: show_upload_prompt()` — follow the exact pattern in `review.py` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Health check scans all VMs on every page render | Concerns page has visible render lag for large datasets | Pre-compute concern flags once and cache in session; invalidate cache in `save_session_data` | At ~300+ VMs |
| AG Grid with 1000+ rows and floating filters active | Floating filter typing has visible input lag | Add `filterParams: { debounceMs: 300 }` to all column definitions that use floating filters | At ~500+ rows |
| Compute page re-reads session DataFrame on every reactive toggle change | Interactive toggles (vMSC, HA ratio) cause perceptible recalculation delay | Cache the DataFrame in a page-scoped variable; do not call `load_session_data()` inside every reactive callback | At ~500+ VMs |
| Per-VM IOPS merge creates duplicate rows | Row count silently doubles for customers with duplicate VM names | Assert row count equality after every merge; deduplicate before merge | Any export with 1+ duplicate VM name |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging VM names, vCPU counts, or RAM values in compute sizing | Customer data exposure in Docker logs | Follow existing `logging_config.py` pattern: log counts and format strings only, never DataFrame contents or VM identifiers |
| Exposing compute parameters (HA ratio, overcommit ratio) as URL query params | Session data pollution if user shares link; param tampering | Store all compute settings in `app.storage.tab` via typed helpers in `state.py`, not URL params |
| Health check page does not validate session data exists | Unhandled `AttributeError` if user navigates to `/concerns` before uploading | Every new page must begin with `df = load_session_data(); if df is None:` guard — no exceptions |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Compute page shows host count with no visible inputs | Pre-sales engineer cannot adapt for customer's hardware; numbers appear authoritative but may be wrong | Always show assumed host specs (cores/socket, RAM/host, overcommit ratio) as editable fields with sensible defaults; show "Calculate" button |
| Health check page lists all concerns as red errors | Users dismiss the page as crying wolf if minor issues are flagged as critical | Use three severity levels: Critical (red), Warning (yellow), Info (blue); most items are Info |
| Per-VM IOPS column visible for RVTools imports where IOPS is NaN | Users see empty IOPS column and wonder if the tool is broken | Hide IOPS columns when all rows have `source_format == 'rvtools'`; show "Not available for RVTools exports" placeholder |
| Compute sizing auto-calculates on page load | Results appear authoritative even though defaults may not match customer hardware | Show editable inputs panel first; require explicit "Calculate" button click before results appear |
| Health check flags best practice violations for powered-off VMs | Pre-sales looks foolish flagging issues on non-running VMs | Filter all health check analysis to `is_powered_on == True` and `is_template == False` |
| Search field in AG Grid does not survive workload edit | User searches for a VM, edits its workload, and search state is lost | Store search/filter state in a page-scoped variable and reapply after cellValueChanged |

---

## "Looks Done But Isn't" Checklist

- [ ] **Compute Sizing page:** Verify `num_cpus` and `memory_mib` are non-zero in the test fixtures after session round-trip — they may be `0` in fixtures created before these columns were populated.
- [ ] **Per-VM IOPS column:** Verify the column is hidden (not just empty) when the source is RVTools — check `source_format` field, not whether values are NaN.
- [ ] **Health Check page:** Verify concerns re-compute after a user edits workload in the Review page and navigates back to Health Check. Test with a session round-trip, not a unit test.
- [ ] **AG Grid search/filter:** Verify that the `selectAll: "filtered"` mode works correctly when a text filter is active — test with actual filter state, not just open grid.
- [ ] **i18n parity:** Run a locale key parity check before each phase merges. Both `en.yaml` and `fr.yaml` must have identical key sets.
- [ ] **vMSC toggle:** Verify that switching the toggle back to "standard" mode resets the host count correctly — reactive state with a two-branch toggle is a common source of stale state.
- [ ] **PDF report with compute data:** Verify any new compute/health-check data added to PDF is tested with FR-vs-EN byte comparison, not text search.
- [ ] **New session keys:** Verify all new `app.storage.tab` keys have typed helpers in `state.py` — no raw string key access in page code.
- [ ] **Powered-off VM filter:** Verify the compute page displays the count of excluded powered-off VMs and templates prominently.
- [ ] **getRowId uniqueness:** Verify that the grid does not log duplicate ID warnings in the browser console when a customer file with duplicate VM names is uploaded.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| AG Grid Enterprise features built before discovering Community limitation | HIGH | Redesign grouping as client-side filter toggles; may require full grid component rewrite |
| `CANONICAL_COLUMNS` mismatch discovered after session state is in production | MEDIUM | Add migration shim in `load_session_data()` that back-fills missing columns with defaults using `df.get(col, default)` |
| i18n key parity gap discovered after several phases | LOW | Run a one-time script to find missing keys, add placeholder translations, fix in next PR |
| Health check reading stale classification discovered late | MEDIUM | Refactor health check to load from session; requires health check logic to be stateless with respect to the raw file |
| `getRowId` duplicate key issue found in production | HIGH | Add `row_index` column during ingestion (zero-impact to other pages), update `getRowId` in `vm_table.py` |
| vMSC sizing producing wrong results due to missing site data | LOW | Add datacenter validation + warning banner; `datacenter` column already parsed and in session |
| IOPS column causing pre-sales to over-size arrays | MEDIUM | Add `avg_iops` as primary column, move `peak_iops` to secondary; add tooltip; no calculation change needed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| AG Grid row grouping requires Enterprise | Grid UX phase (first task) | AG Grid Community feature list reviewed before column definitions are written |
| `CANONICAL_COLUMNS` contract | Compute Sizing (ingestion verification) | Test: `parse_rvtools` returns `num_cpus` and `memory_mib` non-zero for existing sample files |
| Session state round-trip corrupts typed data | Compute Sizing page | Test: reads from session return `int`/`float` not `None` for all compute columns |
| `getRowId` duplicate VM name corruption | Per-VM IOPS phase (before Grid UX) | Test: fixture with duplicate VM names; assert merge row count equals input row count |
| Health check must read session, not re-run pipeline | Health Check page (first implementation) | Integration test: upload → classify → edit classification → navigate to health check → verify concern reflects edit |
| Powered-off VMs inflate compute totals | Compute Sizing logic | Unit test: mixed powered-on/off VM fixture; verify only powered-on VMs contribute to totals |
| i18n key parity | Every feature phase | CI test: `set(en_keys) == set(fr_keys)` in pytest suite |
| vMSC requires site-aware data | Compute Sizing vMSC branch | Test: single-datacenter fixture; verify warning is shown and calculation degrades gracefully |
| `cellValueChanged` does not fire on unchanged value | Grid UX phase | Test: set workload to same value; verify totals correct after the no-op edit |
| IOPS peak sum methodology misleads pre-sales | Per-VM IOPS phase | Manual review of column headers and tooltips by a pre-sales stakeholder before merge |
| Compute page auto-calculates before inputs set | Compute Sizing UX | Manual test: navigate to compute page; verify no host count is shown before user clicks Calculate |

---

## Sources

- NiceGUI AG Grid discussion — row grouping Enterprise limitation: <https://github.com/zauberzeug/nicegui/discussions/3182>
- NiceGUI AG Grid discussion — `cellValueChanged` event issues: <https://github.com/zauberzeug/nicegui/discussions/2887>
- NiceGUI AG Grid discussion — event serialization pitfalls: <https://github.com/zauberzeug/nicegui/discussions/2298>
- NiceGUI AG Grid discussion — filter timing and set column filter: <https://github.com/zauberzeug/nicegui/discussions/2805>
- AG Grid — community vs enterprise features: <https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise/>
- AG Grid — `cellValueChanged` only fires on actual value change (v23+): <https://ag-grid.zendesk.com/hc/en-us/articles/360016352372>
- LiveOptics — IOPS methodology (Time Aligned Aggregation vs Adding Peaks): <https://support.liveoptics.com/hc/en-us/articles/229590507-Live-Optics-Basics-IOPS>
- LiveOptics — VM Performance data documentation: <https://support.liveoptics.com/hc/en-us/articles/360060070213>
- RVTools — vCPU/RAM analysis methodology for ESXi sizing: <https://sizing-workshop.readthedocs.io/en/latest/datacollection/rvtools/rvtools.html>
- VMware vMSC — stretch cluster sizing considerations (VCF): <https://knowledge.broadcom.com/external/article/417356>
- NiceGUI — storage scoping (tab vs browser vs user): <https://nicegui.io/documentation/storage>
- StorePredict codebase — `columns.py`, `rvtools.py`, `liveoptics.py`, `vm_table.py`, `state.py`, `review.py` (live inspection 2026-02-22)

---

*Pitfalls research for: StorePredict v4.0 — compute sizing, health checks, per-VM IOPS, AG Grid UX improvements*
*Researched: 2026-02-22*
