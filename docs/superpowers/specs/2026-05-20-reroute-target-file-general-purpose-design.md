# Design: Route large-unknown VMs to `File / General Purpose` (retire synthetic category)

**Date:** 2026-05-20
**Status:** Approved (brainstorming) — pending implementation
**Amends:** ADR-080 (size-based reroute for unknown VMs ≥100 GiB)
**Target version:** v9.0.2 (patch)

## Context

v9.0.0 introduced a size-aware reroute (ADR-080): unknown VMs (`os_fallback`/`default`
confidence) with `provisioned_mib >= 100 GiB` route to a **synthetic** DRR subcategory
`Virtual Machines / Large data-bearing (>100 GiB unknown)` (lowered to DRR 2.0 in v9.0.1).

That category is not a real workload type — it was invented purely as a reroute target.
The goal of this change is for the classifier to emit **only canonical DRR.csv categories**.
The chosen destination is the existing `File / General Purpose` entry, which is the most
neutral existing category already at DRR 2.0.

## Decision

Reroute large-unknown VMs to `File / General Purpose` instead of the synthetic category,
and delete the synthetic row from DRR.csv.

- **No sizing change.** `File / General Purpose` is DRR 2.0, identical to the value the
  synthetic category carried after v9.0.1. Required-capacity output is unchanged.
- **Provenance preserved.** The reroute keeps `rule_name = "Large generic (>=100 GiB)"`
  and preserves the original `confidence` (`os_fallback`/`default`). Size-rerouted unknowns
  therefore remain fully distinguishable in the data from genuinely-classified file servers
  (which carry the real File rule name). We stop inventing a *category label*, not the trail.
- **Trigger unchanged.** `LARGE_VM_THRESHOLD_MIB` (100 GiB), `_UNKNOWN_SUBCATEGORIES`, and
  the `confidence in {"os_fallback","default"}` gate are all unchanged.

### Accepted trade-off

The review grid / PDF will show `File / General Purpose` for these unknowns rather than an
explicit "unknown ≥100 GiB" label. This is the cost of the no-synthetic-categories goal.
`rule_name` is the escape hatch if surfacing "size-rerouted" in the UI is ever wanted
(out of scope here — YAGNI).

## Changes

### Source
- `src/store_predict/pipeline/classification.py` — in the `classify_dataframe()` reroute
  block, set `category="File"`, `subcategory="General Purpose"` (keep `rule_name` and
  `confidence`). Update the surrounding module comments and the function docstring that
  reference "Large data-bearing".
- `src/store_predict/data/DRR.csv` — delete the
  `Virtual Machines;Large data-bearing (>100 GiB unknown);2.0` row. Mirror in the gitignored
  `samples/DRR.csv` for local consistency.

### Tests
- `tests/test_drr_table.py` — entry count assertion 43 → **42** (update docstring); remove
  `test_large_data_bearing_drr`; add `test_file_general_purpose_drr` asserting
  `get_ratio("File", "General Purpose") == 2.0` to lock the reroute target's ratio.
- `tests/test_classification.py` — the three reroute tests
  (`test_large_unknown_vm_reroutes_*`, `test_threshold_boundary_exact_100gib`) assert
  `workload_category == "File"` and `workload_subcategory == "General Purpose"`; the
  `classification_rule == "Large generic (>=100 GiB)"` and `classification_confidence`
  assertions are unchanged. Update the `TestV900PatternsAndSizeAware` docstring.
- `tests/test_classification_integration.py` — remove the now-dead
  `uncovered.discard(("Virtual Machines", "Large data-bearing (>100 GiB unknown)"))` line
  (the category no longer exists in DRR.csv; `File / General Purpose` is rule-covered).
- `tests/test_real_customer_baseline.py` — in
  `test_v900_large_databearing_takes_unknown_volume`, count rerouted VMs by
  `classification_rule == "Large generic (>=100 GiB)"` instead of by subcategory (so real
  File/General Purpose servers are not conflated); keep `n_large >= 600` and generic `<= 350`.

### Docs & version
- `CHANGELOG.md` — new `## [v9.0.2] - 2026-05-20` entry.
- `docs/adr/080-size-based-unknown-reroute.md` — second dated amendment recording the
  reroute target change (synthetic → `File / General Purpose`) and the rationale
  (classifier emits only canonical categories). Prior content preserved.
- `docs/architecture.md` — update the reroute description to `File / General Purpose`.
- `docs/adr/index.md` — update the ADR-080 summary line.
- `pyproject.toml` — `9.0.1` → `9.0.2`.

## Verification

1. `pytest` — expect the prior pass count (the customer baseline is file-gated and asserts
   counts only, now keyed on `rule_name`).
2. `ruff check .` + `ruff format --check .` + `mypy src/`.
3. Optional `mkdocs build` to confirm ADR/architecture edits render.

## Out of scope

- UI surfacing of "size-rerouted" provenance.
- Any change to the 100 GiB threshold or the DRR value (stays 2.0).
- The historical 2.5-based figures in the v9.0.0 CHANGELOG/ADR body (preserved).
