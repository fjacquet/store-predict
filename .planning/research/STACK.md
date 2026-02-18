# Stack Research — StorePredict

## Core Stack Versions

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| UI Framework | nicegui | 2.x | Web UI with Tailwind CSS support |
| Data Processing | pandas | 2.2+ | DataFrame operations |
| XLSX Parsing | openpyxl | 3.1+ | Read RVTools/LiveOptics .xlsx |
| PDF Generation | reportlab | 4.x | One-page PDF report |
| Type Checking | mypy | 1.x | Static type analysis |
| Linting/Format | ruff | 0.8+ | Fast linter + formatter |
| Testing | pytest | 8.x | Test framework |
| Python | cpython | 3.11+ | Runtime (3.12 preferred) |

## PDF Generation: ReportLab vs WeasyPrint

| Criteria | ReportLab | WeasyPrint |
|----------|-----------|------------|
| Docker image size | +5MB | +200-400MB (cairo, pango, GTK deps) |
| Install complexity | `pip install reportlab` | System deps required (libcairo, libpango) |
| Approach | Programmatic (canvas API) | HTML/CSS → PDF |
| One-page control | Precise pixel control | CSS @page rules |
| Unicode/French | Full support with fonts | Full support natively |
| Learning curve | Higher (imperative API) | Lower (write HTML/CSS) |

**Decision: ReportLab** — Docker simplicity is decisive for single-container deployment. One-page report doesn't need HTML/CSS flexibility.

## NiceGUI + Tailwind CSS Integration

NiceGUI supports Tailwind CSS natively via `.classes()` method on any element:

```python
ui.label('Hello').classes('text-2xl font-bold text-blue-600')
ui.button('Upload', on_click=handle_upload).classes('bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded')
```

Key patterns:

- File upload: `ui.upload(on_upload=handler)` — returns UploadEventArguments with .content (bytes)
- Data tables: `ui.aggrid()` wraps AG Grid — ideal for editable VM classification table
- Multi-select: `ui.select(options, multiple=True)`
- Page routing: `@ui.page('/path')` decorator
- Per-session state: NiceGUI creates isolated state per browser tab

## Project Structure Convention

```
src/store_predict/
├── __init__.py
├── main.py              # NiceGUI app entry point
├── pages/
│   ├── upload.py        # File upload page
│   ├── classify.py      # VM classification/edit page
│   └── report.py        # Results + PDF export page
├── services/
│   ├── ingestion.py     # File parsing (RVTools, LiveOptics)
│   ├── classifier.py    # Rules-based workload classification
│   ├── calculator.py    # DRR calculation engine
│   └── pdf_report.py    # PDF generation
├── models/
│   └── vm.py            # VM dataclass, DRR types
└── data/
    └── drr_table.py     # Load DRR.csv reference data
```

## Docker Deployment

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ src/
COPY samples/DRR.csv data/
EXPOSE 8080
CMD ["python", "-m", "store_predict.main"]
```

NiceGUI uses WebSockets — Docker/reverse proxy must support WS upgrades.

## Testing Strategy

| Layer | What | Priority |
|-------|------|----------|
| Services | ingestion, classifier, calculator — pure functions | HIGH |
| Integration | Full pipeline: xlsx → DataFrame → classified → calculated | HIGH |
| PDF | Report generates, has expected content | MEDIUM |
| UI | NiceGUI page rendering | LOW (manual testing) |

pytest-asyncio not needed — NiceGUI testing is best done at the service layer, keeping UI thin.

## pyproject.toml Dependencies

```toml
[project]
dependencies = [
    "nicegui>=2.0",
    "pandas>=2.2",
    "openpyxl>=3.1",
    "reportlab>=4.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov", "ruff>=0.8", "mypy>=1.0", "pandas-stubs"]
docs = ["mkdocs", "mkdocs-material"]
```
