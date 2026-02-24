.PHONY: all help install dev run stop lint format typecheck test test-cov md-lint docs docs-build docker-up docker-down clean

PYTHON ?= python
PORT ?= 8080
PID_FILE := .store-predict.pid
VENV := .venv

all: quality ## Run full quality gate (lint + types + tests) — default target

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────

venv: ## Create virtual environment with uv
	uv venv $(VENV)

install: ## Install production dependencies (in venv)
	uv pip install -e .

dev: ## Install with dev dependencies (in venv)
	uv pip install -e ".[dev]"

# ── Run ────────────────────────────────────────────

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

# ── Quality ────────────────────────────────────────

lint: ## Run ruff linter
	ruff check .

lint-fix: ## Auto-fix ruff lint issues
	ruff check --fix .

format: ## Format code with ruff
	ruff format .

fix: lint-fix format ## Auto-fix lint + format in one shot

typecheck: ## Run mypy type checker
	mypy src/

test: ## Run all tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=store_predict --cov-report=term-missing

md-lint: ## Check markdown with markdownlint
	markdownlint --fix .

quality: lint typecheck test ## Run full quality gate (lint + types + tests)

# ── Docs ───────────────────────────────────────────

docs: ## Serve docs locally
	mkdocs serve

docs-build: ## Build docs site
	mkdocs build

# ── Docker ─────────────────────────────────────────

docker-up: ## Start with Docker Compose
	docker compose up --build -d

docker-down: ## Stop Docker Compose
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f

# ── Cleanup ────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov/ .coverage
	rm -f .store-predict.pid .store-predict.log
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
