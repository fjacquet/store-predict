# ADR-082: Semantic-Router as Primary Classifier (v10.0.0)

**Status:** Accepted
**Date:** 2026-05-23
**Issue:** v10.0.0 — Deterministic regex list unmaintainable; LLM fallback slow and flaky

## Context

Through v9.x, the classification cascade was:

1. Deterministic `build_default_rules()` (priority 0–950) — regex substring matching.
2. OS fallback (priority 100) — Windows/Linux signals.
3. LLM fallback (priority 0) — litellm/Ollama for unclassified VMs.
4. ADR-080 size-reroute — ≥100 GiB unknowns → `File / General Purpose @ 2.0`.

Two failure modes emerged that made this pipeline untenable in production:

**Regex sprawl.** The rule list grew to 80+ rules covering product names, acronyms, cantonal
app families, SAP component names, and OpenShift topology tokens. Adding rules required
careful priority ordering to avoid stealing matches from earlier rules (e.g. `SAPMSSQL` must
outrank a generic `SAP` rule). The list was increasingly fragile: a new rule for one customer
silently broke another.

**LLM flakiness.** The LLM fallback (ADR-051) turned out to be unreliable in practice:
reasoning/thinking models (`lfm2.5-thinking`, `deepseek-r1`) emit `<think>...</think>`
blocks the parser had to strip; instruct models hallucinated valid-looking but wrong category
strings; network latency made large uploads stall visibly; the circuit breaker masked silent
parse failures. The feature was never enabled by default, and disabling it left a hard
Unknown floor.

## Decision

Replace the LLM fallback tier with a **semantic-router** tier using `FastEmbedEncoder` (ONNX,
offline, see ADR-083). The new cascade is:

```
normalize(vm_name)
  → override rules  (build_override_rules, priority < 900)
  → semantic router (FastEmbedEncoder + curated exemplars, see ADR-085)
  → default         (Unknown Reducible, confidence="default")
  → ADR-080 size reroute (applied after classification)
```

The existing `build_default_rules()` is refactored into two functions:

- `build_override_rules()` — high-confidence, high-priority rules (priority < 900) that must
  fire before any learned or semantic logic. These cover cases where the product/app token is
  unambiguous: `MSSQL`, `ORACLE`, `HANA`, `VDI`, `SAP HANA`, `DDVE`, known healthcare and
  cantonal app families. Typically 25–35 rules.
- `build_default_rules()` — retained for backward compatibility; now returns the full rule
  set including override rules. This is not used in the active pipeline.

Classification confidence values:

| Tier | `classification_confidence` value |
|---|---|
| Override rule matched | `"override"` |
| Semantic router matched | `"semantic"` |
| No match (unknown) | `"default"` |

(`rule_match` and `os_fallback` are registry-internal confidences from `build_default_rules`; the v10 active pipeline emits only `override`, `semantic`, `default`.)

The `classification_rule` field records the matched rule name for override hits, or
`"semantic:<route> (score X.XX)"` for semantic hits, giving a human-readable audit trail.

## Consequences

**Positive:**

- Unknown VMs on the reference customer file (1373 VMs, Valais canton) dropped to ~0.
  Previously 40–60% fell through to the LLM or remained Unknown; now the semantic tier
  captures them against curated exemplars.
- SAP HANA, Email/Exchange, and DDVE buckets are preserved via override rules — the
  deterministic rules that exist for a reason are not thrown away, just prioritised correctly.
- The semantic score is recorded and logged, making classification explainable and tunable
  via the threshold harness (`scripts/tune_semantic_thresholds.py`).
- No runtime network dependency: FastEmbed runs fully offline.
- Adding a new workload category is example-driven: add utterances to
  `classification_exemplars.yaml`, no regex surgery needed.

**Negative:**

- The ONNX model (~130 MB) and `onnxruntime` are added to the Docker image (see ADR-083).
- Semantic routing is probabilistic; a mis-tuned threshold can steal matches. Mitigated by
  the override tier and by the threshold tuning harness.
- The `semantic-router` package's transitive `pillow<11` constraint conflicts with this
  project's `pillow>=12.2.0`; resolved by depending on `fastembed>=0.8` directly
  (see ADR-083).

## Related

- ADR-051: LLM rule-suggestion feedback loop — superseded for the active pipeline; LLM
  module kept dormant (see ADR-084).
- ADR-080: Size-based reroute — still the final safety net after classification.
- ADR-083: FastEmbed encoder choice.
- ADR-084: LLM fallback retirement.
- ADR-085: Curated exemplars + same-file self-learning.
