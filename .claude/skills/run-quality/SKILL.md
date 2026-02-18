---
name: run-quality
description: Run full quality gate (ruff + mypy + pytest) in one shot
---

Run all quality checks for the StorePredict project and report results.

Execute these three commands sequentially:

1. **Lint**: `rtk ruff check .`
2. **Type check**: `rtk mypy src/`
3. **Tests**: `rtk pytest --tb=short`

After all three complete, report a summary:

| Check | Status | Details |
|-------|--------|---------|
| Lint (ruff) | Pass/Fail | Number of issues if any |
| Types (mypy) | Pass/Fail | Number of errors if any |
| Tests (pytest) | Pass/Fail | X passed, Y failed |

If all pass, output: "Quality gate PASSED"
If any fail, output: "Quality gate FAILED" with details on what to fix.
