# StorePredict

Pre-sales sizing tool that analyzes VMware workload exports to predict Data Reduction Ratios (DRR) on Dell PowerStore arrays.

## Quickstart (Docker)

```bash
git clone https://github.com/fjacquet/store-predict.git
cd store-predict
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080).

## Quickstart (Local)

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m store_predict.main
```

## Features

- **Format detection** -- Automatically identifies RVTools (.xlsx) and LiveOptics (.xlsx/.csv) exports
- **29 classification rules** -- Pattern-based VM workload classification (SQL, Oracle, VDI, SAP, and more)
- **DRR prediction** -- Maps workload categories to Dell PowerStore data reduction ratios
- **Interactive review** -- AG Grid table with inline editing and multi-workload dialog
- **PDF report** -- One-page branded sizing report with capacity breakdown

## Documentation

Full documentation: [https://fjacquet.github.io/store-predict/](https://fjacquet.github.io/store-predict/)

## License

See [LICENSE](LICENSE) for details.
