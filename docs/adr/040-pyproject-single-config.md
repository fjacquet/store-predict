# ADR-040: pyproject.toml as Single Configuration File

**Status:** Accepted
**Date:** 2026-02-19

## Context

Python projects commonly scatter tool configuration across multiple files: `setup.cfg`, `.flake8`, `mypy.ini`, `pytest.ini`, `pyproject.toml`. This fragmentation complicates onboarding and maintenance.

## Decision

Consolidate all tooling configuration into `pyproject.toml`: ruff (lint and format), mypy, pytest, and setuptools build metadata. The build backend is `setuptools.build_meta`.

## Rationale

- Single file to read to understand all project tooling
- PEP 517/518 standard; supported by all modern Python tools
- Eliminates the question "which config file takes precedence?"

## Alternatives Considered

- **Separate config files per tool:** Common historical practice but adds files with no benefit; each tool reads its own file and they cannot cross-reference each other

## Consequences

- All tool versions and settings are visible in one place during code review
- New tools must be configured in `pyproject.toml` to maintain the convention
- The `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` sections must not conflict with each other
