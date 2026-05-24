# syntax=docker/dockerfile:1

# ── Stage 1: builder — install deps, the project, and pre-fetch the model ─────
# Everything here (uv binary, build cruft) is discarded; only what we COPY into
# the runtime stage ships. This is what drops the ~49 MB uv binary from the
# final image.
FROM python:3.12-slim AS builder

# uv is needed only to build the virtualenv; it stays in this throwaway stage.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    FASTEMBED_CACHE_PATH=/app/.fastembed_cache

# Layer 1: dependencies only (cached until uv.lock changes). `dev` lives in
# [project.optional-dependencies] (an extra), so `uv sync` correctly skips it.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-install-project

# Layer 2: the project itself (fast — code changes only).
COPY src/ src/
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen

# Pre-download the FastEmbed model so the runtime image runs fully offline.
RUN .venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Strip litellm + tiktoken (semantic-router imports them eagerly via
# encoders/__init__.py, but store-predict only ever uses FastEmbedEncoder, so
# their code paths are dead here). Swap in tiny stubs and drop litellm's
# orphaned dep fastuuid. Saves ~65 MB and removes litellm's CVE surface from the
# shipped image. The build-time import check below fails fast if the stub
# surface is ever insufficient (e.g. after a semantic-router bump). Source-level
# dependency metadata (uv.lock / SBOM) is left untouched — only the image swaps.
COPY docker/stubs/ /tmp/stubs/
RUN set -eux; \
    SITE=.venv/lib/python3.12/site-packages; \
    rm -rf "$SITE"/litellm "$SITE"/litellm-*.dist-info \
           "$SITE"/tiktoken "$SITE"/tiktoken-*.dist-info \
           "$SITE"/fastuuid*; \
    cp /tmp/stubs/litellm.py "$SITE"/litellm.py; \
    cp /tmp/stubs/tiktoken.py "$SITE"/tiktoken.py; \
    rm -rf /tmp/stubs; \
    .venv/bin/python -c "import litellm, tiktoken; from semantic_router import Route; from semantic_router.encoders import FastEmbedEncoder; from semantic_router.routers import SemanticRouter; from semantic_router.schema import RouteChoice; print('stub swap verified — semantic_router imports OK without real litellm/tiktoken')"

# ── Stage 2: runtime — Python, the venv, the code, and the model only ─────────
# Same python:3.12-slim base as the builder, so the venv's interpreter symlink
# (/usr/local/bin/python3.12) and onnxruntime's .so files resolve identically.
FROM python:3.12-slim

# Non-root user created before any files land — no chown -R layer needed.
RUN useradd --uid 1000 --create-home --shell /bin/bash appuser

WORKDIR /app
ENV FASTEMBED_CACHE_PATH=/app/.fastembed_cache

# Copy the built virtualenv, the source (the editable install targets /app/src,
# so the path must match the builder), and the pre-fetched model cache.
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv
COPY --from=builder --chown=appuser:appuser /app/src ./src
COPY --from=builder --chown=appuser:appuser /app/.fastembed_cache ./.fastembed_cache

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080')" || exit 1

CMD [".venv/bin/python", "-m", "store_predict.main"]
