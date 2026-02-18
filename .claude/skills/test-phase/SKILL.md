---
name: test-phase
description: Run tests relevant to a specific phase number
---

Run tests for a specific phase of the StorePredict project.

**Arguments:** Phase number (e.g., `1`, `2`, `3`)

Phase-to-test mapping:

| Phase | Test files | What it covers |
|-------|-----------|----------------|
| 1 | `tests/test_models.py tests/test_drr_table.py` | Models, DRR table service |
| 2 | `tests/test_ingestion.py` | File ingestion pipeline |
| 3 | `tests/test_classifier.py` | Workload classification |
| 4 | `tests/test_ui*.py` | UI pages |
| 5 | `tests/test_calculation.py tests/test_pdf*.py` | Calculation and PDF report |
| 6 | `tests/` | Full suite (polish phase) |

If no phase argument is provided, detect the current phase from `.planning/STATE.md`.

Run with: `rtk pytest {test_files} -v --tb=short`

Report the results with pass/fail count. If tests don't exist yet for the phase, say so.
