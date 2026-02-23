---
phase: 25-vmsc-dr-modeling
verified: 2026-02-23T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 25: vMSC / DR Modeling Verification Report

**Phase Goal:** Engineers can configure site-specific VM distribution for stretched cluster and disaster recovery scenarios, and see per-site host counts on the compute page
**Verified:** 2026-02-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | In vMSC mode, engineer can set any VM split percentage between sites (e.g., 60/40) instead of fixed 50/50 | VERIFIED | `vmsc_split_pct` in `_ComputeConfig`, number input (min=1, max=99) in settings panel, wired to `compute_sizing(vmsc_split_ratio=cfg["vmsc_split_pct"] / 100.0)` |
| 2 | In A/P DR mode, engineer can configure what percentage of VMs are active on the primary site | VERIFIED | `ap_active_pct` in `_ComputeConfig`, number input (min=1, max=100) in settings panel, wired to `compute_sizing(ap_active_ratio=cfg["ap_active_pct"] / 100.0)` |
| 3 | The /compute page shows per-site host counts for vMSC and A/P DR as distinct labeled rows (Site A / Site B) | VERIFIED | `_results_panel()` renders Site A row (`t("compute.vmsc_site_a")`, `result.vmsc_site_a_hosts`) and Site B row (`t("compute.vmsc_site_b")`, `result.vmsc_site_b_hosts`) as distinct `ui.row()` elements within the vMSC card; A/P DR shows Primary Site and Secondary Site columns |

**Score:** 3/3 observable truths verified

### Plan 25-01 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | compute_sizing() accepts vmsc_split_ratio param and computes per-site hosts | VERIFIED | Param present at compute_sizing.py:220, per-site math at lines 318-329 |
| 2 | compute_sizing() accepts ap_active_ratio param and sizes primary by that fraction | VERIFIED | Param present at compute_sizing.py:221, primary sizing at lines 335-341 |
| 3 | ComputeSizingResult exposes vmsc_site_a_hosts and vmsc_site_b_hosts as distinct int fields | VERIFIED | compute_sizing.py:91-92 |
| 4 | All new i18n keys exist in both en.yaml and fr.yaml | VERIFIED | en.yaml: vmsc_split_ratio, vmsc_split_hint, vmsc_site_a, vmsc_site_b, ap_active_ratio, ap_active_hint, host_unit all present; fr.yaml: all 7 keys present |
| 5 | All pytest tests pass | VERIFIED | 56 tests pass (rtk pytest tests/test_compute_sizing.py) |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/store_predict/pipeline/compute_sizing.py` | Updated compute_sizing() with configurable split ratios | VERIFIED | Contains `vmsc_split_ratio`, `ap_active_ratio`, `vmsc_site_a_hosts`, `vmsc_site_b_hosts`; full implementation with clamping math |
| `src/store_predict/i18n/locales/en.yaml` | New UI label keys for split ratio inputs | VERIFIED | Contains `vmsc_split_ratio`, `vmsc_split_hint`, `vmsc_site_a`, `vmsc_site_b`, `ap_active_ratio`, `ap_active_hint`, `host_unit` |
| `src/store_predict/i18n/locales/fr.yaml` | French translations for new keys | VERIFIED | All 7 keys present with proper French text |
| `tests/test_compute_sizing.py` | Tests for configurable ratio behavior | VERIFIED | `TestVMSCConfigurableSplit` (5 tests: 50/50, 60/40, clamped below, clamped above, disabled) and `TestAPActiveRatio` (4 tests) present and passing |
| `src/store_predict/ui/pages/compute.py` | Settings panel with ratio inputs + results panel with per-site rows | VERIFIED | `vmsc_split_pct` and `ap_active_pct` in `_ComputeConfig`; number inputs with visibility toggling; Site A / Site B rows in results |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `compute_sizing() vmsc_split_ratio` | `ComputeSizingResult.vmsc_site_a_hosts / vmsc_site_b_hosts` | Per-site vCPU proportioning math | WIRED | Lines 318-329: `site_a_vcpus = round(total_vcpus * clamped_vmsc_split)`, per-site host max() call |
| `compute_sizing() ap_active_ratio` | `ComputeSizingResult.ap_primary_hosts / ap_secondary_hosts` | Fraction-based primary sizing | WIRED | Lines 335-341: `active_vcpus_primary = round(total_vcpus * clamped_ap_active)` |
| `vmsc_split_ratio input` | `app.storage.tab['compute_vmsc_split']` | on_value_change callback | WIRED | `_on_vmsc_split_change` saves `int(e.value)` to `app.storage.tab["compute_vmsc_split"]`; wired at line 408 |
| `app.storage.tab['compute_vmsc_split']` | `compute_sizing(vmsc_split_ratio=...)` | `_load_compute_config()` loading from tab storage | WIRED | `"vmsc_split_pct": int(app.storage.tab.get("compute_vmsc_split", 50))` at line 65; passed as `cfg["vmsc_split_pct"] / 100.0` at line 173 |
| `ComputeSizingResult.vmsc_site_a_hosts / vmsc_site_b_hosts` | Site A / Site B rows in vMSC card | `_results_panel` rendering | WIRED | Lines 215-223: distinct `ui.row()` for Site A (result.vmsc_site_a_hosts) and Site B (result.vmsc_site_b_hosts) |

### Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| VMSC-01 | 25 (plans 25-01, 25-02) | vMSC mode allows engineer to configure VM split ratio between sites (not locked to 50/50) | SATISFIED | `vmsc_split_pct` input (1-99), wired to `vmsc_split_ratio` param in compute_sizing(), applied in per-site math |
| VMSC-02 | 25 (plans 25-01, 25-02) | A/P DR mode allows engineer to configure what percentage of VMs run active on primary site | SATISFIED | `ap_active_pct` input (1-100), wired to `ap_active_ratio` param in compute_sizing(), applied to primary sizing |
| VMSC-03 | 25 (plan 25-02) | Compute page shows per-site host count for vMSC and A/P DR scenarios as separate rows | SATISFIED | vMSC card: distinct Site A row + Site B row with labeled icons; A/P DR card: Primary Site column + Secondary Site column |

All 3 requirements marked as VMSC in REQUIREMENTS.md traceability table are accounted for across plans 25-01 and 25-02. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| compute_sizing.py | 112 | "placeholder" in comment | Info | Not a code stub — refers to Custom row UI behavior in docstring, no implementation impact |
| compute_sizing.py | 185, 386, 392 | `return []` | Info | Legitimate early-exit guards for empty/None DataFrame inputs, not stubs |

No blockers or warnings found.

### Human Verification Required

#### 1. vMSC split input conditional visibility

**Test:** Enable vMSC toggle, then disable it. Check that the Site A Split (%) input appears and disappears.
**Expected:** Input visible only when vMSC toggle is on; persists across page interactions.
**Why human:** `set_visibility()` behavior in NiceGUI requires browser rendering to confirm.

#### 2. A/P active input conditional visibility

**Test:** Enable A/P DR toggle, enter a custom active %, toggle off and back on.
**Expected:** Input appears with the last saved value (persistent via tab storage).
**Why human:** Tab storage persistence across NiceGUI UI refresh cycles requires live browser test.

#### 3. Site A / Site B row display with asymmetric split

**Test:** With RVTools data containing 2+ datacenters, set vMSC split to 70%. Verify Site A host count > Site B host count.
**Expected:** Site A row shows more hosts than Site B; split label shows "70% / 30%".
**Why human:** Requires uploading actual RVTools data with multi-datacenter configuration.

### Gaps Summary

No gaps found. All automated checks pass:

- `compute_sizing()` correctly accepts and applies `vmsc_split_ratio` and `ap_active_ratio` parameters
- `ComputeSizingResult` exposes `vmsc_site_a_hosts` and `vmsc_site_b_hosts` as distinct fields (the old `vmsc_hosts_per_site` scalar is gone)
- Settings panel exposes configurable number inputs for both ratios, with conditional visibility tied to respective toggles
- Results panel renders Site A and Site B as distinct labeled rows for vMSC
- All key storage/retrieval links are wired: input change -> tab storage -> config load -> compute_sizing() call -> results render
- All 56 tests in `test_compute_sizing.py` pass including the new `TestVMSCConfigurableSplit` and `TestAPActiveRatio` classes
- Both locale files contain all 7 new i18n keys
- No TODO/FIXME/placeholder stubs in implementation code

---

_Verified: 2026-02-23_
_Verifier: Claude (gsd-verifier)_
