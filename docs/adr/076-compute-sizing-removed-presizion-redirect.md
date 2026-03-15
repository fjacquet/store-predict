# ADR-076: Remove compute sizing, redirect to PreSizion

**Date:** 2026-03-15
**Status:** Accepted
**Supersedes:** [ADR-062](062-compute-presets-csv.md) (now Superseded)

## Context

StorePredict's `/compute` page provided ESXi host count recommendations based on
uploaded VM data: vCPU/RAM aggregation, N+1 HA sizing, vMSC stretch cluster splits,
and active/passive DR modeling. This functionality has been fully superseded by
[PreSizion](https://github.com/fjacquet/presizion), a dedicated sizing tool with
broader compute, storage, and network sizing capabilities.

Maintaining parallel compute sizing logic in two projects creates drift risk and
duplicates engineering effort.

## Decision

Remove all compute sizing logic from StorePredict:

- **Deleted:** `pipeline/compute_sizing.py`, `data/compute_presets.csv`,
  `tests/test_compute_sizing.py`
- **Cleaned:** compute config keys from `session_archive.py`, tooltip i18n keys,
  `COMPUTE_PRESETS_CSV_PATH` from `config.py`
- **Replaced:** `/compute` page now displays a card with links to
  PreSizion's web app and GitHub repository

The `/compute` route and nav link are preserved so users discover the redirect
rather than hitting a 404.

## Consequences

- **Positive:** Single source of truth for compute sizing (PreSizion).
- **Positive:** ~500 lines of pipeline code and ~160 lines of UI code removed.
- **Positive:** Simpler session archive format (no compute keys to serialize).
- **Negative:** Users must switch to an external tool for compute sizing.
- **Negative:** Session archives created with schema v1 that contain compute keys
  will silently ignore those keys on restore (harmless — the data is unused).
