"""Tests for the DRR table service."""

from store_predict.services.drr_table import DRRTable


def test_drr_table_loads_30_entries(drr_table: DRRTable) -> None:
    """DRR.csv should produce exactly 28 valid workload categories."""
    assert len(drr_table) == 28


def test_postgresql_entry_parsed_correctly(drr_table: DRRTable) -> None:
    """PostgreSQL entry has embedded newline in CSV -- must parse correctly."""
    ratio = drr_table.get_ratio("Database", "PostgreSQL")
    assert ratio == 1.5


def test_unknown_reducible_default(drr_table: DRRTable) -> None:
    """Unknown (Reducible) has DRR = 5."""
    ratio = drr_table.get_ratio("Unknown (Reducible)", "Unknown (Reducible)")
    assert ratio == 5.0


def test_missing_category_returns_default(drr_table: DRRTable) -> None:
    """Unknown category/subcategory returns default DRR of 5.0."""
    ratio = drr_table.get_ratio("NonExistent", "Nothing")
    assert ratio == 5.0


def test_conservative_ratio_returns_minimum(drr_table: DRRTable) -> None:
    """Multi-workload uses the lowest (most conservative) DRR."""
    ratio = drr_table.get_conservative_ratio(
        [
            ("Database", "Oracle"),  # DRR = 5
            ("Database", "DB2"),  # DRR = 1.5
        ]
    )
    assert ratio == 1.5


def test_conservative_ratio_empty_returns_default(drr_table: DRRTable) -> None:
    """Empty workload list returns default DRR = 5.0."""
    ratio = drr_table.get_conservative_ratio([])
    assert ratio == 5.0


def test_all_ratios_positive(drr_table: DRRTable) -> None:
    """All DRR values must be > 0 (prevent division by zero)."""
    for entry in drr_table.entries:
        assert entry.ratio > 0, f"{entry.category}/{entry.subcategory} has ratio {entry.ratio}"


def test_categories_returns_sorted_unique(drr_table: DRRTable) -> None:
    """Categories property returns sorted unique category names."""
    cats = drr_table.categories
    assert cats == sorted(cats)
    assert len(cats) == len(set(cats))
    assert len(cats) > 0


def test_entries_returns_copy(drr_table: DRRTable) -> None:
    """Modifying returned entries list does not affect internal state."""
    entries = drr_table.entries
    original_len = len(drr_table)
    entries.clear()
    assert len(drr_table) == original_len
