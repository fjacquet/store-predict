# ADR-062: Compute presets from CSV, not hardcoded

**Date:** 2026-02-22
**Status:** Superseded by [ADR-076](076-compute-sizing-removed-presizion-redirect.md)

## Context

Phase 22 introduced a `/compute` page with Dell PowerEdge host presets used to
size ESXi clusters. The initial implementation (`pipeline/compute_sizing.py`)
hard-coded 9 `HostConfig` entries directly in Python. Pre-sales engineers
regularly need to add newly-announced server models (e.g., R770 with Xeon 6
6786P 86c, R7725 with EPYC 9005 Turin 192c Zen5c) without waiting for a code
change and redeployment.

## Decision

Store host presets in `src/store_predict/data/compute_presets.csv`, loaded at
module import time via `load_presets()`. The CSV format is:

```text
name;server_model;cpu_family;cpu_name;cores_per_socket;sockets;ram_gib
```

`load_presets()` accepts an optional `path` parameter so callers can supply a
custom file (e.g., for customer-specific configurations or testing).

```python
# Default — loaded from bundled CSV
DELL_POWEREDGE_PRESETS: list[HostConfig] = load_presets()

# Custom path
my_presets = load_presets(Path("/etc/storepredict/presets.csv"))
```

## Rationale

This mirrors the existing pattern for DRR reference data (`DRR.csv` + `DRRTable`).
Pre-sales engineers are comfortable editing CSV files; they should not need to
understand Python to add a new server model. The CSV also serves as lightweight
documentation of supported configurations.

Graceful fallback: if the CSV is missing or unreadable, `load_presets()` returns
a single `Custom` entry so the UI never crashes.

## Consequences

- **Positive:** New server models added by editing one CSV row — no Python change.
- **Positive:** Consistent with DRR.csv loading pattern (DRY).
- **Positive:** `load_presets()` is testable with fixture CSVs.
- **Negative:** Preset count is no longer a compile-time constant; tests asserting
  `len == 9` must use `>= 9` instead.
- **Constraint:** The `Custom` row must remain the last entry (UI depends on
  `DELL_POWEREDGE_PRESETS[-1].name == "Custom"`).
