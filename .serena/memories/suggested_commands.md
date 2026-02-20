# Suggested Commands

**CRITICAL:** All commands MUST be prefixed with `rtk` for token optimization.

## Development
```bash
source .venv/bin/activate       # Activate existing venv
uv pip install -e ".[dev]"      # Install with dev deps
python -m store_predict.main    # Run the app (port 8080)
```

## Quality (always use rtk)
```bash
rtk ruff check .                # Lint
rtk ruff format .               # Format
mypy src/                       # Type check (rtk does NOT support mypy)
```

## Testing (always use rtk)
```bash
rtk pytest                      # All tests
rtk pytest tests/test_foo.py    # Single file
rtk pytest -k "test_name"       # Single test
rtk pytest --cov=store_predict  # With coverage
```

## Git (always use rtk)
```bash
rtk git status
rtk git diff
rtk git add file && rtk git commit -m "msg"
```

## Docker
```bash
rtk docker compose up --build
```

## Docs
```bash
mkdocs serve                    # Local preview
mkdocs build                    # Build
```

## System (Darwin/macOS)
```bash
ls, cd, grep, find              # Standard Unix commands
```
