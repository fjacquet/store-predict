# External Integrations

**Analysis Date:** 2026-02-23

## APIs & External Services

**LLM Classification (Optional Fallback):**
- OpenRouter - Proxy service for multiple LLM providers
  - SDK/Client: `litellm>=1.81.13`
  - Auth: Env vars `LLM_API_KEY` (SecretStr), `LLM_API_BASE` (custom endpoint URL)
  - Model: Configurable via `LLM_MODEL` env var (default: `mistralai/mistral-small-3.1-24b-instruct`)
  - Feature: `src/store_predict/pipeline/llm_classifier.py` - Async batch + single-VM classification with circuit breaker (3 failures = 60s cooldown)
  - Disabled by default (`LLM_ENABLED=false`)
  - Safety: VM names/OS truncated + sanitized; prompt injection mitigated; all LLM calls guarded by `asyncio.wait_for(timeout=30s)`

**Browser Automation:**
- Playwright (Chromium headless)
  - SDK: `playwright>=1.40`
  - Usage: `src/store_predict/services/playwright_pdf.py` - Print-to-PDF for web pages
  - Feature: Navigates to `/report/print` and `/layout/print` routes with print-optimized rendering
  - No external service; self-hosted Chromium in container

## Data Storage

**Databases:**
- None - Application is stateless in production
- Session storage: NiceGUI `ui.storage` (tab-scoped in-memory, encrypted by `STORAGE_SECRET`)
- File-based: CSV reference data bundled at package build time

**File Storage:**
- Local filesystem only - No cloud integration
- Upload handling: `src/store_predict/pipeline/validation.py` validates file extension + magic bytes
- DRR reference: `src/store_predict/data/DRR.csv` (bundled package data, semicolon-delimited)
- Compute presets: `src/store_predict/data/compute_presets.csv` (bundled reference)
- Logo assets: `src/store_predict/data/dell_logo.png` (Dell partner logo bundled)
- Generated files: Temporary PDFs/Excel files held in memory (`BytesIO`) then streamed to client

**Caching:**
- None - No Redis/Memcached
- In-process: LRU cache for LLM config singleton (`@lru_cache(maxsize=1)` at `src/store_predict/services/llm_config.py`)

## Authentication & Identity

**Auth Provider:**
- None - Application is internal-facing pre-sales tool
- Session security: NiceGUI session isolation via `storage_secret` (prevents cross-tab session hijacking)
- No user login or identity verification

**Access Control:**
- STORAGE_SECRET env var protects session data in NiceGUI storage
- Default: `"dev-only-not-for-production"` (must be changed in production via Docker Compose env file)

## Monitoring & Observability

**Error Tracking:**
- None - No integration with Sentry/Rollbar
- All errors logged to stdout via `logging_config.py`

**Logs:**
- Python stdlib `logging` module
- Log output: stdout (visible in Docker `docker logs` and GitHub Actions logs)
- Sanitization: `logging_config.py` guards against logging DataFrame contents or sensitive VM names
- LLM calls log status only (counts, circuit breaker state); never log keys or VM names

**Health Check:**
- Docker HEALTHCHECK: HTTP GET to `http://localhost:8080` (port 8080)
- Interval: 30 seconds, timeout: 5 seconds, retries: 3
- Endpoint: NiceGUI index page `/` (implicitly available)

## CI/CD & Deployment

**Hosting:**
- Docker (single container)
- Platform: Any Docker-compatible host (Linux, macOS with Docker Desktop, Kubernetes, ECS, etc.)
- Port exposure: 8080 (configurable in `docker-compose.yml`)

**Container:**
- Base image: `python:3.12-slim`
- Playwright/Chromium installed at build time (`playwright install chromium --with-deps`)
- User: `appuser` (non-root for security)
- Entrypoint: `.venv/bin/python -m store_predict.main` (runs NiceGUI on port 8080)

**CI Pipeline:**
- GitHub Actions - Two workflows:
  1. **ci.yml** - Runs on push/PR to `main` branch
     - Lint: `ruff check --fix` + `ruff format`
     - Type check: `mypy src/`
     - Test: `pytest --cov=store_predict`
     - Coverage upload: Codecov (via `codecov/codecov-action@v5`)
     - Auto-commit: Fixes lint issues and pushes back to branch
  2. **docs.yml** - Runs on version tag push (`v*`)
     - Builds MkDocs static site
     - Deploys to GitHub Pages via `mkdocs gh-deploy --force`
     - Resolves symlinked `docs/changelog.md` before build

**Deployment:**
- Docker Compose configuration: `docker-compose.yml`
  - Build from local `Dockerfile`
  - Port mapping: 8080:8080
  - Environment config: Optional `.env` file + explicit vars
  - Restart policy: `unless-stopped`

## Environment Configuration

**Required env vars:**
- `STORAGE_SECRET` - NiceGUI session encryption (CRITICAL for production security)

**Optional env vars (LLM feature):**
- `LLM_ENABLED` - Set to `true` to activate LLM classification
- `LLM_API_KEY` - OpenRouter API key (required if enabled)
- `LLM_API_BASE` - Custom endpoint (defaults to `https://openrouter.ai/api/v1`)
- `LLM_MODEL` - Model identifier (defaults to `mistralai/mistral-small-3.1-24b-instruct`)
- `LLM_TIMEOUT` - Request timeout in seconds (defaults to 30)
- `LLM_MAX_CONCURRENT` - Max concurrent requests (defaults to 5)
- `LLM_BATCH_SIZE` - VMs per batch request (defaults to 10)

**Secrets location:**
- Docker: `.env` file (mounted by `docker-compose.yml`)
- Development: Optional `.env` at project root (not committed)
- Production: Environment variables passed at container runtime

## Webhooks & Callbacks

**Incoming:**
- None - Application receives only browser HTTP requests (form uploads, page navigation)

**Outgoing:**
- LLM API calls to OpenRouter (async via `litellm.acompletion()`)
- GitHub Actions (CI/CD, not outbound integrations from the app)

## External Data Sources

**File Upload Processing:**
- RVTools .xlsx - Parse vInfo sheet (VM metadata: name, OS, provisioned/in-use storage)
- LiveOptics .xlsx or .csv - Parse VMs sheet (same structure) + optional Performance sheet (IOPS/throughput metrics)
- ZIP archives - Fallback extraction if RVTools exports as ZIP (phase 8.1)

**Reference Data:**
- DRR.csv - Semicolon-delimited workload category → data reduction ratio mapping
  - Loaded at `src/store_predict/services/drr_table.py`
  - Format: Category | Subcategory | DRR value
  - Mutable by pre-sales engineer (uploaded at runtime, not hardcoded)
- compute_presets.csv - Dell PowerEdge host configuration profiles
  - Used by `src/store_predict/pipeline/compute_sizing.py`
  - Overridable per-session

## Third-Party Service Dependencies

**No SaaS integrations for core functionality:**
- Sizing calculation: Pure Python (pandas + custom logic)
- PDF generation: ReportLab (in-process, no external service)
- File uploads: Local validation only
- Database: None

**Optional (LLM classification only):**
- OpenRouter acts as proxy to multiple LLM providers (Mistral, etc.)
- Disabled by default; safe for air-gapped environments

---

*Integration audit: 2026-02-23*
