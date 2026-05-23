# ADR-083: FastEmbed (ONNX) as the Offline Embedding Encoder

**Status:** Accepted
**Date:** 2026-05-23
**Issue:** v10.0.0 — Choosing an embedding encoder compatible with offline Docker deployment

## Context

ADR-082 establishes `semantic-router` as the primary classifier tier. `semantic-router`
supports multiple embedding backends: `HuggingFaceEncoder` (via `sentence-transformers`),
`OllamaEncoder` (via a running Ollama daemon), `OpenAIEncoder`, `CohereEncoder`, and
`FastEmbedEncoder` (ONNX via the `fastembed` library).

StorePredict is deployed as a **single offline Docker container** (ADR-030). The deployment
environment has no internet access and no co-deployed Ollama or OpenAI-compatible service.
The embedding backend must therefore be:

1. Fully self-contained (model baked into the image, no runtime downloads).
2. Free of heavyweight ML frameworks (PyTorch adds ~2 GB to the image).
3. Deterministic — the same VM name must always embed to the same vector.

## Decision

Use `FastEmbedEncoder("BAAI/bge-small-en-v1.5")` baked into the Docker image.

`fastembed` wraps ONNX Runtime and ships quantised ONNX model files; no PyTorch is required.
`bge-small-en-v1.5` is a 33M-parameter bilingual encoder (English/Chinese) that produces
384-dimensional vectors and scores well on classification benchmarks for short technical
strings (VM names, application identifiers). The model is small enough to download during the
Docker build (`RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"`)
and resides in the image's HuggingFace cache directory.

### Dependency constraint

`semantic-router[fastembed]` pins `fastembed<0.4`, whose transitive dependency is
`pillow<11`. This conflicts with `pillow>=12.2.0` required by the project's PDF charts
(ADR-071). Resolution: declare `fastembed>=0.8` directly in `pyproject.toml` rather than
using the `[fastembed]` extra. `FastEmbedEncoder` lazy-imports `fastembed` at construction
time, so the import chain is satisfied by the directly-declared `fastembed>=0.8` package,
which does not carry the conflicting Pillow pin.

### Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| `HuggingFaceEncoder` (sentence-transformers) | Requires PyTorch; adds ~2 GB to image |
| `OllamaEncoder` | Needs a running Ollama daemon at classification time — a runtime dependency incompatible with the offline constraint; kept as a developer option, not default |
| `OpenAIEncoder` / `CohereEncoder` | Requires internet access and API keys — violates offline constraint |
| Custom TF-IDF | Fast, but too weak for fuzzy product-name matching across 1000+ VM naming conventions |

## Consequences

**Positive:**

- Fully offline and deterministic.
- No PyTorch in the production image.
- ONNX Runtime is already a common container dependency; image size increase is modest
  (~130 MB model + ~50 MB onnxruntime wheels).
- `bge-small-en-v1.5` produces good similarity scores for short technical strings; the
  threshold tuning harness (see ADR-085) confirms >0.80 similarity for true positives
  with a 0.75 default threshold.

**Negative:**

- Docker build step downloads the model from HuggingFace Hub (once, at build time). CI/CD
  environments with no outbound access must pre-cache or use a registry mirror.
- `onnxruntime` is a compiled wheel; the Docker image must use a compatible base (`python:3.12-slim`
  + `libgomp1` for OpenMP, already present in the Dockerfile).
- The `pillow>=12.2.0` / `fastembed<0.4` conflict requires the workaround above; future
  `semantic-router` versions may resolve this upstream.

## Related

- ADR-082: Semantic-router as primary classifier — motivation for needing an encoder.
- ADR-084: LLM fallback retirement — FastEmbed replaces the Ollama runtime dependency.
- ADR-030: Docker single-container deployment — the offline constraint this ADR satisfies.
