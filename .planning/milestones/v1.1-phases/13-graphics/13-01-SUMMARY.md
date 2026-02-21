# Plan 13-01 Summary: Chart Service Modules

**Completed:** 2026-02-20
**Status:** DONE

## What Was Built

- `src/store_predict/services/charts.py` — 4 ECharts option-dict functions for web UI
- `src/store_predict/services/pdf_charts.py` — 4 ReportLab/matplotlib chart builders for PDF
- `src/store_predict/i18n/locales/en.yaml` — 6 chart i18n keys added
- `src/store_predict/i18n/locales/fr.yaml` — 6 chart i18n keys added
- `pyproject.toml` — `matplotlib>=3.8` confirmed; mypy overrides for `matplotlib.*` confirmed

## Key Decisions Made

- `-> dict[str, Any]` return type (not bare `dict`) required for mypy strict mode
- `# noqa: PLC0415` removed from lazy imports — that's a pylint rule, not ruff; caused RUF100 errors
- Sankey falls back to `echart_before_after_options()` when `len(workload_groups) < 2`
- `make_sankey_image_flowable()` returns `Spacer(width, 0)` not `Image(BytesIO(b""), ...)` for empty data — ReportLab immediately reads Image bytes, raising `UnidentifiedImageError` on empty input

## Verification

- `python -c "from store_predict.services.charts import echart_sankey_options; print('OK')"` ✓
- `python -c "from store_predict.services.pdf_charts import make_sankey_image_flowable; print('OK')"` ✓
- ruff clean, mypy clean
