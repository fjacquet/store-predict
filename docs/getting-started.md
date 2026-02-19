# Getting Started

## Docker Quickstart

The fastest way to run StorePredict:

```bash
docker compose up --build
```

Open your browser at [http://localhost:8080](http://localhost:8080).

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_SECRET` | (auto-generated) | Secret key for session storage. Set this in production for persistent sessions. |

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Run the Application

```bash
python -m store_predict.main
```

The app starts at [http://localhost:8080](http://localhost:8080).

## Running Tests

```bash
pytest                  # All tests
pytest --cov=store_predict  # With coverage
ruff check .            # Lint
mypy src/               # Type check
```

## Supported File Formats

StorePredict accepts VMware workload exports in these formats:

| Format | Extension | Source Tab/Sheet |
|--------|-----------|-----------------|
| RVTools | `.xlsx` | vInfo |
| LiveOptics | `.xlsx` | VMs |
| LiveOptics | `.csv` | VMs export |

## Workflow

1. **Upload** -- Drag and drop or select a file on the Upload page.
2. **Review** -- Inspect auto-classified VMs, adjust workload types if needed.
3. **Report** -- View sizing summary and download the PDF report.
