# ADR-081: Application-Aware Classification Rules for App-Named VM Estates

**Status:** Accepted
**Date:** 2026-05-22
**Issue:** v9.1.0 — Indefensible "everything is 2:1" sizing on app-named estates

## Context

A real RVTools export (Valais-canton multi-domain estate, `*.vs.ch`; 803 VMs, 791 after
template filtering, 948.8 TiB provisioned) exposed a blind spot in the deterministic ruleset.

This customer names VMs by **application** (`saperp-prd`, `mail-p01`, `worker1.oc.vs.ch`,
`abacus-p01`) with `-P/-T/-D` environment suffixes — not the `SQL*/ORA*/VDI*` product tokens
the rules match on. Result before this change:

- Only **100 of 791 VMs** (319 TiB) hit a specific rule. 678 fell to OS-fallback.
- The ≥100 GiB size-reroute (ADR-080) then caught **679 VMs / 628.8 TiB** → `File / General
  Purpose @ 2.0`.
- **90% of capacity (857 TiB) sat in one bucket.** Weighted DRR **2.02:1**, required 470.1 TiB.

The number was conservative but not *accurate* and could not be defended line-by-line — every
large app server looked like an anonymous "File / General Purpose" blob.

The size-reroute (ADR-080) is the correct **safety net** for genuinely-unidentified
data-bearing VMs, but it should not be the *primary* classifier for VMs we can in fact
identify. The fix is to recognise the application families, not to weaken the floor.

## Decision

Extend `build_default_rules()` with rules for the families that could be **positively
identified** (by web research of the products, or by unambiguous structural signal). Each maps
to an **existing** `DRR.csv` (category, subcategory) — no new reference rows. Unidentified
bespoke cantonal apps are **deliberately left** to the ADR-080 floor.

Optimisation target (confirmed with the requesting pre-sales engineer): **accurate &
defensible**, not maximal reduction.

| Family signal | → Category / Subcategory | DRR | Direction |
|---|---|---|---|
| `^SAP(ERP\|NWG\|BOBI\|BODS\|BPC\|ADS\|CCM\|SOM\|CUA\|BCOM\|ENOW\|COCKPIT\|LICENSE\|FRONT)` | Database / SAP Traditional (R/3 / ECC) | 5.0 | ↓ capacity |
| `\bMAIL\b` | Email / Exchange… | 2.0 | neutral |
| `MAILARCH`, `VIDEOMGMT` | File / Archive (Rich Media) | 1.0 | ↑ capacity |
| `^worker\d`, `^master\d`, `^bootstrap` | Containers / Kubernetes… | 2.0 | neutral |
| `KENDOX/AUTOSTORE/AUSTORE/YOUDOC/OTRECM/DOCPRO/^ECM` | File / Content Servers | 2.0 | neutral |
| `ARTIFACT`, `CICD` | File / Developer Workspaces (DevOps) | 2.0 | neutral |
| `^MONITOR` | Logging - Analytics | 1.5 | ↑ capacity |
| `(INFRA\|JUS\|INFRAPOL\|EXPLOIT)DC` | Virtual Machines | 5.0 | ↓ capacity |
| `ABACUS/MIDPOINT/METADIR/MESSERLI/TALEND/EYEGLASS` | Virtual Machines | 5.0 | ↓ capacity |

Key design choices, consistent with existing conventions:

- **SAP app vs HANA split.** The SAP-application regex is start-anchored on component names,
  so `saperp`/`sapnwg`/`sapbpc` → Traditional (5:1, NetWeaver/app tiers) while `saphdb-bpc`
  stays SAP HANA(S4) (2:1) via the higher-priority HANA rules. Confirmed by the customer that
  HANA databases carry `HDB`/`HANA` in their names. `sapmssql` still wins Microsoft SQL.
- **Start-anchored generics.** `^master\d` / `^worker\d` / `^ECM` / `^MONITOR` are anchored so
  they do not match mid-name tokens (`opsmaster-p03` is *not* an OpenShift node; `secmaster` is
  not ECM).
- **DC prefix-qualified.** `\b(?:INFRA|JUS|INFRAPOL|EXPLOIT)DC\b` matches the cantonal AD
  domain controllers without capturing the Citrix Delivery Controller `DDC` (`ctxddcpol`,
  `ddc-*`).
- **Conservative floor preserved.** ~280 bespoke families (`benwue`, `lacepol`, `cmikes`,
  `geres`, `seccenpol`, `sitvalgis`, GIS imagery, …) match no new rule and remain on the
  ADR-080 ≥100 GiB `File / General Purpose @ 2.0` reroute. We do **not** claim 5:1 on
  inventory we cannot defend — exactly the risk ADR-080 was created to avoid.

## Consequences

**Positive:**

- rule_match VMs rise **100 → 358**; the generic File bucket drops from 857 → 525 TiB. Weighted
  DRR **2.02 → 2.10:1**, required **470.1 → 452.2 TiB**. More importantly, the *labels* are now
  defensible: 9 Email VMs, 87 Containers, 65 SAP, 47 DMS content servers, etc.
- The biggest lever (SAP, −19.4 TiB) is a customer-confirmed app/DB split, not an assumption.
- Conservative corrections (mail-archive + video → 1:1, monitoring → 1.5:1) move sizing *up*
  where the data is genuinely incompressible.
- The new rules generalise: most patterns (SAP components, OpenShift nodes, mail, monitoring,
  DMS products, Artifactory) benefit any customer file, not just this one.

**Negative:**

- Some customer-specific tokens enter the global registry (cantonal DC prefixes, a handful of
  Swiss products). This follows the established precedent of the HealthCare rule (ADR
  predecessor) which already lists many Swiss/French cantonal app names with inline citations.
- `\bMAIL\b` and `^MONITOR` are broader than a product token; mitigated by anchoring/word
  boundaries and by the fact their targets (Email 2.0, Logging 1.5) are close to the floor.

**Mitigation:**

- `tests/test_classification.py::TestCustomerAppPatterns` — 15 tests covering each new rule with
  positive cases plus the critical negatives: `saphdb-bpc` stays HANA, `sapmssql` stays SQL,
  `opsmaster` is not OpenShift, `ddc`/`ctxddcpol` are not domain controllers, and bespoke apps
  (`benwue`, `lacepol`, `cmikes`, `geres`) stay at `os_fallback`/`default` confidence.

## Related

- ADR-080: Size-based reroute for unknown VMs ≥100 GiB — the safety net this ADR layers
  identification on top of. Unidentified families still rely on it.
- ADR-005: Most conservative DRR for multi-workload VMs — same defensibility philosophy.
- ADR-002: DRR ratios from CSV — every new rule references an existing reference-table entry.
