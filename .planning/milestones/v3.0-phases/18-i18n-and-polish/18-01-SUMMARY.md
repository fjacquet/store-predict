---
phase: 18-i18n-and-polish
plan: "01"
subsystem: i18n-and-ui
tags:
  - i18n
  - tooltip
  - charts
  - ux-polish
  - localization
dependency_graph:
  requires:
    - 17-01 (pdf_report.py, excel_report.py — layout page/sheet infrastructure)
    - 16-01 (layout_page.py — settings panel and slot template)
    - 16-02 (layout_page.py — expandable datastore tables)
  provides:
    - tooltip section (15 keys) in both locale YAML files
    - chart section (5 keys) in both locale YAML files
    - Localized chart legend strings via t('chart.*') in charts.py
    - Fixed slot template using ds.vm_list i18n key in layout_page.py
    - .tooltip() annotations on 9+ UI controls across 4 pages
  affects:
    - All pages rendering charts (report_page)
    - Layout page expandable datastore table (VM drill-down)
    - Upload, review, report pages (tooltip UX)
tech_stack:
  added: []
  patterns:
    - Python f-string pre-interpolation for NiceGUI slot templates with Vue double-brace escape
    - Provisioned/Required label variables used in both Sankey nodes and links to ensure name/source/target parity
    - .tooltip(t('tooltip.X')) chaining on NiceGUI elements inside page render functions
key_files:
  created: []
  modified:
    - src/store_predict/i18n/locales/en.yaml
    - src/store_predict/i18n/locales/fr.yaml
    - src/store_predict/services/charts.py
    - src/store_predict/ui/pages/layout_page.py
    - src/store_predict/ui/pages/upload.py
    - src/store_predict/ui/pages/review.py
    - src/store_predict/ui/pages/report.py
    - tests/test_ux_polish.py
decisions:
  - "f-string slot template: Vue {{ }} must be escaped to {{{{ }}}} in Python f-strings — applied to col.value and vm variable references"
  - "Sankey node/link parity: provisioned_label and required_label variables pre-computed once, used in both nodes list and links list — guarantees source/target matches node name regardless of locale"
  - "Tooltips added inline in page render functions (not at module level) to respect NiceGUI client context requirements"
  - "isolation_score and oversized_vms tooltip annotations placed on metric label cards in _build_strategy_detail(), not in the ui.table comparison (which renders via JSON rows)"
  - "storage_toggle uses .tooltip() chained after .classes() — NiceGUI toggle() supports tooltip() method like other elements"
metrics:
  duration: "~20 minutes"
  completed: "2026-02-21"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 8
---

# Phase 18 Plan 01: i18n and Polish Summary

Complete i18n coverage for StorePredict v3.0: tooltip and chart i18n sections added to both locale YAML files, chart legend strings localized via t('chart.*'), the last hardcoded slot template string fixed via f-string injection of ds.vm_list, and .tooltip() annotations wired to 9+ UI controls across 4 pages.

## What Was Implemented

### Task 1: YAML i18n Sections (en.yaml + fr.yaml)

Added two new top-level sections at the end of both locale files:

**tooltip: (15 keys)**
Keys: llm_toggle, bulk_update, storage_model, download_pdf, download_excel, upload_logo, max_ds_capacity, max_vms_per_ds, iops_budget, snapshot_reserve, growth_margin, isolation_score, snapshot_rating, oversized_vms, iops_headroom

**chart: (5 keys)**
Keys: provisioned, required, single_category, drr_axis, gib_axis

Final key count: 217 EN keys == 217 FR keys (zero parity gap).

### Task 2: Hardcoded String Fixes

**charts.py:**
- Added `from store_predict.i18n import t` import
- `echart_sankey_options()`: Pre-computed `provisioned_label = t("chart.provisioned")` and `required_label = t("chart.required")` — used in both nodes list (name field) AND links list (source/target fields) to guarantee Sankey chart integrity
- `echart_pie_options()`: `"Single category"` replaced with `t("chart.single_category")`
- `echart_drr_bar_options()`: `"DRR"` yAxis name replaced with `t("chart.drr_axis")`
- `echart_before_after_options()`: `"GiB"`, `"Provisioned"`, `"Required"` replaced with t() calls

**layout_page.py:**
- Pre-computed `vms_label = t("ds.vm_list")` before the body slot call
- Converted body slot from `r'''...'''` to `f'''...'''`
- Escaped all Vue `{{ }}` interpolations to `{{{{ }}}}` (col.value, vm)
- Replaced hardcoded `VMs assigned:` with `{vms_label}:`

### Task 3: Tooltip Annotations and Test Coverage

**layout_page.py (7 annotations):**
- Max DS Capacity select: `.tooltip(t("tooltip.max_ds_capacity"))`
- Max VMs per DS slider: `.tooltip(t("tooltip.max_vms_per_ds"))`
- IOPS Budget number: `.tooltip(t("tooltip.iops_budget"))`
- Snapshot Reserve slider: `.tooltip(t("tooltip.snapshot_reserve"))`
- Growth Margin slider: `.tooltip(t("tooltip.growth_margin"))`
- Isolation Score metric label: `.tooltip(t("tooltip.isolation_score"))`
- Oversized VMs metric label: `.tooltip(t("tooltip.oversized_vms"))`

**upload.py (1 annotation):**
- LLM toggle switch: `.tooltip(t("tooltip.llm_toggle"))`

**review.py (2 annotations):**
- Bulk update button: `.tooltip(t("tooltip.bulk_update"))`
- Storage model toggle: `.tooltip(t("tooltip.storage_model"))`

**report.py (3 annotations):**
- Download PDF button: `.tooltip(t("tooltip.download_pdf"))`
- Download Excel button: `.tooltip(t("tooltip.download_excel"))`
- Logo upload widget: `.tooltip(t("tooltip.upload_logo"))`

**test_ux_polish.py:**
- Added `PHASE_18_KEYS` list (20 keys)
- `test_phase18_i18n_key_present`: parametrized over 20 keys x 2 locales = 40 new tests
- `test_layout_page_slot_uses_ds_vm_list`: asserts no hardcoded 'VMs assigned:' and ds.vm_list present
- `test_charts_no_hardcoded_legend_strings`: asserts no bare 'Provisioned'/'Required' in charts.py

## Test Results

- `test_ux_polish.py`: 62 tests pass (22 existing + 40 new Phase 18 parametrized)
- `test_i18n.py`: 13 tests pass
- Full suite: 345 passed, 1 skipped — zero regressions

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Additional scope (within plan):** Added isolation_score and oversized_vms metric cards with tooltips to `_build_strategy_detail()` — plan mentioned these as optional for the strategy detail view, implemented in the 4-card block as documented.

## Self-Check: PASSED

All created/modified files present on disk. All task commits verified in git log.

| Check | Result |
|-------|--------|
| en.yaml | FOUND |
| fr.yaml | FOUND |
| charts.py | FOUND |
| layout_page.py | FOUND |
| test_ux_polish.py | FOUND |
| 18-01-SUMMARY.md | FOUND |
| Commit 7ac41cd (Task 1) | FOUND |
| Commit 31f57f0 (Task 2) | FOUND |
| Commit 7ce0f09 (Task 3) | FOUND |
