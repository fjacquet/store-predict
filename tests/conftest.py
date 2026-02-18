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
