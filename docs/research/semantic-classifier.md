# Semantic Classifier Design (v10.0.0)

**Published:** 2026-05-23
**Domain:** Semantic routing, embedding models, offline classification
**Confidence:** HIGH

## Summary

v10.0.0 replaces the LLM classification fallback with an offline semantic-router tier using
`FastEmbedEncoder` (ONNX). The full design specification is in the
[semantic classifier design spec](../superpowers/specs/2026-05-23-semantic-classifier-design.md)
and the ADRs [082–085](../adr/index.md). This page summarises the cascade, the encoder
rationale, and the tuning workflow.

## Classification Cascade

```
VM Name (raw)
  │
  ▼
normalize()              lowercase, strip domain suffix, collapse whitespace
  │
  ▼
build_override_rules()   deterministic regex, priority ≥ 900
  │  (matched → confidence="override")
  ▼
SemanticClassifier       FastEmbedEncoder + curated exemplars + self-learned utterances
  │  (matched → confidence="semantic", rule="semantic:<route> (score X.XX)")
  ▼
Unknown Reducible        confidence="default"
  │
  ▼
ADR-080 size reroute     ≥100 GiB unknowns → File / General Purpose @ 2.0
```

### Override Rules

`build_override_rules()` returns the subset of `build_default_rules()` with priority ≥ 900.
These are high-confidence, unambiguous product tokens (SQL Server, Oracle, SAP HANA, VDI,
DDVE, healthcare apps, cantonal app families). They fire before the semantic pass to ensure
that cases we can classify deterministically are not left to a probabilistic model.

### Semantic Tier

`SemanticClassifier` wraps `semantic-router`'s `RouteLayer` with `FastEmbedEncoder`. On
construction it:

1. Loads `classification_exemplars.yaml` (23 routes, 5–15 utterances each).
2. Inspects the upload's override-matched VMs and seeds extra in-memory utterances
   (`"<route>|learned"`) for the routes they matched — one utterance per VM, discarded
   when the session ends.
3. Builds the ONNX embedding index.

At inference time, each unclassified VM name is embedded and compared against all route
centroids. If the top-1 similarity exceeds `SEMANTIC_THRESHOLD` (default 0.75), the VM is
assigned to that route.

## Encoder Choice: FastEmbed (BAAI/bge-small-en-v1.5)

| Property | Value |
|---|---|
| Backend | ONNX Runtime (no PyTorch) |
| Model | `BAAI/bge-small-en-v1.5` (33M parameters, 384-dim) |
| Image size increase | ~130 MB model + ~50 MB onnxruntime |
| Runtime dependency | None (model baked into Docker image at build time) |
| Determinism | Fully deterministic (ONNX inference, no sampling) |

The `fastembed<0.4` / `pillow>=12.2.0` version conflict is resolved by declaring
`fastembed>=0.8` directly in `pyproject.toml` rather than using the
`semantic-router[fastembed]` extra. See [ADR-083](../adr/083-fastembed-offline-encoder.md).

## Exemplar Strategy

`src/store_predict/data/classification_exemplars.yaml` contains the curated base exemplars.
Each route entry lists representative VM name fragments:

```yaml
routes:
  - name: "Database / Microsoft SQL"
    utterances:
      - "sqlserver-prd"
      - "mssql01"
      - "db-sql-prod"
      - "sql-cluster-node1"
      # ... 10+ more
  - name: "Database / SAP HANA(S4)"
    utterances:
      - "saphdb-prd"
      - "hana-primary"
      - "s4hana-db01"
      # ...
```

Encryption/compression subcategory variants (Oracle HCC, SQL TDE, etc.) are excluded — they
are user-toggled in the multi-workload dialog, not classifier outputs.

## Self-Learning (In-Memory, Per-Upload)

Before the semantic pass, `SemanticClassifier` examines the override-matched rows in the
current upload's DataFrame and adds each VM's normalised name as an extra utterance for its
matched route (`"<route>|learned"`). This adapts the embedding index to the specific naming
convention of the uploaded file without persisting any customer data.

Example: if the upload contains `saphdb-bpc`, `saphdb-prd`, `saphdb-qas` — all matched by
the HANA override rule — those three names are added as SAP HANA utterances. Any remaining
SAP HANA VM that the override rule does not catch (e.g. `hana-standby-01`) is more likely to
be picked up by the semantic tier.

## Threshold Tuning

`scripts/tune_semantic_thresholds.py` is a standalone harness for calibrating
`SEMANTIC_THRESHOLD`:

```bash
.venv/bin/python scripts/tune_semantic_thresholds.py \
    --input samples/rvtools_sample.xlsx \
    --ground-truth samples/ground_truth.csv \
    --threshold-range 0.60 0.95 0.05
```

The script evaluates precision/recall for each threshold value and prints a table. The
recommended default (0.75) balances unknown-recall vs. false-positive rate on the reference
customer file.

## Key Findings from the Reference Customer File

On the Valais-canton estate (1373 VMs after template filtering):

- Override rules match ~40% of VMs with high confidence (HANA, SAP app, Email, Containers,
  etc.).
- Self-learned utterances from those ~550 override-matched VMs improve semantic recall for
  the remaining ~820.
- After semantic pass, Unknown VMs dropped from ~40% (v9.x rules-only) to ~0%.
- SAP HANA, Email/Exchange, and DDVE buckets are preserved exactly as in v9.x (override tier).
- Weighted DRR and required capacity figures are stable vs. v9.1.0 (the semantic tier
  classifies previously-Unknown VMs, improving accuracy without changing known-good results).
