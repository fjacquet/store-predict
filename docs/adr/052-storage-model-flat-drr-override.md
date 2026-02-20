# ADR-052: Flat DRR override for non-PowerStore storage models

**Date:** 2026-02-20
**Status:** Accepted

## Context

StorePredict was originally designed exclusively for Dell PowerStore, which supports
both inline deduplication and compression. Pre-sales engineers also need to size for
two other Dell platforms that offer different data-reduction capabilities:

| Platform | Dedup | Compression | Effective DRR |
|----------|-------|-------------|---------------|
| PowerStore | ✅ | ✅ | Per workload (from DRR.csv) |
| PowerFlex | ❌ | ✅ | ~2:1 flat |
| PowerVault | ❌ | ❌ | 1:1 (none) |

The tool needed a way to switch between platforms without re-uploading the file.

## Decision

Apply a **flat DRR override at the session layer** rather than adding platform-aware
columns to DRR.csv or branching inside the calculation engine.

`apply_storage_model()` in `services/drr_table.py` iterates over `row_data` (the
list of per-VM dicts stored in `app.storage.tab["vm_data"]`) and overwrites each
row's `drr` key:

- `POWERVAULT` → `1.0`
- `POWERFLEX` → `2.0`
- `POWERSTORE` → `drr_table.get_ratio(category, subcategory)` (restores from CSV)

The selected model is persisted as `app.storage.tab["storage_model"]` (string value
of the `StorageModel` enum). The review page applies the stored model on every page
load, so navigating away and back preserves the selection.

## Consequences

- `calculation.py` and `report.py` required **zero changes** — they read DRR from
  session data and are model-agnostic.
- Switching model overwrites any manual per-VM DRR edits the user made. This is
  intentional: model selection is a global override. The `drr` column remains
  manually editable after switching for fine-tuning.
- PowerFlex DRR=2.0 is a conservative round number based on Dell's published
  compression-only benchmarks. A pre-sales engineer can override individual VMs
  if they have more precise data.
- Adding a fourth platform in future requires only a new enum value and a new `elif`
  branch in `apply_storage_model()`.
