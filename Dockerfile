# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy
# Playwright browsers stored in a world-readable path so appuser can access them
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ── Layer 1: Install Python dependencies only (cached until uv.lock changes) ──
# uv sync --no-install-project installs all deps without the project package.
# This layer only re-runs when pyproject.toml or uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# ── Layer 2: Playwright (cached until Python deps change) ──────────────────
# Runs only when the previous layer is invalidated (new/changed dependency).
# Browsers are installed to /ms-playwright (world-readable) so the non-root
# appuser can launch Chromium at runtime.
RUN .venv/bin/playwright install chromium --with-deps \
    && chmod -R o+rX /ms-playwright

# ── Layer 3: Install the project itself (fast — code only, no downloads) ────
# This is the only layer that re-runs on regular code changes.
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080')" || exit 1

CMD [".venv/bin/python", "-m", "store_predict.main"]
