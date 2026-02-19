# ADR-033: Context Manager for Shared Layout

**Status:** Accepted
**Date:** 2026-02-19

## Context

All pages share a common header and navigation bar. NiceGUI does not provide a built-in layout inheritance mechanism equivalent to template inheritance in Jinja2.

## Decision

Implement a `@contextmanager` function in `layout.py`. Pages use it as `with layout("Page Title"):` and place their content inside the block.

## Rationale

- Single definition of header and navigation; changes apply to all pages automatically
- The `yield` gives the caller an explicit slot for page-specific content
- Pythonic pattern that does not require NiceGUI-specific extension points

## Alternatives Considered

- **Copy-paste layout into each page:** Header changes require editing every page file; error-prone
- **NiceGUI inheritance/mixins:** NiceGUI does not provide a first-class page inheritance mechanism for this pattern

## Consequences

- All pages must use the context manager; a page that does not is visually inconsistent
- The layout function must not hold page-specific state between `__enter__` and `__exit__`
- Adding a new shared element (e.g., breadcrumbs) requires modifying only `layout.py`
