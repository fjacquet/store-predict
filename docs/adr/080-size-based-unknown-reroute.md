# ADR-080: Size-Based Reroute for Unknown VMs ≥100 GiB

**Status:** Accepted
**Date:** 2026-05-01
**Issue:** v9.0.0 — Sizing risk on real customer files

## Context

Audit of two real customer RVTools exports (May 2026 multi-vCenter, 1373 VMs; Jan 2026 single-vCenter, 570 VMs) revealed a structural sizing risk that the deterministic ruleset alone could not close.

On the Jan 2026 file: after v8.3.2, **365 VMs (64% of the inventory)** still landed in the generic `Virtual Machines / VMware / Hyper-V / KVM…` bucket because they had no recognisable product token. Those 365 VMs collectively held **330.8 TiB** of provisioned storage. At the existing default DRR=5 the tool predicted only 66 TiB of PowerStore need; at a defensible 2.5:1 (the floor pre-sales would size against unknown data-bearing inventory) the real need is ~132 TiB. **Sizing gap: ~66 TiB undersizing on a single customer.**

The size distribution refuted the implicit assumption that "generic Windows / Linux server = OS-only, ~5:1 reducible":

| Provisioned | VMs | Sub-total |
|---|---:|---:|
| <100 GiB (true OS-only) | 15 | 0.9 TiB |
| 100–500 GiB | 172 | 56 TiB |
| 500 GiB – 1 TiB | 116 | 78 TiB |
| 1–2 TiB | 32 | 47 TiB |
| **>2 TiB** | **30** | **155 TiB** |

96% of the bucket was data-bearing. A blind 5:1 default on this volume oversells the array.

Three designs were considered:

1. **In-rule size matching.** Add `size_min` / `size_max` fields to `ClassificationRule` and have rules reason about provisioned size. Polluted every rule's signature; size logic spread across the rule list; inconsistent with the "rules are pure pattern matchers" abstraction.
2. **Multiplicative DRR adjustment in `calculation.py`.** Scale `drr` by a size factor when `confidence == "os_fallback"`. Worked for math but produced a UX schism: the review grid showed DRR=5, but the calculation used 2.5. Pre-sales engineers couldn't defend the number they showed the customer.
3. **Post-classification reroute in `classify_dataframe`.** Override only the `(category, subcategory)` of unknown VMs ≥100 GiB to a new DRR.csv subcategory. Visible in the UI and the PDF, defensible, doesn't touch the rule engine.

## Decision

Adopt option 3.

- Add a new DRR subcategory `Virtual Machines / Large data-bearing (>100 GiB unknown)` at **DRR=2.5** in `samples/DRR.csv`.
- After `RuleRegistry.classify()` returns, `classify_dataframe()` checks: if `confidence in {"os_fallback", "default"}` AND `subcategory in {"VMware / Hyper-V / KVM - No Database, File nor Email", "Unknown (Reducible)"}` AND `provisioned_mib >= 100 * 1024`, replace the verdict with the Large data-bearing subcategory. The `rule_name` becomes `"Large generic (>=100 GiB)"`; `confidence` stays unchanged (preserves provenance).
- Specific app rules (`rule_match`) are **never** rerouted. A 1 TiB Oracle VM keeps DRR=5 — that's a Dell-validated number for that workload.

Threshold and DRR are constants in `pipeline/classification.py` for easy tuning:

```python
LARGE_VM_THRESHOLD_MIB: int = 100 * 1024  # 100 GiB
_UNKNOWN_SUBCATEGORIES: frozenset[str] = frozenset({
    "VMware / Hyper-V / KVM - No Database, File nor Email",
    "Unknown (Reducible)",
})
```

## Consequences

**Positive:**

- Closes the largest sizing risk in the tool. On the Jan 2026 file: 351 VMs reroute to Large data-bearing; the generic VMware bucket drops from 365 → 18 (only true OS-only <100 GiB). Sizing prediction goes from 66 TiB to 132 TiB — defensible.
- Preserves UI honesty: the review grid and PDF now show "Large data-bearing (>100 GiB unknown)" with DRR=2.5, so pre-sales can defend the number.
- Specific app rules untouched (Dell-validated Oracle/SQL/SAP DRRs preserved on large data-bearing apps).
- The threshold is one constant in one file; future tuning trivial.

**Negative:**

- Major version bump (8.3.2 → 9.0.0) signals a behaviour change. Existing customer projects re-run through v9 will see different sizing output for VMs that previously fell into the generic bucket.
- Pre-sales convention assumption: 2.5:1 floor on unknown data-bearing inventory. Some customers may want 2:1 or 3:1; today this is fixed in the DRR.csv ratio.
- Customers without a `provisioned_mib` column (none today, but theoretically possible) get no reroute — `classify_dataframe` checks for the column and skips the reroute when absent.

**Mitigation:**

- 10 new tests in `tests/test_classification.py::TestV900PatternsAndSizeAware` cover the threshold boundary (exactly 100 GiB), small-VM no-reroute, large-default reroute, large-rule_match no-override, missing-column safety, and the 3 new patterns (INSIGHTIQ, SECDB, FORTIA\d).
- `tests/test_real_customer_baseline.py` adds `test_v900_large_databearing_takes_unknown_volume` to assert the bucket sizes on the real file.
- The size-aware reroute is post-processing only — the rule registry remains a pure data structure usable elsewhere (e.g. the LLM rule-suggestion loop in `pipeline/llm_classifier.py`).

## Amendment — v9.0.1 (2026-05-20)

The DRR for `Virtual Machines / Large data-bearing (>100 GiB unknown)` is lowered from
**2.5 to 2.0 (2:1)**. The 2.5:1 floor was judged too optimistic for inventory we could
not classify by signature; 2:1 is a more conservative, defensible floor for truly-unknown
large data-bearing VMs. This realises the tuning lever already noted in this ADR
(see "Negative": *"some customers may want 2:1 or 3:1"*, and "Related": *">1 TiB → DRR=2.0"*).

Only the ratio changes — the reroute logic, the `LARGE_VM_THRESHOLD_MIB` threshold, the
`_UNKNOWN_SUBCATEGORIES` set, and the subcategory name are unchanged. The v9.0.0 Decision,
Consequences, and impact tables above are preserved as history; their figures
(e.g. "66 TiB → 132 TiB") were computed at 2.5:1. At 2:1 the predicted PowerStore need on
the same inventory is correspondingly higher.

## Related

- ADR-079: Description fallback opt-in per rule (v8.3.1).
- ADR-077: Composite (category, drr) groupby for WorkloadGroupResult — the new subcategory flows through the existing aggregation without changes.
- Future: a v9.x evolution could split the Large bucket further (e.g. >1 TiB → DRR=2.0) or LLM-enrich the os_fallback path before reroute. Out of scope here.
