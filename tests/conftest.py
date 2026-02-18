"""Shared test fixtures."""

from pathlib import Path

import pytest

from store_predict.services.drr_table import DRRTable


@pytest.fixture
def sample_drr_path() -> Path:
    """Path to the real DRR.csv sample file."""
    return Path(__file__).parent.parent / "samples" / "DRR.csv"


@pytest.fixture
def drr_table(sample_drr_path: Path) -> DRRTable:
    """DRRTable loaded from the real DRR.csv."""
    return DRRTable.from_csv(sample_drr_path)


@pytest.fixture
def rvtools_path() -> Path:
    """Path to the real RVTools xlsx sample file."""
    return Path(__file__).parent.parent / "samples" / "rvtools.xlsx"


@pytest.fixture
def liveoptics_xlsx_path() -> Path:
    """Path to the real LiveOptics xlsx sample file."""
    return Path(__file__).parent.parent / "samples" / "live-optics.xlsx"


@pytest.fixture
def liveoptics_csv_path() -> Path:
    """Path to the LiveOptics CSV test fixture."""
    return Path(__file__).parent / "fixtures" / "liveoptics_sample.csv"
