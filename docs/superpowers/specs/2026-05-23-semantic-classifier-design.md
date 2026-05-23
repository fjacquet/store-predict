# Design: Semantic Classifier (v10.0.0)

**Date:** 2026-05-23
**Status:** Draft — pending user review
**Branch:** `feat/semantic-classifier-v10` (cut from `maincd` @ `90eb6fc`)
**Supersedes / relates to:** ADR-081 (app-aware rules), the LLM classification fallback (ADR for `llm_classifier`)

## 1. Problem & Goal

StorePredict classifies VMware workloads into DRR categories so pre-sales engineers can size
PowerStore arrays. Today classification is a deterministic regex `RuleRegistry`
(`build_default_rules`) followed by an optional Ollama LLM fallback for `default`-confidence VMs.

**Goal:** modernize the classifier so a local **semantic-router** layer becomes the *primary*
classification mechanism, with the regex engine demoted to a small set of high-precision,
must-win **overrides**. This should be more maintainable (example-driven instead of an
ever-growing regex list), fully offline, and cheaper/faster than the LLM path — while never
regressing the real-customer baseline.

This is shipped as a **breaking major version (v10.0.0)** on a dedicated branch. The real-customer
baseline test is the **merge gate** before anything reaches `maincd`.

## 2. End-State Cascade

Per VM, evaluated in order:

```
raw VM(name, os, description, folder)
   │
   ├─① Normalize        keep today's preprocessing: company-prefix + role-prefix stripping
   │
   ├─② Overrides        high-precision must-win keyword rules (subset of today's rules):
   │                    SQL, Oracle, SAP/HANA, VDI/Citrix, Exchange, Veeam, K8s, Nutanix-CVM, …
   │                    hit → confidence="override", done
   │
   ├─③ Semantic route   FastEmbed SemanticRouter over curated + self-learned exemplars
   │                    score ≥ route threshold → confidence="semantic", record route + score
   │                    below threshold → fall through
   │
   └─④ Default          "Unknown (Reducible)" (DRR 5), confidence="default"

   ⑤ Post-pass          ADR-080 numeric size-reroute (≥100 GiB generic → File/General Purpose)
```

**Why ② and ⑤ stay deterministic:** embeddings are *worse* at exact-token disambiguation
(word-boundary `SQL`/`DB2`, prefix stripping, folder-qualified `match_mode="all"`) and at the
purely numeric size reroute. The semantic tier owns the genuinely fuzzy long tail that today's
brittle medium-priority rules and the LLM handled.

There is **no LLM tier** in the active pipeline. The `llm_classifier` module is kept **dormant**
(unwired, not deleted) so it remains available and its tests stay green.

## 3. Modules — Create / Modify / Keep-Dormant

### Create
- `src/store_predict/pipeline/semantic_classifier.py`
  `SemanticClassifier` wrapping a FastEmbed `SemanticRouter` (default model
  `BAAI/bge-small-en-v1.5`, ~130 MB ONNX). Responsibilities: build the index
  from exemplars; classify one VM → `(category, subcategory, route_name, score)`; grow the
  in-memory index from same-file override hits. Maps route name → `(category, subcategory)`.
- `src/store_predict/data/classification_exemplars.yaml`
  Curated, **synthetic/anonymized** utterances per **base** category, seeded from the DRR.csv
  "Application/Use case" text + the existing rule keywords (generic, not customer data).
  Encryption/compression subcategory variants (`Oracle - TDE`, `MS SQL - Page Compressed + TDE`,
  …) are **never** auto-classified — they remain user-selected toggles in the Scope UI.
- `src/store_predict/services/semantic_config.py`
  pydantic-settings config (mirrors `LLMConfig`): model name, global + per-route thresholds,
  self-learning on/off, enable flag. Threshold defaults are populated from the tuning harness.
- New ADRs (see §8).

### Modify
- `src/store_predict/pipeline/classification.py`
  Keep normalization helpers (`strip_company_prefix`, `_strip_role_prefix`, pattern helpers),
  `ClassificationRule`, `ClassificationResult`, `RuleRegistry`. Add `build_override_rules()`
  (the must-win subset of `build_default_rules()`). Rewire `classify_dataframe()` to the new
  cascade (overrides → semantic → default), keeping the ADR-080 numeric reroute post-pass.
  Decision: keep `build_default_rules()` for now (used by dormant LLM tests / fallback parity)
  but the active pipeline calls `build_override_rules()`.
- `src/store_predict/ui/pages/upload.py::_run_pipeline`
  Replace the rules+LLM block with overrides → semantic → default, all via `run.io_bound`.
  New progress + notification messages; remove the active `classify_unknown_vms_async` call and
  `save_rule_suggestions` wiring (the function/module stay defined, just unused).
- `pyproject.toml`
  Add `semantic-router[fastembed]` (pinned). Bump `version = "10.0.0"`. Keep `litellm` (dormant).
- `src/store_predict/i18n/locales/{en,fr}.yaml`
  Add `semantic.*` keys (classifying, progress, error). Retire `llm.*` keys no longer surfaced in
  the active UI (keep any still referenced by dormant code paths).
- `Dockerfile`
  Pre-bake the FastEmbed ONNX model into the image at build time so the running container needs
  no network on first use (fully offline).

### Keep dormant (do NOT delete)
- `src/store_predict/pipeline/llm_classifier.py` and `tests/test_llm_classifier.py` — unwired from
  the pipeline but retained, compiling and passing. `LLMConfig`, `litellm`, and `save_rule_suggestions`
  remain in the tree. Re-wiring is a config/UI change away if ever needed.

## 4. Confidence & Provenance Model

Active confidence values become `{override, semantic, default}` (the legacy `os_fallback`/`llm`
values stay *defined* for the dormant code but are not produced by the active cascade):

| Confidence | `classification_rule` value                         | Meaning                              |
|------------|-----------------------------------------------------|--------------------------------------|
| `override` | `override:<RuleName>`                                | Deterministic must-win keyword match |
| `semantic` | `semantic:<route> (score 0.84)`                      | Vector match at/above threshold      |
| `default`  | `default`                                            | Below threshold → Unknown (Reducible)|
| (reroute)  | `Large generic (>=100 GiB)`                          | ADR-080 numeric post-pass            |

Provenance stays explainable and queryable in the Scope/review UI — the similarity score is
recorded so a semantic call is defensible to a customer.

## 5. Router Lifecycle & Self-Learning

- **Build once** at app startup: load `classification_exemplars.yaml` → `FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")`
  → `SemanticRouter` with committed per-route thresholds. Hold as a module-level singleton (the
  model load + base-utterance embedding is the expensive part; do it once).
- **Per upload:** classify against the shared base index. Before the semantic pass, take VMs that
  ②-overrides matched with high precision *in this file*, and `router.add(...)` their normalized
  names as extra utterances for the matching route; then classify the still-unmatched VMs.
  **In-memory only, never persisted, discarded after the upload.**
- **Determinism:** same input file → same output (override matches are deterministic; FastEmbed +
  pinned model + fixed exemplars + fixed thresholds are reproducible). Results differ across
  *different* files because the self-learned exemplars differ — this is input-dependent, not random.

## 6. Threshold Tuning

`scripts/tune_semantic_thresholds.py` (dev/CI only, not shipped at runtime) runs
`router.fit(X, y)` / `router.evaluate(X, y)` against the anonymized baseline fixtures to choose
per-route thresholds. The resulting thresholds are committed into `semantic_config.py` defaults.
Re-run whenever exemplars change.

## 7. Error Handling, Determinism & Security

- Encoder/model-load failure or a per-VM embedding error → that VM falls to `default` (Unknown);
  an upload **never** crashes on classification. Errors logged as **counts only**.
- Empty/whitespace `name`+`os`+`description` → straight to `default`, skip embedding.
- **Security:** preserve the existing rule — never log VM names or DataFrame contents; only counts
  and status. Exemplars committed to the repo are synthetic/anonymized only.
- Pin `semantic-router` version and the FastEmbed model name for reproducibility.

## 8. Testing Strategy

- **Baseline is the merge gate:** `tests/test_real_customer_baseline.py` must not regress, and
  should ideally lower the Unknown rate. Go/no-go for merging to `maincd`.
- **Real encoder, no mocks** (project convention): semantic tests run real FastEmbed on small
  canned exemplars. The model is pre-cached in CI via the same bake step as Docker, so tests are
  offline; mark them `slow` if needed.
- New unit tests: override subset behavior; provenance strings; threshold/`default` fallthrough;
  self-learning grows a route in-memory and is discarded after the upload; error → `default`.
- `tests/test_classification.py` adapted to the override-only active path. `test_llm_classifier.py`
  retained (module is dormant but kept).

## 9. Versioning, Branch & Docs

- **v10.0.0** — breaking (classifier behavior change; LLM no longer in the active path).
- **Branch:** `feat/semantic-classifier-v10` off `maincd` @ `90eb6fc` (post-#22 merge). Not stacked
  on the old LLM-fix branch.
- **ADRs:** (a) "Semantic-router as primary classifier"; (b) "FastEmbed offline encoder";
  (c) "Retire LLM classification fallback from active pipeline (kept dormant)"; (d) "Curated +
  same-file self-learning exemplars". Update `docs/adr/index.md`, `CHANGELOG.md`, and add a
  `docs/research/` page.

## 10. Risks & Open Questions

1. **Image size:** FastEmbed adds `onnxruntime` + a ~30–130 MB ONNX model. Accepted. Partly offset
   because `litellm` stays but is no longer exercised at runtime.
2. **Accuracy until tuned:** embeddings on short VM-name tokens can be weak. Mitigations: the
   override tier absorbs the high-precision cases; threshold tuning against the baseline; and if
   semantic recall disappoints, expanding the override set degrades gracefully.
3. **CI test time:** real embeddings slow the semantic suite; mitigated by the cached model.

## 11. Out of Scope

- Re-wiring or improving the LLM fallback (it goes dormant).
- Auto-classifying encryption/compression subcategory variants (stay user toggles).
- Persisting self-learned exemplars across uploads.
- Replacing the deterministic ADR-080 size reroute.
