# ADR-023: Page Routes via Module Import Side-Effects

**Status:** Accepted
**Date:** 2026-02-19

## Context

NiceGUI registers routes using the `@ui.page` decorator. The decorator fires at class/function definition time, which is at module import time.

## Decision

Register all pages by importing their modules in `main.py`. The `@ui.page` decorator fires as a side-effect of the import. All page imports must appear before `ui.run()`.

## Rationale

- Follows the established NiceGUI convention used in the official docs and examples
- No additional registration infrastructure needed
- Makes the list of all routes visible in one file (`main.py`)

## Alternatives Considered

- **Explicit route registration functions:** More verbose; requires each page module to export a `register()` function and `main.py` to call each one

## Consequences

- Import order in `main.py` matters: page modules must be imported before `ui.run()`
- Circular imports between page modules and shared layout must be avoided
- Adding a new page requires both creating the module and adding an import line in `main.py`
