# StorePredict Development Makefile
# Standardized on the fjacquet/ci canonical Python interface (do not rename the
# canonical targets: tools lint format test build vuln sbom security docs
# coverage-upload release ci). Repo-specific app/docker targets are preserved
# below the canonical block.
.DEFAULT_GOAL := all
DIST ?= dist
PYTHON ?= python
PORT ?= 8080
PID_FILE := .store-predict.pid

.PHONY: all clean install tools lint format test build vuln sbom security docs coverage-upload release ci \
        help venv dev run start stop status restart typecheck test-cov md-lint docs-serve docs-build \
        docker-up docker-down docker-logs

# ── Canonical fjacquet/ci interface ────────────────
all: clean lint test build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

clean: ## Remove build artifacts and caches
	rm -rf $(DIST) site .coverage coverage.xml *.sarif
	rm -rf build/ *.egg-info src/*.egg-info htmlcov/
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f .store-predict.pid .store-predict.log
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

install: ## Install all deps + project (uv-managed venv)
	uv sync --all-extras --all-groups

tools: install ## Alias for install (fjacquet/ci standard)

lint: ## Lint + format check (read-only, fjacquet/ci standard)
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format with ruff
	uv run ruff format .

# CI runs unit tests only. `slow`-marked tests download the FastEmbed model
# (real embeddings) — excluded so CI never depends on a network model pull.
test: ## Run unit tests with coverage (excludes slow/model tests)
	uv run pytest -m "not slow" --cov --cov-report=xml --cov-report=term-missing

build: ## Build distributable wheel/sdist
	uv build

vuln: ## OSV vulnerability scan against uv.lock (fjacquet/ci standard)
	uvx osv-scanner scan --lockfile=uv.lock || true

sbom: ## Generate a CycloneDX SBOM to $(DIST)/sbom.cdx.json (fjacquet/ci standard)
	mkdir -p $(DIST)
	uv run cyclonedx-py environment --output-format JSON --output-file $(DIST)/sbom.cdx.json

security:  ## Semgrep SAST (advisory; non-blocking — CodeQL/osv are the blocking gates)
	uvx semgrep scan --config auto --skip-unknown-extensions || true

docs: ## Build MkDocs documentation strict mode to site/ (fjacquet/ci standard)
	# --extra docs self-provisions mkdocs-material: the central mkdocs-publish
	# action runs `make docs` WITHOUT a prior `make install`, and mkdocs lives in
	# the `docs` optional-dependencies extra (uv does not auto-sync extras).
	uv run --extra docs mkdocs build --strict --site-dir site

coverage-upload: ## Upload coverage.xml to Codecov (fjacquet/ci standard)
	uvx --from codecov-cli codecov upload-process --file coverage.xml || true

release: ## Build wheel/sdist (no PyPI publish — release.yml ships GitHub Release + GHCR image)
	uv build

ci: lint test build ## Canonical CI target: lint test build

# ── Repo-specific: environment ─────────────────────
venv: ## Create virtual environment with uv
	uv venv .venv

dev: ## Install with dev dependencies (in venv)
	uv pip install -e ".[dev]"

# ── Repo-specific: run/manage the NiceGUI app ──────
run: ## Start the app (foreground)
	$(PYTHON) -m store_predict.main

start: ## Start the app (background, port=$(PORT))
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "StorePredict is already running (PID $$(cat $(PID_FILE)))"; \
	else \
		echo "Starting StorePredict on port $(PORT)..."; \
		nohup $(PYTHON) -m store_predict.main > .store-predict.log 2>&1 & echo $$! > $(PID_FILE); \
		sleep 2; \
		if kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
			echo "StorePredict started (PID $$(cat $(PID_FILE)), port $(PORT))"; \
		else \
			echo "Failed to start. Check .store-predict.log"; \
			rm -f $(PID_FILE); \
			exit 1; \
		fi; \
	fi

stop: ## Stop the background app
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			echo "Stopping StorePredict (PID $$PID)..."; \
			kill $$PID; \
			sleep 1; \
			kill -0 $$PID 2>/dev/null && kill -9 $$PID; \
			echo "Stopped."; \
		else \
			echo "Process $$PID not running."; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "No PID file found. StorePredict is not running."; \
	fi

status: ## Check if app is running
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "StorePredict is running (PID $$(cat $(PID_FILE)))"; \
	else \
		echo "StorePredict is not running"; \
		rm -f $(PID_FILE) 2>/dev/null; \
	fi

restart: stop start ## Restart the app

# ── Repo-specific: quality extras ──────────────────
typecheck: ## Run mypy type checker
	uv run mypy src/

test-cov: ## Run tests with coverage report (terminal)
	uv run pytest --cov=store_predict --cov-report=term-missing

md-lint: ## Check + auto-fix markdown with markdownlint
	markdownlint --fix .

# ── Repo-specific: docs preview ────────────────────
docs-serve: ## Serve docs locally
	uv run mkdocs serve

docs-build: ## Build docs site (non-strict)
	uv run mkdocs build

# ── Repo-specific: Docker ──────────────────────────
docker-up: ## Start with Docker Compose
	docker compose up --build -d

docker-down: ## Stop Docker Compose
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f
