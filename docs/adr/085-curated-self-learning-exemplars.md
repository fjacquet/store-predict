# ADR-085: Curated Exemplars + In-Memory Same-File Self-Learning

**Status:** Accepted
**Date:** 2026-05-23
**Issue:** v10.0.0 — Bootstrapping the semantic router with robust, customer-adaptive utterances

## Context

A semantic router (ADR-082) requires exemplar utterances per route to build the embedding
index. The obvious sources were:

1. **DRR.csv descriptions** (`Application/Use case` column): too sparse and too generic
   (`"VMware Virtual Machine"`, `"Microsoft SQL Server"`). These strings embed weakly and do
   not cover the naming conventions customers actually use (`saperp-prd`, `mail-p01`,
   `worker1.oc.vs.ch`).

2. **Existing regex patterns** (from `build_default_rules()`): embedding regex strings
   (`^SAP(?:ERP|NWG).*`) is not meaningful — an embedding model treats them as opaque
   character sequences, not as the product names they match.

3. **Customer VM names from the uploaded file**: real, highly specific, but would commit
   customer data to the codebase if persisted. Also, bootstrapping from the *same file being
   classified* creates a circular dependency if not handled carefully.

## Decision

### Curated base exemplars (persisted)

Maintain `src/store_predict/data/classification_exemplars.yaml`, a hand-curated YAML file
with 23 route keys (one per base DRR category) and 5–15 representative utterances per route.
Utterances are synthetic but representative: they model the product names, acronyms, and VM
naming conventions seen across many real RVTools exports (SQL Server, Oracle, SAP HANA,
Exchange, VDI, Kubernetes, DDVE, FortiNet, etc.).

Encryption/compression subcategory variants (e.g. `Oracle HCC`, `SQL TDE`) are intentionally
excluded from the exemplars: these subcategories are user-toggled overrides in the UI, not
classifier outputs.

This file is version-controlled and ships in the Docker image. It is the only artefact that
encodes domain knowledge about workload naming conventions.

### In-memory same-file self-learning (not persisted)

When a VM is matched by a deterministic override rule (confidence `"override"`), its
normalised VM name is used as an additional utterance for the matching route, injected into
the semantic router's in-memory index before the semantic pass begins. These utterances are
tagged `"<route>|learned"` to distinguish them from curated exemplars.

This means: if the current upload contains 10 VMs that the override rules identify as SAP
HANA (`saphdb-*`, `hana*`), those 10 names are added as SAP HANA exemplars *for this upload*,
making the semantic tier more accurate for any remaining SAP HANA VMs that do not match the
override rules exactly.

**The learned utterances are never written to disk.** Each upload creates a fresh
`SemanticClassifier` instance; the in-memory index is discarded when the upload session ends.
No customer data is persisted or committed.

### What is excluded

- Encryption/compression subcategory variants are not routed by the semantic tier; they
  remain user-toggled checkboxes in the multi-workload dialog.
- The LLM is not used to generate exemplars (the LLM tier is dormant, ADR-084).
- The self-learning mechanism does not update `classification_exemplars.yaml`; human review
  is required before promoting a learned pattern to a curated utterance.

## Consequences

**Positive:**

- Per-file adaptivity: a customer file that uses a consistent naming convention (e.g.
  `sap*-prd` for all SAP components) self-reinforces within the upload, reducing threshold
  sensitivity for that convention.
- Deterministic for a given input file: the set of override-matched VMs is deterministic,
  so the learned utterances are deterministic, so the semantic router's index is deterministic.
- No customer data is committed to git or the Docker image.
- Adding a new workload variant to the exemplars file does not require any code change.

**Negative:**

- The exemplar file is a new maintenance artefact. When DRR.csv gains a new base category,
  a corresponding route must be added to `classification_exemplars.yaml`.
- Self-learning utterances are unreviewed customer data in memory during the upload session.
  The `logging_config.py` sanitization rules (ADR-032) ensure these names are never logged.
- Exemplar quality affects semantic accuracy more than threshold tuning. Sparse or
  unrepresentative exemplars for a route will produce low similarity scores and missed
  classifications.

## Related

- ADR-082: Semantic-router cascade — how the exemplars are consumed.
- ADR-083: FastEmbed encoder — how the exemplars are embedded.
- ADR-032: Log sanitization — ensures learned VM names are never logged.
- ADR-002: DRR ratios from CSV — the reference table that defines valid route names.
