# Changelog

All notable changes to StorePredict are documented here.

## [Unreleased]

## [v9.1.0] - 2026-05-22

Adds application-aware classification rules so estates that name VMs by application
(rather than by `SQL*/ORA*/VDI*` product tokens) are classified accurately instead of
collapsing into the `File / General Purpose` size-reroute floor. Derived from a real
Valais-canton RVTools export (791 VMs, 948.8 TiB) where 90% of capacity previously sat in
one bucket. Optimised for **accurate & defensible** sizing — see [ADR-081](adr/081-customer-app-classification-rules.md).

### New / extended classification rules

- **SAP application components** (`saperp`, `sapnwg`, `sapbobi`, `sapbods`, `sapbpc`,
  `sapads`, `sapccm`, `sapsom`, `sapcua`, `sapbcom`, `sapenow`, `sapcockpit`, `saplicenses`,
  `sapfront`) → `Database / SAP Traditional (R/3 / ECC)` (5:1). HANA DB tiers (`saphdb*`)
  keep `SAP HANA(S4)` (2:1); `sapmssql` keeps `Microsoft SQL`.
- **Live mail** (`\bMAIL\b`, e.g. `mail-p01`) → `Email` (2:1). **Mail archive** (`mailarch`)
  and **video management** (`videomgmt`) → `File / Archive` (1:1, incompressible media).
- **OpenShift/Kubernetes nodes** (`worker1`, `master1`, `bootstrap`) → `Containers` (2:1),
  start-anchored so `opsmaster-*` is not misread as a node.
- **DMS / ECM / capture** (Kendox, AutoStore, YouDoc, OpenText `otrecm`, `docpro`, `^ecm`) →
  `File / Content Servers`; **Artifactory / CICD** → `File / Developer Workspaces (DevOps)`.
- **Monitoring** (`^monitor`) → `Logging - Analytics` (1.5:1).
- **Cantonal domain controllers** (`infradc`, `jusdc`, `infrapoldc`, `exploitdc`) →
  `Virtual Machines`; prefix-qualified so the Citrix Delivery Controller `ddc`/`ctxddcpol`
  is excluded.
- **Identified app servers / appliances** (Abacus ERP, Evolveum midPoint, identity
  metadirectory, Messerli, Talend, Superna Eyeglass) → `Virtual Machines` (5:1).

### Behaviour

- On the reference file, rule-matched VMs rise 100 → 358 and the generic `File / General
  Purpose` bucket drops 857 → 525 TiB. Weighted DRR 2.02 → 2.10:1 (required 470.1 → 452.2 TiB).
- Unidentified bespoke apps deliberately remain on the ADR-080 ≥100 GiB `File / General
  Purpose @ 2.0` reroute floor — no 5:1 is claimed on inventory that cannot be defended.
- All rules reference existing `DRR.csv` entries; no reference rows added.

### Tests

- `tests/test_classification.py::TestCustomerAppPatterns` — 15 tests (positive cases plus the
  critical negatives: HANA/SQL not stolen, `opsmaster` not OpenShift, `ddc` not a DC, bespoke
  apps stay at the floor). Full suite: 651 passed.

## [v9.0.2] - 2026-05-20

Retires the synthetic `Virtual Machines / Large data-bearing (>100 GiB unknown)` category.
Large-unknown VMs (≥100 GiB, `os_fallback`/`default`) now route to the existing canonical
`File / General Purpose` entry. The classifier emits only categories that exist in the
reference DRR table.

### Behaviour change (labels only — sizing unchanged)

- Size-aware reroute target changed from `Virtual Machines / Large data-bearing (>100 GiB
  unknown)` to `File / General Purpose`. Both are DRR 2.0, so required-capacity output is
  identical — only the displayed category/subcategory changes.
- The synthetic `Large data-bearing` row is removed from `src/store_predict/data/DRR.csv`
  (43 → 42 entries).
- Provenance preserved: rerouted VMs keep `rule_name = "Large generic (>=100 GiB)"` and
  their original `os_fallback`/`default` confidence, so they stay distinguishable from
  genuinely-classified File/General Purpose servers.

### Docs

- ADR-080 gains a second amendment recording the target change.
- `docs/architecture.md` and `docs/adr/index.md` updated.

### Tests

- `test_drr_table.py`: entry count 43 → 42; `test_large_data_bearing_drr` replaced by
  `test_file_general_purpose_drr`.
- Reroute tests in `test_classification.py` assert `File / General Purpose`.
- `test_real_customer_baseline.py` counts rerouted VMs by `classification_rule`.

## [v9.0.1] - 2026-05-20

Calibration of the v9.0.0 size-aware reroute. The `Virtual Machines / Large data-bearing
(>100 GiB unknown)` floor is lowered from **2.5:1 to 2:1 (DRR=2.0)** — a more conservative,
defensible ratio for inventory we couldn't classify by signature. ADR-080 already flagged
this as a known tuning lever ("some customers may want 2:1 or 3:1").

### Behaviour change (re-run sizings to see new numbers)

- `Virtual Machines / Large data-bearing (>100 GiB unknown)` DRR: **2.5 → 2.0** in
  `samples/DRR.csv` and `src/store_predict/data/DRR.csv`. Required capacity for affected
  large-unknown VMs rises ~25% (`provisioned / 2.0` vs `provisioned / 2.5`). The reroute
  logic, the 100 GiB threshold, and the subcategory name are unchanged.

### Docs

- ADR-080 gains a dated amendment recording the 2.5 → 2.0 change (the original v9.0.0
  decision text and impact figures, computed at 2.5, are preserved as history).
- `docs/architecture.md` updated to state DRR=2.0.

### Tests

- `tests/test_drr_table.py::test_large_data_bearing_drr` now asserts 2.0.

## [v9.0.0] - 2026-05-01

Major version bump — addresses the **single biggest sizing risk** in StorePredict: unclassified VMs landing in the generic `Virtual Machines / VMware-Hyper-V-KVM…` bucket at DRR=5 by default. Audit of two real customer RVTools exports showed 64–67% of inventory in this bucket, holding 330+ TiB of provisioned data. A blind 5:1 default predicts ~66 TiB of PowerStore need; a defensible 2.5:1 floor on unknown data-bearing inventory predicts ~132 TiB. The pre-existing default systematically undersized arrays by tens of TiB on real customer projects.

### Behaviour change (re-run sizings to see new numbers)

- **Size-aware reroute (ADR-080):** unknown VMs (`os_fallback` or `default` confidence) with `provisioned_mib >= 100 GiB` now reroute to a new DRR subcategory `Virtual Machines / Large data-bearing (>100 GiB unknown)` at **DRR=2.5**. Specific app rules (`rule_match`) are never rerouted — Dell-validated DRRs on Oracle / SQL / SAP / etc. stay intact at any size.
- The reroute is implemented as post-processing in `classify_dataframe()`. The `RuleRegistry` itself stays a pure pattern engine.
- `LARGE_VM_THRESHOLD_MIB = 100 * 1024` is a single constant in `pipeline/classification.py` — easy to tune.

### Added

- New DRR subcategory `Virtual Machines / Large data-bearing (>100 GiB unknown)` at 2.5 in `samples/DRR.csv`.
- **3 missed pattern fixes** identified during the same audit:
  - `INSIGHTIQ` → Database / PostgreSQL (Dell PowerScale InsightIQ ships embedded Postgres).
  - `SECDB` → Database / Microsoft SQL (customer convention for Security Database).
  - `FORTIADC` substring + `FORTIA\d` regex → Logging - Analytics / FortiNet… (catches FortiADC short-host names like `SPHFRFORTIA01`).
- ADR-080 documents the size-based reroute design (post-processing vs in-rule vs DRR-multiplier).
- 10 new tests in `tests/test_classification.py::TestV900PatternsAndSizeAware` covering the threshold boundary, no-reroute on small VMs, no-override on rule_match, missing-column safety, and the 3 new patterns.
- New baseline regression `test_v900_large_databearing_takes_unknown_volume` in `tests/test_real_customer_baseline.py`.

### Real-file impact (Jan 2026 customer, 570 powered-on VMs)

| Bucket | v8.3.2 | **v9.0.0** |
|---|---:|---:|
| Generic `Virtual Machines / VMware-Hyper-V-KVM…` (DRR=5) | 365 | **18** (only true OS-only <100 GiB) |
| **`Virtual Machines / Large data-bearing (>100 GiB unknown)` (DRR=2.5)** | 0 | **351** |
| `Database / PostgreSQL` | 6 | 7 (+1 INSIGHTIQ) |
| `Database / Microsoft SQL` | 16 | 21 (+5 SECDB and downstream) |
| `Logging - Analytics / FortiNet…` | 4 | 5 (+1 FORTIA01) |

Sizing prediction on the 351 large-unknown VMs: **66 TiB → 132 TiB** of PowerStore need. Defensible 2.5:1 floor instead of indefensible 5:1.

### Tests

Full suite: 635 passed, 1 skipped (LLM API key). Includes the 10 v9.0.0 tests and the customer-file regression on the May 2026 file (gated by file presence).

## [v8.3.2] - 2026-05-01

Manual rule extensions identified by re-auditing the Jan 2026 customer file (570 powered-on VMs) after the v8.3.1 hotfix landed. Closes 7 specific naming patterns that pre-sales clearly recognises as products but the deterministic ruleset was missing.

### Added

- **Healthcare specialty apps** in the EMR/EHR rule (priority 200): `CARDIO`, `ORAMED`, `EMEDISTA`, `EASYDOSE`, `CODMED`, `DCIMED`, `HEMA`. Routes 17 cardiology / pharma / hematology VMs to `HealthCare / EMR/EHR (Epic, McKesson)` (DRR=3) instead of generic Virtual Machines.
- **SharePoint role tokens** `SPAPP`, `SPWFE` in the File Content Servers rule (priority 340). Routes 8 SharePoint App / Web Front End VMs to `File / Content Servers` (DRR=2). Extends the existing `SPBE`, `SPFE`, `SPOWA`, `SPOFFICE` patterns.
- **Microsoft DFS** (Distributed File System) — new `DFS\d` and `DFS[-_]` regex patterns in the File General Purpose rule (priority 330). Routes 2 file-server VMs to `File / General Purpose` (DRR=2). Pattern requires DFS followed by a digit or separator to avoid matching `PDFs`, `MDFS`, etc.
- **WSUS rule** (priority 315) — routes Microsoft Windows Server Update Services VMs to `Web Servers / Content included` (DRR=1.5). WSUS stores already-compressed `.cab` / `.msu` / `.msi` patches; DRR=1.5 reflects the limited reduction headroom on PowerStore.
- **DWH token** in the Microsoft SQL Page Compressed rule (priority 92) — Data Warehouse VMs route to `Database / Microsoft SQL - Page Compressed` (DRR=2.5) on the convention that DWH workloads typically use SQL columnstore / page compression at the application layer.

### Tests

- 11 new parametrised regression tests in `tests/test_classification.py::TestV832Extensions` covering the 5 new rule extensions, plus a negative-match assertion for the DFS pattern (`PDFSERVER01` must NOT match File). Full suite: 619 passed, 1 skipped.

### Real-file impact (570 powered-on VMs, vs v8.3.1)

| Bucket | v8.3.1 | v8.3.2 |
|---|---:|---:|
| Generic `Virtual Machines` (DRR=5) | 420 | 373 (–47) |
| `HealthCare / EMR/EHR` | 0 | 17 |
| `File / Content Servers` | 4 | 10 |
| `File / General Purpose` | 1 | 3 |
| `Web Servers / Content included` | 17 | 20 |
| `Database / Microsoft SQL - Page Compressed` | 0 | 17 |

## [v8.3.1] - 2026-05-01

Hotfix on top of v8.3.0 that eliminates a critical false-positive in the workload classifier. On a real customer RVTools export (570 powered-on VMs) **375 VMs (66%)** were wrongly tagged `VM Replication / Veeam, Zerto, RP4VM` because the vCenter Annotation field was auto-populated by Veeam with backup metadata like `"Last backup: …; Veeam server: [bkp01]; Job: […]; Repository: […]"`. The classifier's pass-2 description fallback re-tested every rule's `vm_name_patterns` against the description, so the literal word "Veeam" fired the Veeam rule on every backed-up VM — including pure Exchange servers, domain controllers, and 369 others. Same systemic risk applied to any rule whose product token might appear in descriptions.

### Fixed

- **Description fallback is now opt-in per rule** via a new `match_description: bool = False` flag on `ClassificationRule`. Default is OFF, so backup-tool annotations no longer trigger app rules. `pipeline/classification.py`.
- **11 OVA-annotation signature rules opted in** with `match_description=True`: Cisco UC (250), Nutanix CVM (294), Dell PowerProtect (299), vCenter / vSAN Witness (396), FortiDeceptor (401), BeyondTrust / Bomgar (430), Tenable / Nessus (435), NetApp OnCommand UM (450), Horizon3.ai NodeZero (460), exotrack (465). Every other rule (VM Replication, Email, Database, VDI, Web Servers, …) defaults to OFF.

### Added

- **`EXCH` short-token in Email rule (priority 210)** — covers the customer's `SPHFREXCH01-04` / `SPRFSMEXCH01-02` naming convention. Specific enough to not false-match `APEX`, `EXT`, `EXOS`, `NEXT`.
- **5 regression tests** covering the bug, the EXCH short-token, and that the opt-in description signatures (BeyondTrust, Nutanix CVM annotation) still fire correctly.

### Changed

- `tests/test_classification_prefix.py::test_classification_with_description` was renamed to `test_description_does_not_match_non_optin_rule` to match the new semantics.
- `test_classify_dataframe_with_description_column` now also asserts that the BeyondTrust opt-in signature still works alongside generic-description rejection.

### Real-file impact (570 powered-on VMs)

| Bucket | Before (v8.3.0) | After |
|---|---:|---:|
| `VM Replication / Veeam, Zerto, RP4VM` | 375 | 0 |
| `Email` | 2 | 8 (4 EXCH + 2 EXC1/EXC2 + 2 WITEXC) |
| `os_fallback` confidence | 41 | 418 (correct Windows/Linux fallback) |
| `rule_match` confidence | 529 | 146 (only legit matches) |

Full test suite: 608 passed, 1 skipped.

## [v8.3.0] - 2026-05-01

Smart-matching feature release: the workload classifier now consumes the vCenter folder path as a first-class signal alongside VM name and OS, and ships 17 new rules that close real-world gaps observed on a multi-vCenter customer export (1373 powered-on VMs).

### Added

- **`vm_folder` classification signal** — RVTools `Folder` (and any LiveOptics `Folder`/`Path` column) is now extracted into the canonical schema and passed through `classify_dataframe()`. `pipeline/parsers/columns.py`, `pipeline/parsers/rvtools.py`, `pipeline/parsers/liveoptics.py`.
- **`ClassificationRule.folder_patterns`** — rules can now match on folder regex. `match_mode="all"` enables AND-qualifier semantics (e.g. Nutanix CVM requires both a tight name pattern and `/NTNX CVMs/` folder). Default OR semantics fire on any defined set match. `pipeline/classification.py`.
- **17 new classifier rules** routed to existing DRR.csv categories (zero taxonomy churn):
  - SAP HANA HDB token (priority 109) — catches `*saphdb*` and `\bHDB\d+\b` plus `/HanaDB/` folder → `Database / SAP HANA(S4)` (DRR=2).
  - SAP general folder (175) — `/SAP_*/` non-HANA → `Database / SAP Traditional` (DRR=5).
  - Microsoft Exchange folder (215) — `/EXCH(?:ANGE)?/` → `Email` (DRR=2).
  - Cisco Unified Communications (250) — CUCM, UCCX, CUIC, Finesse, IPCC, CCX, CUC, CER, PCD names + `/UC` folder + "Cisco Unity Connection" annotation → `Web Servers / Content included` (DRR=1.5).
  - Nutanix CVM (294) — `NTNX-` / `_CVM_` / "Nutanix Controller VM" → `VM Replication / Data Domain Virtual Edition (DDVE)` (DRR=1.0). Storage controllers cannot be 5:1 reducible.
  - Dell PowerProtect description (299) → `VM Replication / Veeam, Zerto, RP4VM` (DRR=1.5).
  - Dell PowerFlex SDS k8s (311) — `/PowerFlex` folder + `*pflex*` → `Containers / Kubernetes` (DRR=2).
  - Domain Controller / AAD (320) — `\bDC\d+\b`, `\bAADC?\d*\b`, `\bADDS\b`, `/AD$|/AADC` → `Virtual Machines` (DRR=5).
  - IPAM (325) — `\bIPAM\b` + `/IPAM` → `Web Servers / Content included` (DRR=1.5).
  - Identity / Auth Nevis (330) — `/IAM|/EID|/NEVIS` + `\bnevis\b` → `Web Servers / Content included` (DRR=1.5).
  - vCenter / vSAN Witness annotation (396) → `Virtual Machines`.
  - FortiDeceptor (401) → `Logging - Analytics / FortiNet…`.
  - BeyondTrust / Bomgar annotation (430) → `Web Servers / Content included`.
  - Tenable / Nessus annotation (435) → `Web Servers / Content included`.
  - NetApp OnCommand UM annotation (450) → `Web Servers / Content included`.
  - Horizon3.ai NodeZero annotation (460) → `Web Servers / Content included`.
  - exotrack annotation (465) → `Web Servers / Content included`.
- **Folder column in review grid** — `vm_folder` exposed as a hidden, toggleable AG Grid column. `ui/pages/review.py`, `ui/components/vm_table.py`, locale files (`columns.vm_folder`).
- **Customer-baseline regression test** — `tests/test_real_customer_baseline.py` runs the classifier against a real multi-vCenter dump and asserts SAP HANA, Email, DDVE bucket sizes plus an `os_fallback ≤ 940` ceiling (baseline 1021). Gated by file presence so CI passes when the dump is absent.
- **`scripts/classify_customer_dump.py`** — read-only ad-hoc tool that prints subcategory + confidence distributions for any RVTools/LiveOptics export.

### Changed

- Folder is shown hidden by default in the review grid to avoid widening the layout; users can enable it from the column chooser when investigating misclassifications.

### Tests

- 15 new folder-aware classification tests (qualifier semantics, priority ordering, description-only signatures) and 2 RVTools parser tests for `vm_folder` extraction. Full suite: 603 passed, 1 skipped (LLM fallback test gated on API key).

### Real-file impact (1373 powered-on VMs)

| Bucket | Before | After |
|---|---:|---:|
| `rule_match` confidence | 339 | 542 |
| `os_fallback` | 1021 | 857 |
| SAP HANA(S4) | 0 | 12 |
| Email | 0 | 7 |
| DDVE (Nutanix CVMs at DRR=1.0) | 0 | 6 |
| Containers (PowerFlex k8s) | 0 | 11 |
| SAP Traditional | 0 | 48 |

## [v8.2.2] - 2026-04-20

Bug-fix release correcting a long-standing under-reporting in LiveOptics xlsx ingestion that affected any VM with more than one virtual disk.

### Fixed

- **LiveOptics multi-disk VMs** — `parse_liveoptics_xlsx` now sums per-disk capacities from the `VM Disks` sheet and overrides `provisioned_mib` / `in_use_mib` per VM. Previously only the primary virtual disk from the `VMs` sheet's `Virtual Disk Size (MiB)` was counted, causing severe under-reporting for storage-heavy clusters (e.g. a container cluster with ~11 disks/VM showed ~4 TiB instead of ~40 TiB). Join uses MOB ID with a VM Name fallback. Falls back to VMs-sheet values when the `VM Disks` sheet is absent (older exports, CSV). `pipeline/parsers/liveoptics.py`, `pipeline/parsers/columns.py`.

### Tests

- 9 new tests in `tests/test_liveoptics_vm_disks.py` covering per-VM aggregation, multi-disk regression, metadata preservation, and the VMs-sheet-only fallback path. Full suite: 589 passed, 1 skipped.

## [v8.2.1] - 2026-04-18

Re-release of v8.2.0 with correct artifacts. The `v8.2.0` tag was pushed before the version-bump commit landed on `maincd`, so its GitHub Release shipped wheels/sdists labelled `8.1.0` under a `v8.2.0` tag. No source code changes vs `v8.2.0` — this release simply builds and publishes the same `maincd` tree with the correct `8.2.1` package metadata.

## [v8.2.0] - 2026-04-18

Security and stability release driven by a full code review (semgrep + 5 parallel audits). Closes 7 HIGH findings and 11 Dependabot CVE alerts in `aiohttp` and `nicegui`.

### Security

- **Fail-closed `STORAGE_SECRET`** — `src/store_predict/main.py` now raises `RuntimeError` at startup when `STORAGE_SECRET` is missing outside dev mode. `reload=True` is also gated on `STORE_PREDICT_ENV == "dev"`. The secret itself is never logged.
- **Excel/CSV formula injection (CWE-1236)** — `services/excel_report.py` pipes every string cell through a new `safe_excel_cell` sanitiser that prepends a `'` to values starting with `=`, `+`, `-`, `@`, `\t`, or `\r`. Numeric cells pass through unchanged.
- **ReportLab Paragraph XML injection** — VM-name fields interpolated into PDF `Paragraph(...)` strings (`services/pdf_report.py`) are now escaped via `xml.sax.saxutils.escape`. Prevents malformed-tag crashes and tag-injection from user-controlled VM names.
- **Session archive zip-bomb + path traversal** — `pipeline/session_archive.py` now imports a shared `pipeline/_zip_safety.py` helper enforcing a 100 MB uncompressed cap (`MAX_UNCOMPRESSED_BYTES`) and rejecting traversal components via `safe_member_name`. Same guard applied to `pipeline/zip_extraction.py`.
- **Stricter `.xlsx` magic-byte validation** — `pipeline/validation.py` now requires a `[Content_Types].xml` entry inside the ZIP after the `PK\x03\x04` magic check; plain ZIPs renamed `.xlsx` are rejected.
- **Log hygiene (CWE-532)** — `chunk_upload.py` and `ui/pages/upload.py` no longer log raw filenames. A new `hash_name()` helper in `logging_config.py` logs a 12-char SHA-256 prefix instead.
- **CVE dependency bumps** — `aiohttp 3.13.3 → 3.13.5` (closes trailer-header DoS, UNC SSRF on Windows, multipart-size bypass, duplicate Host headers, DNS-cache DoS, CRLF injection, response splitting, header-injection via null bytes, late multipart size enforcement, cross-origin Cookie/Proxy-Auth leak) and `nicegui 3.9.0 → 3.10.0` (closes filename-sanitisation bypass on Windows). A `[tool.uv] override-dependencies` entry relaxes litellm's frozen-dep `aiohttp>=3.13.3,<3.13.3+` pin — patch releases in the 3.13.x line are ABI-compatible.

### Fixed

- **`merger.vm_name` dtype** — cast to `str` before `.str.strip()` so dual-source merges whose VM names are numeric no longer produce NaN join keys (`pipeline/merger.py`).
- **Hottest-VM only when data exists** — `CalculationSummary.max_vm_peak_iops_name` is now only assigned when `has_performance_data` is true; otherwise empty (`pipeline/calculation.py`).
- **DRR and numeric guards** — `drr <= 0` now logs a warning and falls back to `DEFAULT_DRR` instead of silently using `max(drr, 0.1)` (a 10× capacity over-sizing). Provisioned/in-use MiB coercion via the existing `_safe_float` avoids NaN poisoning the totals.
- **LiveOptics CSV BOM** — parser tries `utf-8-sig` before `utf-8` so Excel-exported CSVs no longer leak a `\ufeff` into the first header (`pipeline/parsers/liveoptics.py`).
- **DB2 false-positive** — the DB2 classification rule is now word-bounded so storage-array hostnames like `DB2500`/`DB2700` no longer misclassify as DB2 databases.

### Changed

- **Thread-safe `CircuitBreaker`** — `pipeline/llm_classifier.py` extracts the module-level breaker globals into a `CircuitBreaker` class with an internal `threading.Lock` and a shared `_call_llm` helper. No public API change.
- **New internal helpers** — `src/store_predict/_sanitizers.py` (escape_xml, safe_excel_cell) and `src/store_predict/pipeline/_zip_safety.py` (MAX_UNCOMPRESSED_BYTES, assert_zip_within_limits, safe_member_name) centralise escape and archive-safety logic.

### Tests

- 571 tests pass (up from 551). New coverage on: startup secret enforcement, merger numeric VM names, calculation guards, Excel formula injection, PDF XML escape, zip-bomb + path-traversal rejection, CSV BOM, DB2 word boundaries, stricter xlsx validation, and `CircuitBreaker` thread-safety + breaker-open code paths for `_call_llm` / `classify_batch_vms` / `classify_single_vm` / `classify_unknown_vms_async`.

## [v8.1.0] - 2026-04-17

### Added

- **Per-VM ignore flag** (Issue #11) — users can now mark individual VMs as "ignored" on the review page via a new checkbox column or the **Mark Ignored** / **Mark Active** bulk buttons. Ignored VMs stay visible (greyed out) on the review page but are excluded from the summary stats, the DRR calculation, and the PDF/Excel report. The flag persists in session storage, survives scope filtering, and follows the established filter-at-the-edge pattern used for datacenter/cluster scope. See [ADR-078](docs/adr/078-per-vm-ignore-flag.md).

### Changed

- **GitHub Actions migrated to Node 24** — all 22 action references in `ci.yml`, `docs.yml`, and `release.yml` repinned to Node 24-compatible versions (checkout v6, setup-python v6, upload-artifact v7, download-artifact v8, docker/* v4–v7, anchore/sbom-action v0.24, softprops/action-gh-release v3, etc.) to resolve the deprecation of Node 20 runtimes on GitHub-hosted runners.
- **Lockfile refreshed** — `uv lock --upgrade` run; dependency graph is now as current as upstream `litellm==1.83.9` allows. litellm's exact pins on aiohttp/click/jsonschema/openai/pydantic/python-dotenv/importlib-metadata transitively block further minor/patch bumps (notably nicegui 3.10.0 which requires aiohttp ≥ 3.13.4).

## [v8.0.0] - 2026-03-26

### Fixed

- **DRR category split** (Issue #5) — `calculate()` now groups by `(category, drr)` tuple instead of `workload_category` alone. VMs with the same workload category but different DRR values (e.g., SQL uncompressed vs SQL encrypted) now produce separate rows in the web UI, PDF, and Excel breakdown table. See [ADR-077](docs/adr/077-drr-category-split-groupby-key.md).

### Added

- **Classification expanded** — New rules reduce Unknown Reducible VM rate:
  - Veritas / NetBackup agents (`VERITAS`, `NETBACKUP`, `NBU`) → VM Replication (priority 298)
  - Generic backup servers (`BACKUP`) → File Archive (priority 360)
  - Network monitoring infrastructure (`NAGIOS`, `ICINGA`, `SOLARWINDS`, `LIBRENMS`, `OPENNMS`) → Logging - Analytics (priority 400)
  - Redis cache VMs (`REDIS`) → Database / MySQL / NoSQL (priority 101)
- **PDF Sankey at 300 DPI** — matplotlib Agg renders at 2083×833 px (500×200 pt canvas), eliminating pixelation at 100% zoom in PDF readers
- **PDF Sankey palette aligned** — 6th color corrected from `#5B8DB8` to `#DEE2E6`, matching the ECharts DELL_PALETTE used in the web UI
- **PDF Sankey legibility** — mid-node category label fontsize 5→6, axis label default 6.5→7

## [v7.2.0] - 2026-03-15

### Changed

- **Compute sizing replaced with PreSizion redirect** — the `/compute` page now links to [PreSizion](https://fjacquet.github.io/presizion/), a dedicated tool with advanced compute, storage, and network sizing. All compute sizing pipeline code, presets CSV, and associated tests have been removed. Session archives silently ignore legacy compute keys on restore. See [ADR-076](docs/adr/076-compute-sizing-removed-presizion-redirect.md).

## [v7.1.5] - 2026-02-26

### Fixed

- **Upload endpoint 422 error** — `Request` was imported inside `TYPE_CHECKING` but `from __future__ import annotations` made FastAPI unable to resolve the type at runtime, causing every upload to silently return HTTP 422. Moved to a runtime import.
- **ZIP extraction too strict** — only accepted files matching the canonical `LiveOptics_*_VMWARE_*.xlsx` pattern inside ZIPs. Now falls back to any `.xlsx` in the archive, supporting RVTools-in-zip and non-standard LiveOptics exports.
- **Silent upload errors** — `IngestionError` during file processing was caught but never logged; added `logger.warning` so validation failures always appear in server logs. Error notifications now persist (`timeout=0`) instead of auto-dismissing.
- **Chunk assembly off-by-one guard** — added `max_end >= total_size` check alongside byte-count comparison to handle potential Content-Range total mismatches from Quasar.

## [v7.1.4] - 2026-02-26

### Fixed

- **Chunked upload for corporate proxies** — files are now uploaded in 2 MB chunks via a dedicated `/api/upload/{token}` endpoint instead of a single large multipart request. This resolves uploads being cut off mid-transfer (~60%) on enterprise networks with proxy timeout limits. A `ui.timer` polls the per-session queue and triggers the pipeline once all chunks are assembled server-side.

## [v7.1.3] - 2026-02-25

### Added

- **Open Sans in Excel report** — all XlsxWriter cell formats now specify `"Open Sans"` (bold/header) or `"Open Sans Light"` (body/numbers), matching PDF report typography.

### Fixed

- **PDF chart labels font** — bar charts, pie chart, and Sankey diagram now render axis/slice labels in Open Sans via `FONT_REGULAR` constant imported from the shared `_fonts.py` module.
- **Rebase artifact** — stray commit-message text left in `pdf_charts.py` line 238 by a rebase conflict caused a `SyntaxError` at runtime; removed.

## [v7.1.2] - 2026-02-25

### Added

- **Open Sans fonts bundled** — `OpenSansLight.ttf` and `OpenSansSemiBold.ttf` (OFL) shipped in `data/`; registered as `AppFont`/`AppFontBd` via `_register_fonts()` with automatic fallback to Vera when fonts are absent (test environments).
- **KPI card strip** — totals section replaced by two rows of brand-blue KPI cards (`_make_kpi_cards`): VMs / CPUs / Memory on row 1, Provisioned / In-Use / Required on row 2. Values use a compact single-unit formatter (`_fmt_kpi_storage`: `"5.2 TiB"` instead of `"5284.0 GiB (5.2 TiB)"`) to prevent wrapping at 17 pt.
- **Page-number footer** — `_draw_footer` draws a `#cccccc` rule and a centred grey page number on every page.
- **Section rules** — 1.5 pt brand-blue `HRFlowable` added after every section heading (Totals, Averages, Performance, Breakdown, Health, Charts, Layout, Findings detail).
- **Health table orphan fix** — health findings summary block wrapped in `KeepTogether` so the heading and severity table always land on the same page.
- **Datastore → VM styled header** — per-datastore VM lists now use a single `Table` per datastore: row 0 is the DS name as a light-blue (`#d0e8f4`) spanning header with brand-blue bold text; rows below are the 3-column VM name grid.

### Changed

- Heading style parent changed from `Heading2` to `Normal` (removes left indent); colour set to `_BRAND_BLUE`; font switched to `AppFontBd` (Open Sans SemiBold).
- Dell logo no longer auto-injected from the bundled asset — logo only appears when the caller explicitly provides bytes.
- All `"Vera"` / `"VeraBd"` literals in `pdf_report.py` replaced by `_FONT_REGULAR` / `_FONT_BOLD` constants.

## [v7.1.1] - 2026-02-25

### Fixed

- **PDF in container**: replaced Plotly + kaleido Sankey with matplotlib Agg backend — kaleido 1.2.0 required a headless browser unavailable in the slim Docker image, causing PDF generation to fail silently. Cubic Bezier sigmoid flow bands rendered via `FigureCanvasAgg` give the same professional appearance without any system dependencies.

### Removed

- `plotly>=5.0` and `kaleido>=0.2` dependencies (replaced by `matplotlib>=3.8`)

## [v7.1.0] - 2026-02-25

### Changed

- **MkDocs navigation clean-up** — individual ADR and Research pages are now
  declared `not_in_nav`; `mkdocs build` is warning-free. Pages are still built
  and fully reachable via their index tables (`adr/index.md`,
  `research/index.md`). Navigation collapses to index pages only, keeping the
  sidebar concise.

### Internal

- GSD planning files updated: v5.0 and v7.0 milestone accomplishments filled in,
  v7.0.x key decisions captured in PROJECT.md, stale Playwright references
  removed, phase directories 27–28 archived to `milestones/v7.0-phases/`.

## [v7.0.7] - 2026-02-25

### Added

- **Automatic dark mode** — the app now follows the browser/OS `prefers-color-scheme`
  setting on first visit. Users who have never set a preference see dark mode automatically
  when their system is in dark mode. Explicit toggle preference is still persisted via
  `app.storage.user` and overrides auto-detection on subsequent visits.

## [v7.0.6] - 2026-02-25

### Changed

- **Single comprehensive PDF** — the layout datastore detail (per-strategy tables with
  DS capacity, utilisation, IOPS, and workload types) is now appended directly to the
  main sizing report PDF. The separate Layout PDF download button is removed; one
  download from the Report page delivers everything.
- **Improved DS detail table formatting** — workload-type column is now word-wrapped
  (no more 30-character truncation); column widths are rebalanced to fill the full A4
  usable width (482 pt).
- **VM lists rendered as compact 3-column tables** — replacing the previous plain
  comma-separated paragraph, making the assignment lists scannable at a glance.

### Removed

- `generate_layout_pdf()` function — superseded by the extended `generate_report_pdf()`.
- Layout PDF download button from the Layout page.

## [v7.0.5] - 2026-02-25

### Performance

- **Docker image ~389 MB smaller** — eliminated the `chown -R appuser:appuser /app`
  layer by creating `appuser` before any `COPY` steps and using `--chown=appuser:appuser`
  on all `COPY` instructions. The venv is now created as `appuser` from the start;
  no ownership fixup layer is needed.

### Changed

- **`pyright` moved to dev dependencies** — it is a static type-checker, not a runtime
  dependency, and should not be installed in production containers.

## [v7.0.4] - 2026-02-25

### Changed

- **PDF charts: matplotlib Sankey replaced by Plotly + kaleido** — the Sankey diagram
  in PDF exports is now rendered by `plotly.graph_objects.Sankey` and exported as PNG
  via kaleido, producing a cleaner, more professional output that closely matches the
  ECharts Sankey visible in the web UI.

### Removed

- **Playwright / headless Chromium removed** — PDF export no longer requires a browser.
  The existing ReportLab path (`pdf_report.py`) is now wired directly to both the
  Report and Layout download buttons. The HTML print routes (`/report/print`,
  `/layout/print`) and the one-time print-session token mechanism are deleted.
- **matplotlib removed** — was only used for the Sankey diagram; replaced by Plotly.

### Added

- `generate_layout_pdf()` public function in `pdf_report.py` — standalone
  layout-recommendations PDF with optional `PlacementConstraints` parameter.

### Dependencies

- **Added:** `plotly>=5.0`, `kaleido>=0.2`
- **Removed:** `playwright>=1.40`, `matplotlib>=3.8`

### Docker

- Image shrinks by **~430 MB** — Playwright Chromium layer eliminated. (ADR-071)

## [v7.0.3] - 2026-02-25

### Dependencies

- **certifi** 2026.1.4 → 2026.2.25
- **fastapi** 0.132.0 → 0.133.0
- **hf-xet** 1.2.0 → 1.3.1
- **litellm** 1.81.14 → 1.81.15
- **mkdocs-material** 9.7.2 → 9.7.3
- **nicegui** 3.7.1 → 3.8.0
- **openai** 2.21.0 → 2.24.0

## [v7.0.2] - 2026-02-25

### Fixed

- **PDF export broken in production container** — Playwright's Chromium was
  installed to `/root/.cache/ms-playwright` (root) but the app runs as `appuser`,
  causing all PDF exports to fail with a browser-not-found error. Fixed by setting
  `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` in the Dockerfile and granting
  world read+execute on that path after install. (ADR-070)

## [v7.0.1] - 2026-02-24

### Performance

- **Docker build time ~5–10 s for code-only changes** (down from 3+ minutes) —
  reordered Dockerfile layers so Python dependencies and Playwright are cached
  separately from source code. Uses `uv sync --frozen --no-install-project` to
  install deps before copying `src/`, BuildKit `--mount=type=cache` for the uv
  package cache, and `UV_LINK_MODE=copy` to suppress hardlink warnings.

## [v7.0.0] - 2026-02-24

### New features

- **Session save & restore** — engineers can save a complete sizing session
  to a portable `.zip` archive and restore it later by re-uploading on the
  Upload page. The archive contains the original uploaded file plus a
  `session.json` snapshot capturing VM list, workload classifications, DRR
  overrides, layout settings, and compute settings. Works with all input
  formats (RVTools, LiveOptics xlsx/csv, dual-source merge).

- **Concerns remediation hints** — every health finding card on `/concerns`
  now shows a concise actionable hint in italic gray text explaining what
  action to take (e.g., "Re-run RVTools after VMware Tools is installed to
  populate OS fields"). All 14 finding types across 13 health checks include
  hints.

- **Concerns PDF export** — new "Export PDF" button on `/concerns` downloads
  a standalone A4 PDF report (ReportLab Platypus, Vera fonts) containing all
  findings with severity-colour-coded tables and remediation hint text.
  Independent of the main sizing report pipeline.

- **Concerns CSV export** — new "Export CSV" button on `/concerns` downloads
  a UTF-8 BOM CSV (Excel-compatible) with one row per finding and columns:
  severity, check_id, title, detail, remediation, affected_count, cluster.

### Bug fixes

- **Session restore: layout and compute pages no longer crash** — after
  restoring a session saved before the layout or compute pages were visited,
  `_load_constraints()` and `_load_compute_config()` now use `or`-fallback
  defaults so that falsy restored values (`0`, `0.0`, `""`) correctly resolve
  to page defaults (4 TB DS capacity, "R760" preset) instead of causing
  `ValueError: Invalid value` in `ui.select()`.

### Documentation

- ADR-066: Session persistence via self-contained zip archive
- ADR-067: SESSION_ZIP_SENTINEL to distinguish session archives from LiveOptics zips
- ADR-068: Remediation hints as hardcoded English strings
- ADR-069: Standalone concerns export as pure ReportLab
- PRD updated to v7.0 (§4.11 session persistence, §4.12 concerns enhancements,
  updated user journey, milestone history)
- Architecture updated: session persistence and concerns export modules

## [v6.1.0] - 2026-02-23

### Bug fixes

- **vMSC per-site sizing always available** — the "Hosts per site (vMSC)"
  section no longer requires a Datacenter column with 2+ distinct values.
  The split ratio is applied to total VMs; the Datacenter column is
  informational only. Engineers can now use vMSC mode on any file,
  including single-datacenter or datacenter-less RVTools exports.

- **Type safety** — fixed two mypy errors: unsafe `int()` cast on `object`
  in `state.py`, and union-attr on `list | None` iteration in `layout_page.py`.

- **LLM config tests** — `test_llm_config_timeout_default` and
  `test_llm_config_max_concurrent_default` now guard against shell-level
  `LLM_TIMEOUT` / `LLM_MAX_CONCURRENT` env vars overriding pydantic-settings
  defaults.

### Documentation

- ADR-064: Datacenter/cluster scope filtering as a dedicated pipeline stage
- ADR-065: Windows Desktop OS fallback → VDI Linked Clone
- PRD updated to v6.0 (§4.2b scope filtering, classification table, §11
  shipped requirements)
- Architecture updated: 5-stage pipeline, `/scope` in diagrams, session
  state scope helpers, rule count 43 → 50

## [v6.0.0] - 2026-02-23

### New features

- **Datacenter & cluster filtering** — new `/scope` page (between upload and
  review) lets engineers select which datacenters and clusters to include in the
  analysis. All downstream pages (review, report, compute, layout, concerns) use
  the filtered dataset. Unselected VMs are preserved in session state so
  re-scoping never requires a re-upload. Scope badge shown in review/report
  headers; DC/cluster suffix appended to exported PDF and Excel filenames.

- **Improved workload classification** — rule set updated from a 1,483-VM
  LiveOptics analysis that previously left 92 % of VMs in `os_fallback`:
  - Windows 10/11 desktop VMs now classify as **VDI / Linked Clone** instead of
    Virtual Machines (catches ~900 VMs in typical enterprise files)
  - New generic VDI rule (priority 224): `VDI`, `DESKTOP`, `RDS`, `UAG`,
    `LOGINVSI`, `LOGINENTERPRISE`
  - Containers: added `TKG`, `HARBOR`, and `photon-*-kube` regex for Tanzu node images
  - Email: added `EXCHG` abbreviation
  - File Content Servers: added SharePoint abbreviations `SPBE`, `SPFE`, `SPOWA`, `SPOFFICE`
  - Logging - Analytics: added `LOGSTASH` and `KIBANA`

### Bug fixes

- **AG Grid reliability** — explicit `:valueGetter` on `vm_name` column fixes
  silent field extraction failure after NiceGUI `update_grid()` cycles (AG Grid
  v34). `typeof` guard on `:localeText` prevents ReferenceError when CDN hasn't
  loaded. Grid refresh now uses `run_grid_method("setGridOption")` instead of
  `update()` for reliable data refresh without destroy/recreate cycles.
- **"New Analysis" button** — clears session and navigates back to upload page
  without a full page reload.
- **Payload size** — `_to_grid_rows()` trims row data sent to AG Grid (~35 %
  smaller JSON on large files).
- **Type safety** — fixed two mypy errors in `state.py` (unsafe `int()` cast on
  `object`) and `layout_page.py` (union-attr on `list | None` iteration).

## [v5.0.0] - 2026-02-23

### New features

- **Per-cluster compute breakdown** — the `/compute` page now shows a breakdown table
  grouping host recommendations by cluster name when the RVTools file contains a Cluster
  column. A grand total row sums all clusters. Health check findings that apply per-cluster
  (HW version spread, HA ratio) display the cluster name alongside the finding on
  `/concerns`.

- **Health findings in exports** — PDF report now includes a findings summary table
  (Critical / Warning / Info counts) on the main sizing page, and a dedicated findings
  detail appendix listing every finding sorted critical-first. Excel export includes a new
  "Findings" worksheet with columns: Finding, Severity, Category, Affected VMs, Detail,
  Cluster.

- **Configurable vMSC site split ratio** — in vMSC (stretched cluster) mode, engineers
  can set any VM split percentage between sites (e.g. 60/40) instead of the fixed 50/50.
  The `/compute` settings panel exposes a 1–99% input visible only when vMSC is enabled.
  Site A and Site B host counts display as distinct labeled rows in the results card.

- **Configurable A/P DR active percentage** — in Active/Passive DR mode, engineers can
  configure what percentage of VMs are active on the primary site (1–100%, default 100%).
  Secondary site is sized at 50% of the computed primary (cold standby convention).

- **PRD v5.0** — Product Requirements Document updated to reflect all v5.0 features,
  personas, and non-functional requirements.

## [v4.0.1] - 2026-02-22

### Bug fixes

- **Fix all event handlers on `/compute`** — replaced `.on("update:model-value")` with
  `.on_value_change()`. Every control (preset selector, overcommit ratio, vMSC toggle,
  A/P toggle, spec inputs) was silently broken due to `GenericEventArguments` having no
  `.value` attribute; `ValueChangeEventArguments` does.
- **Ruff TC003** — moved `from pathlib import Path` into a `TYPE_CHECKING` block in
  `compute_sizing.py` (annotation-only use, safe with `from __future__ import annotations`).

### UX improvements

- **vCPU / RAM breakdown in N+1 card** — displays both sub-counts (e.g.
  "vCPU-based: 11 · RAM-based: 20") so users can see exactly which constraint binds
  and how the other count moves when adjusting the overcommit ratio.
- **Host spec inputs always visible** — cores/socket, sockets, and RAM are no longer
  hidden behind a "Custom" preset selection; all three inputs appear at all times.
- **Preset auto-populate** — selecting a named preset fills the spec fields from its
  base config; selecting "Custom" leaves the current field values untouched.
- **One preset per server model** — dropdown simplified from 16 spec-laden variants
  (e.g. "R760 (2x28c / 512 GiB)") to 7 clean model names: R760, R770, R860, R960,
  R7725, XE7745, Custom.
- **Remove duplicate heading** — "Configuration de l'hôte" was rendering twice in the
  settings panel; the redundant card label was removed.

## [v4.0.0] - 2026-02-22

Grid UX improvements, per-VM hardware data, and a new health check concerns page.

### Grid UX & VM Data (Phase 20)

- **Quick-filter search box** above the VM review grid — filters all visible columns
  instantly on each keystroke via AG Grid `quickFilterText`
- **Column visibility panel** — collapsible expansion above the grid with four
  checkboxes (vCPUs, RAM, Avg IOPS, Peak IOPS) toggling column visibility via
  `setColumnsVisible`; replaces AG Grid sidebar (Enterprise-only, unavailable in
  Community edition)
- **Hidden column definitions** added to the VM grid: `num_cpus`, `memory_mib`,
  `avg_iops`, `peak_iops` — hidden by default, revealed on demand
- **Stable row identity** — AG Grid `getRowId` switched from `vm_name` to
  `String(params.data.row_index)`, fixing row corruption for customer files with
  duplicate VM names (linked clones, template copies)
- `row_index` added to `CANONICAL_COLUMNS` and assigned as a contiguous integer
  in `ingest_file()` after template filtering
- Cell-change and bulk-update handlers updated to match rows by `row_index` (int)
  instead of `vm_name` string comparison

### Health Check & Concerns Page (Phase 21)

- **New `/concerns` page** — surfaces data quality flags, sizing risks, and VMware
  best practice violations derived from the current session without re-classifying
- **11 health checks** across three categories:
  - *Data Quality*: missing OS, zero provisioned storage, missing vCPU/RAM, high
    powered-off VM ratio (>30%)
  - *Sizing Risks*: high Unknown VM ratio (>25%), large Unknown VMs (>1 TiB),
    single VM exceeding 100K IOPS/datastore budget
  - *VMware Best Practices*: no cluster assignment, old HW version (<vHW17 /
    ESXi 7.0), very old HW version (<vHW14 / ESXi 6.7, Critical), VMware Tools
    not installed (Critical), VMware Tools not running
- Findings colour-coded by severity: Critical=red, Warning=yellow, Info=blue
- Powered-off VMs and templates excluded from best-practice checks
- `hw_version=0` sentinel guard: LiveOptics exports skip hardware-version checks
  rather than falsely flagging every VM as old hardware
- `hw_version` and `tools_status` added to `CANONICAL_COLUMNS`; RVTools parser
  reads them with graceful fallback (0 / "") when column absent
- LiveOptics parser sets sentinel values `hw_version=0`, `tools_status=""`
- Page uses `load_session_data()` — user edits from the Review grid are preserved;
  `HealthCheckResult` is never cached in session storage

### Compute Sizing Module & Page (Phase 22)

- **New `/compute` page** — reactive ESXi host count recommendations from the
  uploaded session data, with no re-ingestion; uses `load_session_data()` only
- **N+1 HA sizing** — recommended host count = `max(hosts_by_vcpu, hosts_by_ram) + 1`
  with configurable vCPU overcommit ratio (0.5–20.0, default 4.0)
- **vMSC (stretch cluster) mode** — toggle reveals per-datacenter host counts;
  shows a warning card when no datacenter column data is available in the export
- **Active/Passive DR mode** — toggle reveals primary site hosts and secondary
  site = `ceil(primary / 2)` (minimum 1)
- **17 Dell PowerEdge presets** loaded from `compute_presets.csv` (editable without
  code changes), covering:
  - R760 (Xeon 5th Gen: 28c, 32c, 48c variants)
  - R770 (Xeon 6 P-core: 6748P 48c, 6780P 64c, 6786P 86c)
  - R860/R960 (Xeon 5th Gen 4-socket: up to 56c/6 TiB)
  - R7725 (EPYC 9005 Turin: 9555 64c, 9655 96c, 9755 128c, 9955 192c Zen5c)
  - XE7745 AI server (EPYC 9005 Turin: 64c, 96c)
  - Custom (user-defined cores/socket, sockets, RAM)
- Preset selector, overcommit input, and mode toggles are session-scoped
  (`app.storage.tab`); result cards refresh reactively on every change
- Aggregate cards: active vCPU total, RAM total (GiB), excluded VM count
- `HostConfig`, `ComputeSizingResult` frozen dataclasses; zero UI imports in
  `pipeline/compute_sizing.py`
- `load_presets(path)` public function for loading alternate CSV files

### LLM Classifier Enhancement

- `vm_description` field (RVTools Annotation / LiveOptics Description) now included
  in LLM classifier prompts as an optional classification signal
- Description truncated to 200 chars, newlines stripped; only included when
  non-empty to keep token usage lean

### Tests

- 49 new health check tests covering all 11 check IDs, sentinel guards,
  powered-off/template exclusion, and affected_vms tuple contract
- 386 total tests passing

## [v3.2.0] - 2026-02-22

Annotation-based VM classification for healthcare and application workloads.

### Classifier

- Fix two-pass classification logic: OS-fallback rules (priority ≥ 900) are now
  skipped in pass 1 when an annotation (`vm_description`) is present, allowing
  pass 2 to match richer annotation content before falling back to OS heuristics
- Expand HealthCare/EMR-EHR rule with 25+ application keywords:
  - Radiology & imaging: PACS, INTELLISPACE, GLEAMER, AZMED, RAYVOLVE, TRAUMACAD
  - Hospital IS (French/Swiss & European ecosystem): OPALE, CARIATIDE, HANDYLIFE,
    POLYPOINT, MEDIDATA, DATABICS, PROCAMED, SEDIA, DGLAB, STERIGEST, WINSCRIBE,
    SYNLAB, EXOLIS, SCENARA, MIRTH, KODIP
  - Regex anchors: `\bRIS\b` (Radiology IS), `\bSIEMS\b`, `\bHESTIA\b`, `Bloc-?Op`
- Add `TOMCAT`, `FORTIWEB` to Web Servers rule
- Add `PRTG` to Logging/Analytics rule
- Add `APP VOLUMES` / `APPVOL` to VDI Profiles rule
- Add `ALFRESCO` to File Content Servers rule
- Add `FILEMAKER`, `CLARIS`, `SQLITE` to MySQL/NoSQL rule
- Word-boundary guards: SIEMS (avoids SIEMENS), HESTIA (avoids HestiaCP)

## [v3.0.0] - 2026-02-21

Datastore layout recommendations for PowerStore sizing.

### Layout Engine

- Three layout strategies: Consolidation (BFD bin-packing), Performance (mission-critical isolation + tier BFD), Uniform (LPT equal distribution)
- Multi-dimensional BFD algorithm respecting capacity, IOPS budget, and VM count constraints per datastore
- Default 4 TiB datastores, 25 VMs/DS, 100K IOPS/DS (all tunable via PlacementConstraints)
- Oversized VMs (>usable capacity) automatically placed in dedicated datastores
- `generate_all_proposals()` public API returning all 3 strategy proposals

### Default IOPS Estimates

- Workload-based IOPS estimates for RVTools imports (no LiveOptics performance data)
- 8 workload categories: Database/SQL (500), Oracle (800), SAP HANA (1000), VDI (30-50), generic VMs (50), File (100)
- Configurable via `src/store_predict/data/IOPS.csv` (semicolon-delimited, same pattern as DRR.csv)
- Hardcoded fallback when CSV is missing — tests remain independent

### Documentation

- ADR-059: Workload-based IOPS defaults for RVTools sizing
- Research page: Default IOPS domain knowledge (sources, conservative bias, peak vs average)
- Architecture docs updated with layout engine as 4th pipeline stage

### Tests

- 46+ layout engine tests covering BFD packing, 3 strategies, metrics, IOPS injection, CSV loading

## [v2.2.0] - 2026-02-21

Observability, developer experience, and project health improvements.

### LLM Classification Improvements

- Live progress counter in UI notification during AI classification: "AI classification: 42 / 496 VMs"
- `on_progress` callback added to `classify_unknown_vms_async` for UI integration
- Ready-to-paste `ClassificationRule(...)` snippets now logged to server logs after LLM pass, allowing operators to promote LLM findings to deterministic rules without restarting

### CI / GitHub

- GitHub Release v2.1.0 created (was missing — tag existed but Release page had not been generated)
- `ci.yml`: added `permissions: contents: read` (workflow security hardening)
- `ci.yml`: added `codecov/codecov-action@v5` upload step with `CODECOV_TOKEN`
- `ci.yml`: added `--cov-report=xml` to generate Codecov-compatible report
- Coverage measurement scoped to testable backend code (UI layer omitted — NiceGUI pages require a live server)
- Effective coverage: **84%** (up from misleading 51% that included untestable UI)

### README

- Added badges: CI, Docs, Release, Codecov coverage, Python version, Version
- Fixed stale "29 classification rules" → **43 rules**

### Tests

246 tests passing (unchanged); ruff and mypy clean.

## [v2.1.0] - 2026-02-20

Application-level DRR variants, DDVE support, and AI classification UI toggle.

### DRR Reference Table (+14 entries, 28 → 42 total)

New subcategories covering application-layer encryption and compression scenarios
where PowerStore's inline dedup/compression is partially or fully defeated:

- `Database / Oracle - HCC (App Compressed)` → DRR 2.5
- `Database / Oracle - TDE (Encrypted)` → DRR 1.5
- `Database / Oracle - HCC + TDE` → DRR 1.2
- `Database / Microsoft SQL - Page Compressed` → DRR 2.5
- `Database / Microsoft SQL - TDE (Encrypted)` → DRR 1.5
- `Database / Microsoft SQL - Page Compressed + TDE` → DRR 1.2
- `Database / MongoDB - Encrypted` → DRR 1.3
- `Database / PostgreSQL - Encrypted` → DRR 1.3
- `Database / My SQL / NoSQL - Encrypted` → DRR 1.3
- `Containers / Kubernetes - Encrypted PVs` → DRR 1.3
- `VM Replication / Commvault` → DRR 1.5
- `VM Replication / Veeam - Compressed + Dedup` → DRR 1.2
- `VM Replication / Commvault - Compressed + Dedup` → DRR 1.2
- `VM Replication / Data Domain Virtual Edition (DDVE)` → DRR 1.0 (already deduplicated — 1:1 at most)

### Classifier (+14 rules, priorities 88–97 and 293–297)

Pattern matching for encrypted/compressed VM naming conventions. Combined scenarios
(e.g. Oracle HCC + TDE) use regex lookaheads for AND matching. DDVE, Commvault, and
compressed Veeam/Commvault variants also added.

### AI Classification UI Toggle

Per-session `ui.switch` on the upload page to disable LLM classification without
server restart. Greyed out with hint when `LLM_ENABLED=false`. State persisted in
`app.storage.tab["llm_ui_enabled"]`.

### Documentation

- ADR-052: Flat DRR override for non-PowerStore storage models
- ADR-053: Application-level DRR degradation as CSV subcategory variants
- ADR-054: AI classification toggle is per-session, not a server restart
- Research phase 14: application-level data reduction findings with source references
- `architecture.md` updated: storage model section, DRR/rule counts, session state

### Tests

246 tests passing (up from 230); ruff and mypy clean.

## [v2.0.0] - 2026-02-20

Multi-platform storage model selection — **breaking UX change**: DRR values now depend on the selected target storage platform, not only on workload type.

### Target Storage Model Selector

- New `StorageModel` enum in `config.py`: `POWERSTORE` (full dedup+compression, per-workload DRR), `POWERFLEX` (compression only, flat 2.0), `POWERVAULT` (no reduction, flat 1.0)
- `apply_storage_model()` added to `services/drr_table.py` — overwrites per-VM DRR in session based on selected platform
- `get_storage_model()` / `set_storage_model()` added to `ui/state.py` for tab-scoped session persistence
- Review page now shows a `ui.toggle` selector (PowerStore / PowerFlex / PowerVault) above the summary stats; switching instantly recalculates all DRR values, refreshes the grid and stats
- Model is applied at page load so navigating back from the report preserves the selection
- Report page picks up overridden DRR values automatically — no changes required
- 6 i18n keys added (`storage_model.label`, `.powerstore`, `.powerflex`, `.powervault`) in both `en.yaml` and `fr.yaml`
- 3 new tests for `apply_storage_model()` (PowerVault→1.0, PowerFlex→2.0, PowerStore→table values); 230 tests passing, ruff and mypy clean

## [v1.1] - 2026-02-20

i18n, Branding & Intelligence milestone.

### Phase 13: Graphics (COMPLETE)

- `src/store_predict/services/charts.py` — four ECharts option-dict builders: `echart_sankey_options`, `echart_pie_options`, `echart_drr_bar_options`, `echart_before_after_options`; all use Dell blue `#007DB8` palette; Sankey falls back to grouped bar when fewer than 2 workload groups
- `src/store_predict/services/pdf_charts.py` — four ReportLab/matplotlib builders: `make_sankey_image_flowable` (lazy matplotlib import, `Spacer` guard for empty data), `make_pie_drawing`, `make_drr_bar_drawing`, `make_before_after_bar_drawing`
- `report.py` — `_build_charts_section()` added: Sankey full-width, pie + DRR bar in two-column grid, before/after bar full-width; only rendered when workload groups exist
- `pdf_report.py` — second PDF page added via `PageBreak()` + chart flowables; `on_later_pages` callback ensures Dell branded header on page 2
- `matplotlib>=3.8` confirmed in runtime dependencies; mypy overrides for `matplotlib.*` added
- 6 i18n keys added across `en.yaml` and `fr.yaml` (`pdf.charts_heading`, `pdf.sankey_title`, `pdf.pie_title`, `pdf.drr_bar_title`, `pdf.before_after_title`, `report.charts_heading`)
- 227 tests passing, ruff and mypy clean

### Phase 12: UX Polish (COMPLETE)

- Upload page refactored with spinner, linear progress bar, and `run.io_bound` pipeline offloading for a responsive event loop during 2-10 second processing
- Persistent LLM ui.notification (spinner=True, timeout=None) updated in-place to positive/negative outcome instead of fire-and-forget notify
- Review and report pages upgraded from plain links to card-with-CTA empty states (icon + label + button)
- PDF and Excel download buttons now disable during generation and re-enable via try/finally guard
- Company logo upload error message replaced with `t("error.logo_upload_failed")` i18n key
- Added 8 new i18n keys across en.yaml and fr.yaml (upload.processing, llm.error, error.unexpected, error.logo_upload_failed)
- Raw exception strings replaced with i18n messages across all user-facing error paths
- All `ui.notify()` type values audited to canonical NiceGUI types (positive/negative/warning/info)
- 20-test suite in test_ux_polish.py locking in UX patterns; full suite grows to 227 passed, 1 skipped

### Phase 11: LLM Classification Fallback (COMPLETE)

- LLMConfig pydantic-settings class reads 6 env vars (LLM_ENABLED/MODEL/API_KEY/API_BASE/TIMEOUT/MAX_CONCURRENT) with SecretStr masking for the API key
- `classify_unknown_vms_async` async function filters only "default" confidence VMs, runs bounded concurrency via asyncio.Semaphore, and logs only counts (never VM names)
- `classify_single_vm` applies input sanitization against prompt injection (truncate vm_name/os_name, strip newlines), asyncio timeout, and circuit breaker (3 failures -> 60s cooldown)
- LLM fallback wired into upload pipeline behind `llm_cfg.enabled` guard — feature is opt-in via `LLM_ENABLED=true` env var, never active in CI
- User notifications: persistent spinner before LLM pass, count notification after
- docker-compose.yml updated with `env_file` (required: false) and LLM_* env var stubs pointing to OpenRouter/Mistral defaults
- `.env.example` added and tracked in git as operator onboarding guide
- 7-test suite for config and classifier; pydantic-settings added to runtime dependencies

### Phase 10: PDF Branding (COMPLETE)

- Dell partner logo PNG bundled as package data and loaded at import time (Docker-safe path resolution)
- `_preprocess_logo()` normalizes any image mode (RGBA/RGB/P/JPEG) to RGBA PNG before ReportLab embedding, preventing black-background palette images
- `validate_logo()` validates PNG/JPEG by extension, magic bytes, file size, and image dimensions, raising IngestionError for user-facing messages
- `generate_report_pdf()` extended with backwards-compatible `dell_logo_bytes` and `company_logo_bytes` kwargs
- Company logo upload UI: `ui.upload` card on report page accepting .png/.jpg/.jpeg up to 200 KB with remove button
- Logo stored as base64 in `app.storage.tab` (tab-scoped session isolation) and decoded on PDF download
- `_on_download()` passes decoded `company_logo_bytes` to `generate_report_pdf()`, embedding customer logo in PDF header
- Pillow added to runtime dependencies; 16 branding tests + 11 logo UI wiring tests; 200 total tests

### Phase 9: Excel Export (COMPLETE)

- `generate_report_xlsx(summary, project_name, locale) -> bytes` pure function mirroring the PDF service shape (same locale param, same BytesIO pattern)
- Three styled sheets: Summary (label-value metrics), Workload Breakdown (category subtotals + totals row), VM Detail (per-VM row with optional performance columns)
- Brand blue (#1e3a5f) header row with white bold text, freeze panes at row 1, autofit columns on all sheets
- Alternate row colouring on body rows; performance columns/rows gated on `has_performance_data` flag
- 18 new `excel.*` i18n keys in both en.yaml and fr.yaml; EN and FR outputs verified to differ in bytes
- Green "Download Excel Report" button wired on report page between PDF and Back buttons
- `_on_download_excel` handler mirrors `_on_download`: assert summary type, generate bytes, sanitize filename, `ui.download`
- XlsxWriter mypy override added; 8-test suite validating magic bytes, locale switching, performance guard, and sheet count

### Phase 8.1: LiveOptics ZIP Extraction (COMPLETE)

- ZIP accepted as a fourth upload format alongside .xlsx and .csv
- `extract_liveoptics_from_zip(content: bytes) -> tuple[bytes, str]` module finds the LiveOptics xlsx member by case-insensitive regex pattern
- Zip bomb guard rejects archives whose total uncompressed bytes exceed 100 MB (central directory header check, no extraction needed)
- ZIP extraction runs before `validate_upload()` so extracted xlsx bytes go through existing validation logic unchanged
- `validation.py` extended to accept "zip" extension and PK magic bytes; upload accept prop updated to `.xlsx,.csv,.zip`
- 7-test suite with real in-memory zipfile objects covering happy path, pattern mismatch, no match, invalid zip, multiple members, and bomb guard
- Zero regressions; 165 tests passing after addition

### Phase 8: i18n Foundation (COMPLETE)

- `t()` translation helper backed by python-i18n YAML files with `%{variable_name}` placeholder syntax
- Tab-scoped `get_locale()` / `set_locale()` session helpers safe outside NiceGUI context (catches RuntimeError for pytest)
- English and French YAML locale files with 73 strings across 8 namespaces (layout, upload, review, report, stats, dialog, columns, pdf)
- `add_locale_toggle()` FR/EN toggle button triggering full page reload (required because `ui.header` cannot be in `@ui.refreshable`)
- French is the default locale per project convention; toggle label shows the switch-target language
- All 65 UI-layer strings in 8 files wrapped in `t()` calls; no hardcoded labels remain
- AG Grid configured with French CDN locale pack (`ag-grid-community/locale@32.2.2`) and `:localeText` JS binding, injected only when locale is 'fr'
- PDF localized: `generate_report_pdf()` accepts `locale` param; `_i18n.set('locale', locale)` called once before all t() calls
- 13-test i18n unit suite covering EN/FR lookup, placeholder substitution, get_locale() safety, and PDF locale correctness

## [v1.0] - 2026-02-19

MVP Sizing Tool milestone.

### Phase 7: UI Bug Fixes & Report Enhancements (COMPLETE)

- Fixed AG Grid "No Rows To Show" — NiceGUI requires `:` prefix for JS function properties
- Fixed NaN serialization chain: `NaN → None` (not empty string) for JSON compatibility
- NiceGUI auto-reload with `__mp_main__` guard for multiprocessing
- LiveOptics performance columns: Peak IOPS, 8K Eq. IOPS, Peak MB/s (conditional on data)
- 8K IOPS normalization fix: `throughput_KB/s / 8` (was double-counting with avg_iops)
- Editable DRR column for custom overrides (min 0.1)
- Bulk workload update: select multiple VMs via checkboxes, mass-assign workload category
- Workload dropdown popup (`cellEditorPopup: True`) for readable category labels
- Filtered select-all: header checkbox selects only visible (filtered) rows
- CPU/memory metrics: `num_cpus` and `memory_mib` in parsers, calculation, report, and PDF
- Report reorganized into Totals and Averages sections (web + PDF)
- Replaced misleading "Total Peak IOPS" with "Hottest VM Peak IOPS" (single VM max)
- WorkloadDialog fixed to accept plain strings (not dicts) for NiceGUI ui.select
- 145 tests passing, 1 skipped

### Phase 6: Polish, Docs & Deployment (COMPLETE)

- Docker hardening: `.dockerignore`, `HEALTHCHECK` directive, env-var `STORAGE_SECRET`
- Server-side file upload validation with magic-byte checks (XLSX zip header, CSV UTF-8)
- Logging configuration with sanitization guidance (never log DataFrame contents)
- Session isolation verification via `app.storage.tab` (tab-scoped)
- Performance benchmark tests: 5000 VM classification < 10s, PDF generation < 5s
- MkDocs documentation: architecture page with 3 Mermaid diagrams, getting-started guide
- Project README with Docker and local dev quickstart
- GitHub Actions CI: ruff check, ruff format, mypy, pytest on push/PR to main
- GitHub Actions docs: MkDocs deployment to GitHub Pages on push to main
- 15 new tests (validation + log sanitization + performance), 121 total tests passing

### Phase 5: Calculation & PDF Report (COMPLETE)

- Calculation service with per-VM required capacity (`provisioned_mib / drr`)
- Workload grouping with subtotals (VM count, provisioned, in-use, required per category)
- Weighted average DRR (`total_provisioned / total_required`, not simple average)
- Division-by-zero guard: `max(drr, 0.1)` prevents invalid calculations
- Missing field defaults via `.get()` for robustness with incomplete data
- PDF report generator using ReportLab Platypus with branded one-page layout
- Dark blue header bar with StorePredict branding
- Workload breakdown table in PDF (Category, VMs, Provisioned, Avg DRR, Required)
- Vera/VeraBd TTF fonts for French character support (accents, special chars)
- Storage formatting helper: MiB to GiB with TiB display for large values
- Report page at `/report` with summary cards and workload breakdown table
- PDF download button triggering browser download
- Navigation wiring: Review → Report button, Report link in nav bar
- 24 new tests (12 calculation + 12 PDF), 106 total tests passing

### Phase 4: UI — Upload & Review Pages (COMPLETE)

- Session state module for per-tab DataFrame serialization (`ui/state.py`)
- Upload page with file dropzone, project name input, pipeline integration
- AG Grid VM table component with inline workload dropdown (ADR-007)
- Multi-select workload dialog for assigning multiple workload types (ADR-009)
- Summary statistics cards (Total VMs, Provisioned, Avg DRR, Effective Capacity)
- Review page wiring all components: table, dialog, stats, DRR recalculation
- Dark mode toggle with persistent user preference via `app.storage.user` (ADR-008)
- Navigation header with Home, Upload, and Review links
- Cell change handler: inline workload dropdown updates DRR and stats
- Row click handler: multi-select dialog applies conservative (lowest) DRR
- Per-tab session isolation for upload data, per-user storage for preferences (ADR-008)

### Phase 3: Workload Classification Engine

- Classification engine with 29 priority-ordered rules covering all 28 DRR subcategories
- ClassificationRule dataclass with pattern matching on VM name and OS field
- RuleRegistry with first-match-wins evaluation and confidence tracking
- Substring matching (CADSRVSQL001 -> SQL) with false positive prevention
- OS-based fallback rules (Windows Server -> Virtual Machines)
- classify_dataframe() for bulk DataFrame classification
- 0% Unknown rate on 594 real LiveOptics VMs (target was <20%)
- 28 unit tests + 11 integration tests with real sample data

### Phase 2: File Ingestion Pipeline

- RVTools .xlsx parser (vInfo tab)
- LiveOptics .xlsx and .csv parsers (VMs tab)
- Format auto-detection based on sheet names and column headers
- Column alias resolution for name variations
- Template VM filtering
- Unified ingest_file() orchestrator
- 29 ingestion tests with real sample files

### Phase 1: Project Foundation & DRR Table

- Python project structure with src layout
- DRR table service loading 28 workload categories from CSV
- Data models (VM, FileFormat, WorkloadCategory)
- NiceGUI app skeleton with page routing
- ruff + mypy configuration
- pytest setup with 14 initial tests
- Dockerfile + docker-compose.yml
