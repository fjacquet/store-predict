# ADR-053: Application-level DRR degradation as CSV subcategory variants

**Date:** 2026-02-20
**Status:** Accepted

## Context

PowerStore's published DRR benchmarks assume **reducible data** — data that has not
already been processed by application-layer encryption or compression. When an
application performs deduplication, compression, or encryption before data reaches
the array, PowerStore's inline engine achieves significantly lower ratios.

Three families of application-level reduction were identified (see research page
`phase-14-app-level-drr-variants.md`):

1. **Application compression** (Oracle HCC, SQL Server Page Compression, MongoDB
   WiredTiger) — removes the block-level redundancy that array dedup targets.
2. **Encryption** (Oracle TDE, SQL Server TDE, pgcrypto, LUKS) — randomises the
   bitstream, making blocks incompressible and appearing unique. Dell KB000267460
   classifies host-encrypted data as "unreducible".
3. **Backup agent source-side dedup** (Veeam with compression+dedup enabled,
   Commvault, DDVE) — exhausts reduction opportunities before data reaches the array.

## Decision

Model these scenarios as **additional subcategory rows in DRR.csv** rather than
adding code logic to the classification engine or calculation layer.

The existing `(category, subcategory) → DRR float` lookup in `DRRTable` already
provides the necessary flexibility. New rows such as:

```text
Database;Oracle - TDE (Encrypted);1.5
Database;Oracle - HCC + TDE;1.2
VM Replication;Data Domain Virtual Edition (DDVE);1.0
```

…appear automatically in the workload dropdown on the review page without any UI
code changes. Pre-sales engineers can manually select the appropriate variant when
they know a VM uses encryption or source-side compression.

Companion classifier rules (priority 88–97) match common naming conventions
(e.g. `ORACLE-TDE-01`, `SQL-PAGE-DB`) to auto-assign variants for recognisable
names. Classifier patterns use regex lookaheads for combined scenarios
(e.g. a VM name containing both "ORACLE", "HCC", and "TDE" → "Oracle - HCC + TDE").

## Consequences

- **DRR.csv** is the single source of truth for all DRR values, including
  application-level degradation scenarios — no ratios are hardcoded anywhere else.
- Adding a new scenario (e.g. "Oracle TDE + ASM") requires only a new CSV row and,
  optionally, a new classifier rule — no code changes to pipeline or UI.
- Automatic detection via VM names is heuristic: many encrypted VMs will not have
  "TDE" or "ENC" in their name. Manual selection via the dropdown remains the primary
  workflow for confirmed encrypted workloads.
- The conservative (lowest) DRR principle (ADR-005) still applies when a VM has
  multiple workloads assigned, including encrypted variants.
