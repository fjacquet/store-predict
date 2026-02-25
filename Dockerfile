# syntax=docker/dockerfile:1
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user before any files land in /app — eliminates chown -R layer
RUN useradd --uid 1000 --create-home --shell /bin/bash appuser

WORKDIR /app
RUN chown appuser:appuser /app

ENV UV_LINK_MODE=copy
# Use a writable cache dir accessible to appuser
ENV UV_CACHE_DIR=/tmp/uv-cache

USER appuser

# ── Layer 1: Install Python dependencies (cached until uv.lock changes) ──────
# Files are owned by appuser from the start — no chown -R needed later.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/tmp/uv-cache,uid=1000,gid=1000 \
    uv sync --frozen --no-install-project

# ── Layer 2: Install the project itself (fast — code changes only) ────────────
COPY --chown=appuser:appuser src/ src/
RUN --mount=type=cache,target=/tmp/uv-cache,uid=1000,gid=1000 \
    uv sync --frozen

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080')" || exit 1

CMD [".venv/bin/python", "-m", "store_predict.main"]
