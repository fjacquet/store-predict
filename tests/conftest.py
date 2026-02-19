"""Shared test fixtures."""

from pathlib import Path

import pytest

from store_predict.config import DRR_CSV_PATH
from store_predict.services.drr_table import DRRTable

_SAMPLES_DIR = Path(__file__).parent.parent / "samples"


@pytest.fixture
def sample_drr_path() -> Path:
    """Path to DRR.csv — uses package data (always available)."""
    return DRR_CSV_PATH


@pytest.fixture
def drr_table(sample_drr_path: Path) -> DRRTable:
    """DRRTable loaded from the real DRR.csv."""
    return DRRTable.from_csv(sample_drr_path)


@pytest.fixture
def rvtools_path() -> Path:
    """Path to the real RVTools xlsx sample file (customer data, local only)."""
    p = _SAMPLES_DIR / "rvtools.xlsx"
    if not p.exists():
        pytest.skip("samples/rvtools.xlsx not available (customer data)")
    return p


@pytest.fixture
def liveoptics_xlsx_path() -> Path:
    """Path to the real LiveOptics xlsx sample file (customer data, local only)."""
    p = _SAMPLES_DIR / "live-optics.xlsx"
    if not p.exists():
        pytest.skip("samples/live-optics.xlsx not available (customer data)")
    return p


@pytest.fixture
def liveoptics_csv_path() -> Path:
    """Path to the LiveOptics CSV test fixture."""
    return Path(__file__).parent / "fixtures" / "liveoptics_sample.csv"
