# ADR-038: MkDocs with Material Theme for Documentation

**Status:** Accepted
**Date:** 2026-02-19

## Context

The project requires user-facing documentation that can be hosted on GitHub Pages and maintained alongside the codebase.

## Decision

Use MkDocs with the Material theme. Documentation is deployed to the `gh-pages` branch via GitHub Actions. Mermaid diagrams are supported via `pymdownx.superfences`.

## Rationale

- Material theme is the de facto standard for Python project documentation
- Built-in Mermaid support via `pymdownx.superfences` requires no additional tooling
- GitHub Actions deployment is straightforward with `mkdocs gh-deploy`
- Markdown source files are readable without rendering, unlike Sphinx RST

## Alternatives Considered

- **Sphinx with autodoc:** Better for API reference generation but heavier; overkill for a pre-sales tool that needs user guides, not API docs

## Consequences

- Documentation lives in `docs/` and is deployed automatically on push to `main`
- Mermaid diagrams render in the hosted docs but not in raw GitHub Markdown preview
- Adding a new page requires both creating the `.md` file and adding it to `mkdocs.yml` nav
