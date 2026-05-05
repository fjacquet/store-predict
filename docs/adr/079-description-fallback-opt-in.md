# ADR-079: Classification Description Fallback Is Opt-In Per Rule

**Status:** Accepted
**Date:** 2026-05-01
**Issue:** v8.3.1 hotfix — Veeam over-classification on real customer file

## Context

The classifier evaluates each VM through a two-pass pipeline (`pipeline/classification.py::RuleRegistry.classify`). Pass 1 matches `vm_name_patterns` against the VM hostname; pass 2 retries unmatched rules against the vCenter `Annotation` field as a description fallback. Up to v8.3.0, **every rule that defined `vm_name_patterns`** participated in pass 2 — the description fallback was on by default.

A real customer RVTools export (`RVTools_export_all_2026-01-07_10.23.35.xlsx`, 570 powered-on VMs) revealed that this default is unsafe. Veeam writes its backup metadata into the same Annotation field:

```text
Last backup: [06.01.2026 21:20:13]; Veeam server: [sphfrbkp01];
Job: [HFR - Gold - Standard - DC1]; Repository: [sobr-hfr-immutable-dc1]
```

The literal word `Veeam` then fired the priority-300 "VM Replication / Veeam, Zerto, RP4VM" rule on **375 VMs (66%)** that were merely backed up by Veeam — including pure Exchange, Domain Controllers, and Active Directory Connect VMs. The same systemic risk existed for any rule whose product token might appear in admin-written or tool-written descriptions (Domino, Cisco UCS strings, Tenable, Forti…).

Two designs were on the table:

1. **Keep the default-on behaviour and excise specific noisy substrings** (e.g. strip `"Veeam server:"` before matching). Brittle: every backup vendor adds its own free-text format, and any future rule whose token appears in any description re-introduces the bug.
2. **Make description fallback opt-in per rule.** Rules that genuinely depend on description signals (OVA / appliance annotations like "Nutanix Controller VM", "BeyondTrust Secure Remote Access Appliance") explicitly set `match_description=True`. Every other rule ignores the description.

## Decision

Adopt option 2. Add `match_description: bool = False` to `ClassificationRule`. The new default is OFF. `matches()` consults the description only when the rule has opted in *and* the VM-name didn't match.

Eleven OVA-annotation signature rules opt in: Cisco Unified Communications (250), Nutanix CVM (294), Dell PowerProtect (299), vCenter / vSAN Witness (396), FortiDeceptor (401), BeyondTrust / Bomgar (430), Tenable / Nessus (435), NetApp OnCommand UM (450), Horizon3.ai NodeZero (460), exotrack (465). Every other rule (VM Replication, Email, Database, VDI, Web Servers…) keeps the safer default.

## Consequences

**Positive:**

- The Veeam-annotation false-positive (375 VMs in this dataset) is closed at the root.
- A whole class of latent bugs (any future rule whose product token appears in any description) is prevented by construction.
- The behaviour of every rule is now explicit and grep-able — `match_description=True` is a deliberate signal of "this rule is meant to fire on annotations."
- `os_fallback` count rises (correct Windows / Linux fallback) and `rule_match` count drops on the same dataset — fewer over-confident classifications.

**Negative:**

- Customers who relied on free-text admin notes ("Oracle Database Server" written in the Annotation) lose that path. We judged this trade-off favourable: the false-positive volume on tool-written annotations is far larger than the upside from manual annotations.
- One existing test (`test_classification_with_description`) was repurposed to assert the new semantics — it now verifies that a non-opt-in rule does NOT fire from description.

**Mitigation:**

- Five regression tests in `tests/test_classification.py::TestDescriptionFallbackOptIn` cover the Veeam case (`test_veeam_description_does_not_overmatch_*`), the new EXCH short-token (`SPHFREXCH01-04`), and confirm BeyondTrust + Nutanix signatures still work via the opt-in path.

## Related

- ADR-051: LLM rule suggestion loop — description signals remain valuable for the LLM enrichment path; that path is independent and unaffected.
- v8.3.0 introduced folder-aware classification (`folder_patterns`) — this hotfix does not change that machinery.
