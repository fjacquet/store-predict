# ADR-039: uv for Python Package Management

**Status:** Accepted
**Date:** 2026-02-19

## Context

The project needs a Python package manager for dependency resolution, virtual environment management, and reproducible installs in CI and Docker.

## Decision

Use `uv` for all Python package management operations.

## Rationale

- 5-10x faster than pip for dependency resolution and installation
- Drop-in compatible with standard `pyproject.toml` format
- Single binary with no Python runtime dependency for installation
- Compatible with `pip install -e ".[dev]"` workflows via `uv pip install`

## Alternatives Considered

- **pip/venv:** Slower; no built-in lockfile support; the established baseline but not the best choice for developer experience
- **poetry:** Heavier; introduces its own lockfile format and dependency resolver that diverges from PEP standards

## Consequences

- All `CLAUDE.md` and documentation references use `uv` commands (e.g., `uv pip install -e ".[dev]"`)
- The Dockerfile and CI workflows install `uv` as a first step
- Developers must have `uv` installed; the README documents this as a prerequisite
