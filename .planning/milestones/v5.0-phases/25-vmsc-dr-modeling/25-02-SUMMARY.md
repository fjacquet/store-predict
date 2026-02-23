---
phase: 25-vmsc-dr-modeling
plan: "02"
subsystem: ui/compute
tags: [compute, vmsc, dr, split-ratio, i18n, nicegui]
dependency_graph:
  requires:
    - phase: 25-01
      provides: compute_sizing() with vmsc_split_ratio and ap_active_ratio params, vmsc_site_a_hosts/vmsc_site_b_hosts fields
  provides:
    - Settings panel with vmsc_split_pct input (visible when vMSC toggle on)
    - Settings panel with ap_active_pct input (visible when A/P toggle on)
    - Results panel vMSC card with Site A and Site B as distinct labeled rows
    - Results panel A/P card with active ratio context note
    - compute.host_unit i18n key (en/fr)
  affects:
    - Phase 26 (Documentation — UI features to document)
tech_stack:
  added: []
  patterns:
    - Conditional input visibility toggled by switch on_change callback
    - Integer percentage stored in tab storage, converted to float ratio for pipeline call
key_files:
  created: []
  modified:
    - src/store_predict/ui/pages/compute.py
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
key_decisions:
  - "vmsc_split_pct stored as integer 1-99 in tab storage; divided by 100.0 at compute_sizing() call boundary"
  - "ap_active_pct stored as integer 1-100 in tab storage; divided by 100.0 at compute_sizing() call boundary"
  - "vmsc_split_input and ap_active_input visibility toggled in switch on_change callbacks — no separate refresh needed"
  - "Site A and Site B displayed as distinct labeled rows with icons, counts, and unit label (VMSC-03)"

patterns-established:
  - "Ratio inputs: store integer pct in tab storage, convert to float at pipeline boundary"
  - "Input visibility: set_visibility(bool(e.value)) in the corresponding toggle callback"

requirements-completed: [VMSC-01, VMSC-02, VMSC-03]

duration: ~2min
completed: "2026-02-23"
---

# Phase 25 Plan 02: vMSC & DR Modeling — UI Controls for Site Split Ratios

**Compute UI now exposes configurable vMSC Site A split % and A/P primary active % inputs with reactive per-site host count display (Site A / Site B rows)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-23T08:43:35Z
- **Completed:** 2026-02-23T08:45:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Settings panel: vmsc_split_pct number input (1-99) appears when vMSC toggle is on, persists to tab storage key `compute_vmsc_split`, defaults to 50
- Settings panel: ap_active_pct number input (1-100) appears when A/P toggle is on, persists to tab storage key `compute_ap_active`, defaults to 100
- vMSC results card: Site A and Site B shown as distinct labeled rows with host counts, icons, and split percentage label (satisfies VMSC-03)
- A/P results card: active ratio context note added below secondary site
- compute_sizing() call now passes both ratios (vmsc_split_ratio and ap_active_ratio) derived from the pct inputs
- compute.host_unit i18n key added to en.yaml ("hosts") and fr.yaml ("hotes")

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend session config and settings panel with ratio inputs** - `ecf25a5` (feat)
2. **Task 2: Update results panel for per-site host count display (VMSC-03)** - `37ca71b` (feat)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified

- `src/store_predict/ui/pages/compute.py` - Added vmsc_split_pct/ap_active_pct to TypedDict; new ratio inputs in settings panel; per-site Site A/B rows in vMSC card; active ratio note in A/P card; compute_sizing() now receives both ratios
- `src/store_predict/i18n/locales/en.yaml` - Added compute.host_unit: "hosts"
- `src/store_predict/i18n/locales/fr.yaml` - Added compute.host_unit: "hotes"

## Decisions Made

- Integer percentage stored in tab storage, float ratio passed to pipeline: clean separation between UI representation and computation layer
- Input visibility controlled in the switch callback (not a separate observer): reduces latency for the common toggle-then-see-input UX flow
- Site A / Site B as distinct rows with icons satisfies VMSC-03 (distinct labeled rows)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed EN DASH in TypedDict comments (RUF003)**
- **Found during:** Task 1 (ruff check)
- **Issue:** Plan code sample used EN DASH characters (–) in comments; ruff flags RUF003
- **Fix:** Replaced EN DASH with hyphen-minus in both TypedDict field comments
- **Files modified:** src/store_predict/ui/pages/compute.py
- **Verification:** ruff check clean
- **Committed in:** ecf25a5 (Task 1 commit)

**2. [Rule 1 - Bug] Added strict=False to zip() in pre-Task-2 code (B905)**
- **Found during:** Task 1 (ruff check on the existing zip loop from plan 25-01)
- **Issue:** zip() without strict= parameter; Task 2 would replace this code but ruff checks ran after Task 1
- **Fix:** Added strict=False to the zip() call; code replaced by Task 2 anyway
- **Files modified:** src/store_predict/ui/pages/compute.py
- **Verification:** ruff check clean
- **Committed in:** ecf25a5 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - linting bugs in code derived from plan or prior phase)
**Impact on plan:** Trivial cosmetic fixes. No scope creep.

## Issues Encountered

Pre-existing test failure `test_llm_config_max_concurrent_default` in `tests/test_llm_classifier.py` — confirmed pre-existing by stash test. Unrelated to this plan's changes (LLMConfig.max_concurrent default value mismatch). All 461 other tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- vMSC & DR Modeling phase complete (both plans 25-01 and 25-02 done)
- UI exposes configurable split ratios with reactive per-site display
- Phase 26 (Documentation) can proceed

## Self-Check: PASSED

### Files Exist
- [x] `src/store_predict/ui/pages/compute.py` — contains `vmsc_split_pct`, `ap_active_pct`, `vmsc_split_input`, `ap_active_input`, Site A/B rows
- [x] `src/store_predict/i18n/locales/en.yaml` — contains `compute.host_unit: "hosts"`
- [x] `src/store_predict/i18n/locales/fr.yaml` — contains `compute.host_unit: "hotes"`
- [x] `.planning/phases/25-vmsc-dr-modeling/25-02-SUMMARY.md` — this file

### Commits Exist
- [x] ecf25a5 — Task 1 (session config, settings panel, compute_sizing() call)
- [x] 37ca71b — Task 2 (per-site rows, host_unit i18n keys, AP note)

### Test Results
- 461 tests pass, 1 skipped, 1 pre-existing failure (unrelated LLM test)
- ruff: no issues on compute.py
- mypy: no issues on compute.py

---
*Phase: 25-vmsc-dr-modeling*
*Completed: 2026-02-23*
