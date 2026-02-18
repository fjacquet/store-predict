FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
COPY src/ src/
COPY samples/DRR.csv samples/DRR.csv

RUN uv venv .venv && . .venv/bin/activate && uv pip install --no-cache .

EXPOSE 8080

CMD [".venv/bin/python", "-m", "store_predict.main"]
