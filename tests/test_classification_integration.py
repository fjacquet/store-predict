"""Integration tests for the workload classification engine.

Tests classification against real sample data (610 LiveOptics VMs, RVTools)
and verifies rule-DRR table consistency. Uses real objects only -- NO mocks.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)
from store_predict.pipeline.ingestion import ingest_file
from store_predict.services.drr_table import DRRTable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registry() -> RuleRegistry:
    """Build a registry with the full default rule set."""
    return RuleRegistry(build_default_rules())


# ---------------------------------------------------------------------------
# 1. DRR table consistency tests
# ---------------------------------------------------------------------------

class TestDRRTableConsistency:
    """Verify that classification rules and DRR table are in sync."""

    def test_rule_categories_exist_in_drr_table(self, drr_table: DRRTable) -> None:
        """Every rule's (category, subcategory) must exist in DRR.csv."""
        drr_categories = {(e.category, e.subcategory) for e in drr_table.entries}
        for rule in build_default_rules():
            key = (rule.category, rule.subcategory)
            assert key in drr_categories, (
                f"Rule '{rule.name}' references ({rule.category!r}, "
                f"{rule.subcategory!r}) which does not exist in DRR table. "
                f"Available: {sorted(drr_categories)}"
            )

    def test_all_drr_categories_have_rules(self, drr_table: DRRTable) -> None:
        """Every DRR (category, subcategory) must have at least one matching rule.

        Exception: ("Custom DRR", "Custom DRR") is user-assigned only.
        """
        rule_categories = {
            (r.category, r.subcategory) for r in build_default_rules()
        }
        drr_categories = {
            (e.category, e.subcategory) for e in drr_table.entries
        }
        uncovered = drr_categories - rule_categories
        # Custom DRR is user-assigned only, not auto-classified
        uncovered.discard(("Custom DRR", "Custom DRR"))
        # "Content not included" is a user override -- cannot detect from
        # VM name/OS alone; default is "Content included" (conservative)
        uncovered.discard(("Web Servers", "Content not included"))
        assert uncovered == set(), (
            f"DRR categories without matching rules: {sorted(uncovered)}"
        )


# ---------------------------------------------------------------------------
# 2. LiveOptics sample classification tests
# ---------------------------------------------------------------------------

class TestLiveOpticsSampleClassification:
    """Integration tests using the real 610-VM LiveOptics sample."""

    def test_classify_liveoptics_sample_no_nulls(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """All 4 classification columns must be non-null for every row."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        for col in [
            "workload_category",
            "workload_subcategory",
            "classification_rule",
            "classification_confidence",
        ]:
            null_count = result[col].isna().sum()
            assert null_count == 0, (
                f"Column {col!r} has {null_count} null values"
            )

    def test_classify_liveoptics_sample_unknown_under_20pct(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """Unknown (Reducible) must be < 20% of total VMs.

        This is the primary success criterion from ROADMAP.md.
        """
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        total = len(result)
        unknown_count = (
            result["workload_category"] == "Unknown (Reducible)"
        ).sum()
        unknown_pct = unknown_count / total

        assert unknown_pct < 0.20, (
            f"Unknown (Reducible) is {unknown_pct:.1%} ({unknown_count}/{total})"
            f" -- must be < 20%"
        )

    def test_classify_liveoptics_sample_distribution(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """At least 5 distinct categories present in the classification."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        category_counts = result["workload_category"].value_counts()
        # Print for debugging (visible with pytest -s)
        print("\n=== LiveOptics Classification Distribution ===")
        for cat, count in category_counts.items():
            pct = count / len(result) * 100
            print(f"  {cat:40s} {count:4d}  ({pct:5.1f}%)")
        print(f"  {'TOTAL':40s} {len(result):4d}")

        distinct_categories = len(category_counts)
        assert distinct_categories >= 5, (
            f"Only {distinct_categories} distinct categories found: "
            f"{list(category_counts.index)}"
        )

    def test_classify_liveoptics_sql_vms(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with 'SQL' in name should all be classified as Database."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        sql_vms = result[result["vm_name"].str.upper().str.contains("SQL", na=False)]
        if len(sql_vms) == 0:
            pytest.skip("No VMs with 'SQL' in name found in sample")

        non_db = sql_vms[sql_vms["workload_category"] != "Database"]
        assert len(non_db) == 0, (
            f"{len(non_db)} SQL VMs not classified as Database: "
            f"{list(non_db['vm_name'])}"
        )

    def test_classify_liveoptics_citrix_vms(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with 'CIT' in name should all be classified as VDI."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        cit_vms = result[result["vm_name"].str.upper().str.contains("CIT", na=False)]
        if len(cit_vms) == 0:
            pytest.skip("No VMs with 'CIT' in name found in sample")

        non_vdi = cit_vms[cit_vms["workload_category"] != "VDI"]
        assert len(non_vdi) == 0, (
            f"{len(non_vdi)} Citrix VMs not classified as VDI: "
            f"{list(non_vdi['vm_name'])}"
        )

    def test_classify_liveoptics_fortinet_vms(
        self, liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with FortiNet OS should be Logging-Analytics."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        forti_vms = result[
            result["os_name"].str.contains("Forti", case=False, na=False)
        ]
        if len(forti_vms) == 0:
            pytest.skip("No VMs with FortiNet OS found in sample")

        non_logging = forti_vms[
            forti_vms["workload_category"] != "Logging - Analytics"
        ]
        assert len(non_logging) == 0, (
            f"{len(non_logging)} FortiNet VMs not classified as "
            f"Logging - Analytics: {list(non_logging['vm_name'])}"
        )


# ---------------------------------------------------------------------------
# 3. RVTools sample classification tests
# ---------------------------------------------------------------------------

class TestRVToolsSampleClassification:
    """Integration tests using the real RVTools sample."""

    def test_classify_rvtools_sample_no_nulls(
        self, rvtools_path: Path,
    ) -> None:
        """All 4 classification columns must be non-null for every row."""
        df = ingest_file(rvtools_path)
        result = classify_dataframe(df, _registry())

        for col in [
            "workload_category",
            "workload_subcategory",
            "classification_rule",
            "classification_confidence",
        ]:
            null_count = result[col].isna().sum()
            assert null_count == 0, (
                f"Column {col!r} has {null_count} null values"
            )


# ---------------------------------------------------------------------------
# 4. End-to-end pipeline test
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """Full pipeline: ingest -> classify -> DRR lookup."""

    def test_ingest_then_classify_pipeline(
        self,
        liveoptics_xlsx_path: Path,
        drr_table: DRRTable,
    ) -> None:
        """Every classified VM must have a valid DRR ratio > 0."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        for _, row in result.iterrows():
            ratio = drr_table.get_ratio(
                row["workload_category"],
                row["workload_subcategory"],
            )
            assert ratio > 0, (
                f"VM {row['vm_name']!r} classified as "
                f"({row['workload_category']!r}, {row['workload_subcategory']!r}) "
                f"has DRR ratio {ratio} (expected > 0)"
            )
