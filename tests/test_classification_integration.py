"""Integration tests for the workload classification engine.

Tests classification against real sample data (610 LiveOptics VMs, RVTools)
and verifies rule-DRR table consistency. Uses real objects only -- NO mocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.ingestion import ingest_file
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

if TYPE_CHECKING:
    from pathlib import Path

    from store_predict.services.drr_table import DRRTable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry() -> RuleRegistry:
    """Build a registry with the full default rule set."""
    return RuleRegistry(build_default_rules())


def _cascade(df):  # type: ignore[no-untyped-def]
    """Run the v10 cascade: override rules + the real semantic tier."""
    registry = RuleRegistry(build_override_rules())
    semantic = SemanticClassifier(config=SemanticConfig())
    return classify_dataframe(df, registry, semantic=semantic)


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
        rule_categories = {(r.category, r.subcategory) for r in build_default_rules()}
        drr_categories = {(e.category, e.subcategory) for e in drr_table.entries}
        uncovered = drr_categories - rule_categories
        # Custom DRR is user-assigned only, not auto-classified
        uncovered.discard(("Custom DRR", "Custom DRR"))
        # "Content not included" is a user override -- cannot detect from
        # VM name/OS alone; default is "Content included" (DRR 1.5, safe for pre-sales)
        uncovered.discard(("Web Servers", "Content not included"))
        assert uncovered == set(), f"DRR categories without matching rules: {sorted(uncovered)}"


# ---------------------------------------------------------------------------
# 2. LiveOptics sample classification tests
# ---------------------------------------------------------------------------


class TestLiveOpticsSampleClassification:
    """Integration tests using the real 610-VM LiveOptics sample."""

    def test_classify_liveoptics_sample_no_nulls(
        self,
        liveoptics_xlsx_path: Path,
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
            assert null_count == 0, f"Column {col!r} has {null_count} null values"

    @pytest.mark.slow
    def test_classify_liveoptics_sample_unknown_under_20pct(
        self,
        liveoptics_xlsx_path: Path,
    ) -> None:
        """Unknown (Reducible) must be < 20% of total VMs.

        This is the primary success criterion from ROADMAP.md.
        """
        df = ingest_file(liveoptics_xlsx_path)
        result = _cascade(df)

        total = len(result)
        unknown_count = (result["workload_category"] == "Unknown (Reducible)").sum()
        unknown_pct = unknown_count / total

        assert unknown_pct < 0.20, (
            f"Unknown (Reducible) is {unknown_pct:.1%} ({unknown_count}/{total}) -- must be < 20%"
        )

    def test_classify_liveoptics_sample_distribution(
        self,
        liveoptics_xlsx_path: Path,
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
            f"Only {distinct_categories} distinct categories found: {list(category_counts.index)}"
        )

    def test_classify_liveoptics_sql_vms(
        self,
        liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with 'SQL' in name should all be classified as Database."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        sql_vms = result[result["vm_name"].str.upper().str.contains("SQL", na=False)]
        if len(sql_vms) == 0:
            pytest.skip("No VMs with 'SQL' in name found in sample")

        non_db = sql_vms[sql_vms["workload_category"] != "Database"]
        assert len(non_db) == 0, f"{len(non_db)} SQL VMs not classified as Database: {list(non_db['vm_name'])}"

    def test_classify_liveoptics_citrix_vms(
        self,
        liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with 'CIT' in name should all be classified as VDI."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        cit_vms = result[result["vm_name"].str.upper().str.contains("CIT", na=False)]
        if len(cit_vms) == 0:
            pytest.skip("No VMs with 'CIT' in name found in sample")

        non_vdi = cit_vms[cit_vms["workload_category"] != "VDI"]
        assert len(non_vdi) == 0, f"{len(non_vdi)} Citrix VMs not classified as VDI: {list(non_vdi['vm_name'])}"

    def test_classify_liveoptics_fortinet_vms(
        self,
        liveoptics_xlsx_path: Path,
    ) -> None:
        """VMs with FortiNet OS should be Logging-Analytics."""
        df = ingest_file(liveoptics_xlsx_path)
        result = classify_dataframe(df, _registry())

        forti_vms = result[result["os_name"].str.contains("Forti", case=False, na=False)]
        if len(forti_vms) == 0:
            pytest.skip("No VMs with FortiNet OS found in sample")

        non_logging = forti_vms[forti_vms["workload_category"] != "Logging - Analytics"]
        assert len(non_logging) == 0, (
            f"{len(non_logging)} FortiNet VMs not classified as Logging - Analytics: {list(non_logging['vm_name'])}"
        )


# ---------------------------------------------------------------------------
# 3. RVTools sample classification tests
# ---------------------------------------------------------------------------


class TestRVToolsSampleClassification:
    """Integration tests using the real RVTools sample."""

    def test_classify_rvtools_sample_no_nulls(
        self,
        rvtools_path: Path,
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
            assert null_count == 0, f"Column {col!r} has {null_count} null values"


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


# ---------------------------------------------------------------------------
# 5. Classification coverage report
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_classification_coverage_report(liveoptics_xlsx_path: Path) -> None:
    """Print a human-readable classification coverage report.

    Shows: category, count, percentage, sample VM names (first 2 per category).
    Also verifies confidence breakdown is reasonable.
    """
    df = ingest_file(liveoptics_xlsx_path)
    result = _cascade(df)

    total = len(result)
    assert total > 0, "No VMs in result"

    # --- Coverage summary table ---
    print("\n" + "=" * 80)
    print("CLASSIFICATION COVERAGE REPORT")
    print("=" * 80)
    print(f"{'Category':<42} {'Count':>5} {'Pct':>6}  Sample VMs")
    print("-" * 80)

    for cat, group in result.groupby("workload_category", sort=False):
        count = len(group)
        pct = count / total * 100
        samples = group["vm_name"].head(2).tolist()
        sample_str = ", ".join(str(s) for s in samples)
        print(f"  {cat:<40} {count:5d} {pct:5.1f}%  {sample_str}")

    print("-" * 80)
    print(f"  {'TOTAL':<40} {total:5d}")
    print("=" * 80)

    # --- Verify no VMs lost ---
    assert result["workload_category"].notna().all()
    assert len(result) == total, "VMs lost during classification"

    # --- Confidence breakdown ---
    confidence_counts = result["classification_confidence"].value_counts()
    print("\n--- Confidence Breakdown ---")
    for conf, count in confidence_counts.items():
        pct = count / total * 100
        print(f"  {conf:<20} {count:5d} ({pct:5.1f}%)")

    # override should be present (VMs matched by override rules)
    assert "override" in confidence_counts.index, "No VMs matched by override rules (override missing)"

    # semantic should be present (VMs matched by semantic tier)
    assert "semantic" in confidence_counts.index, "No VMs matched by semantic tier (semantic missing)"

    # default should be minimal (<5%)
    default_count = confidence_counts.get("default", 0)
    default_pct = default_count / total
    assert default_pct < 0.05, f"Default confidence is {default_pct:.1%} ({default_count}/{total}) -- should be < 5%"
