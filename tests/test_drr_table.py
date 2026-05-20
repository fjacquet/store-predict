"""Tests for the DRR table service."""

from store_predict.config import StorageModel
from store_predict.services.drr_table import DRRTable, apply_storage_model


def test_drr_table_loads_30_entries(drr_table: DRRTable) -> None:
    """DRR.csv should produce exactly 43 valid workload entries
    (28 base + 14 variants + 1 Large data-bearing v9.0.0)."""
    assert len(drr_table) == 43


def test_large_data_bearing_drr(drr_table: DRRTable) -> None:
    """Size-aware reroute target: DRR=2.0 (2:1) for unknown ≥100 GiB VMs (v9.0.1)."""
    assert drr_table.get_ratio("Virtual Machines", "Large data-bearing (>100 GiB unknown)") == 2.0


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


def test_apply_storage_model_powervault(drr_table: DRRTable) -> None:
    """PowerVault sets all DRR values to 1.0."""
    rows: list[dict] = [
        {"vm_name": "sql-01", "workload_category": "Database", "workload_subcategory": "Microsoft SQL", "drr": 5.0},
        {"vm_name": "web-01", "workload_category": "Virtual Machines", "workload_subcategory": "Windows", "drr": 5.0},
    ]
    apply_storage_model(rows, StorageModel.POWERVAULT, drr_table)
    assert all(r["drr"] == 1.0 for r in rows)


def test_apply_storage_model_powerflex(drr_table: DRRTable) -> None:
    """PowerFlex sets all DRR values to 2.0."""
    rows: list[dict] = [
        {"vm_name": "sql-01", "workload_category": "Database", "workload_subcategory": "Microsoft SQL", "drr": 5.0},
    ]
    apply_storage_model(rows, StorageModel.POWERFLEX, drr_table)
    assert rows[0]["drr"] == 2.0


def test_apply_storage_model_powerstore_restores_table_values(drr_table: DRRTable) -> None:
    """PowerStore restores per-workload DRR from the reference table."""
    rows: list[dict] = [
        {"vm_name": "sql-01", "workload_category": "Database", "workload_subcategory": "Microsoft SQL", "drr": 1.0},
    ]
    apply_storage_model(rows, StorageModel.POWERSTORE, drr_table)
    expected = drr_table.get_ratio("Database", "Microsoft SQL")
    assert rows[0]["drr"] == expected
    assert rows[0]["drr"] > 1.0


# ---------------------------------------------------------------------------
# Encrypted/compressed variant DRR spot-checks
# ---------------------------------------------------------------------------


def test_oracle_tde_drr(drr_table: DRRTable) -> None:
    """Oracle TDE encrypted DRR should be 1.5 (encryption defeats dedup)."""
    assert drr_table.get_ratio("Database", "Oracle - TDE (Encrypted)") == 1.5


def test_oracle_hcc_tde_drr(drr_table: DRRTable) -> None:
    """Oracle HCC + TDE combined DRR should be 1.2 (most conservative)."""
    assert drr_table.get_ratio("Database", "Oracle - HCC + TDE") == 1.2


def test_sql_page_compressed_tde_drr(drr_table: DRRTable) -> None:
    """SQL Server page-compressed + TDE should yield 1.2."""
    assert drr_table.get_ratio("Database", "Microsoft SQL - Page Compressed + TDE") == 1.2


def test_ddve_drr(drr_table: DRRTable) -> None:
    """DDVE DRR should be 1.0 — data is already deduplicated by DDVE."""
    assert drr_table.get_ratio("VM Replication", "Data Domain Virtual Edition (DDVE)") == 1.0


def test_kubernetes_encrypted_pvs_drr(drr_table: DRRTable) -> None:
    """Kubernetes encrypted PVs DRR should be 1.3."""
    assert drr_table.get_ratio("Containers", "Kubernetes - Encrypted PVs") == 1.3


def test_veeam_compressed_dedup_drr(drr_table: DRRTable) -> None:
    """Veeam with compression+dedup enabled should yield 1.2."""
    assert drr_table.get_ratio("VM Replication", "Veeam - Compressed + Dedup") == 1.2
