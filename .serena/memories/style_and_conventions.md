# Style & Conventions

## Code Style
- **Formatter/Linter:** ruff (replaces black, isort, flake8)
- **Type checker:** mypy (strict mode)
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Type hints:** Required on all function signatures
- **Docstrings:** Brief, present on public functions/classes
- **Imports:** `from __future__ import annotations` in all modules

## Conventions
- NO `unittest.mock` — tests use real objects, fixtures, and sample data
- Pipeline modules must NOT import from `store_predict.ui` (zero UI deps)
- DRR reference data loaded from CSV, never hardcoded
- `frozen=True` dataclasses for immutable data structures
- `__all__` exports in public modules
- Sample data in `samples/` is real customer data — never commit new customer data without anonymization
- Use `Any` type for pandas dict outputs (e.g., `to_dict()`)
- Add `# type: ignore[import-untyped]` for untyped third-party libs (openpyxl)
- NiceGUI pages need `await ui.context.client.connected()` before accessing `app.storage.tab`

## Patterns
- Context manager pattern for NiceGUI shared layout
- Page registration via side-effect imports in main.py (`# noqa: F401`)
- `.get(key, default)` for dict field access with defaults
- `defaultdict(list)` for grouping operations
