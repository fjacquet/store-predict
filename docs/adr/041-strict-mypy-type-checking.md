# ADR-041: Strict mypy with TYPE_CHECKING Guards

**Status:** Accepted
**Date:** 2026-02-19

## Context

The codebase uses type annotations throughout. The level of mypy strictness and the handling of annotation-only imports must be defined.

## Decision

Run mypy with `--strict` on all source code. Annotation-only imports are placed inside `TYPE_CHECKING` blocks per ruff's TCH rules. `from __future__ import annotations` is used throughout. mypy overrides with `ignore_missing_imports = true` are applied for `nicegui.*` and `reportlab.*` which have no type stubs.

## Rationale

- `--strict` catches the largest class of type errors, including missing return types and untyped function parameters
- `TYPE_CHECKING` guards prevent circular imports and eliminate runtime overhead for annotation-only imports
- `from __future__ import annotations` enables PEP 563 deferred evaluation, reducing runtime import costs
- `ignore_missing_imports` for nicegui and reportlab is a pragmatic workaround until those libraries ship stubs

## Alternatives Considered

- **Lenient mypy (no --strict):** Allows gradual typing but permits implicit `Any`, which defeats the purpose of type checking

## Consequences

- New code must be fully annotated; mypy CI check blocks merges with type errors
- Developers must understand the `TYPE_CHECKING` pattern to avoid accidentally moving runtime imports inside the guard
