"""Regression test against a real customer RVTools export.

Gated by CUSTOMER_FILE existence so CI without the file passes silently.
The file path is the one analysed during the v8.3 classifier-improvement work
(May 2026 customer engagement).

Targets validated by hand against the same data:
    - SAP HANA(S4)         >= 12 VMs (folder /SAP_Dina/HanaDB/*)
    - Email                >=  7 VMs (folder /EXCH/*)
    - DDVE (Nutanix CVMs)  >=  6 VMs (folder /NTNX CVMs/*)
    - default confidence    <= 15 VMs (NaN OS rows in /AUTO_DEPLOYED/)
    - unknown/default rate <= 300 VMs (semantic tier replaces old os_fallback path)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.parsers.rvtools import parse_rvtools
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

CUSTOMER_FILE = Path(
    "/Users/fjacquet/Library/CloudStorage/OneDrive-Home/20260430_1400_allvCenters.xlsx",
)


@pytest.fixture(scope="module")
def classified_customer_df():  # type: ignore[no-untyped-def]
    if not CUSTOMER_FILE.exists():
        pytest.skip(f"Customer baseline file not present: {CUSTOMER_FILE}")
    df = parse_rvtools(CUSTOMER_FILE)
    df = df[df["is_powered_on"]].reset_index(drop=True)
    registry = RuleRegistry(build_override_rules())
    semantic = SemanticClassifier(config=SemanticConfig())
    return classify_dataframe(df, registry, semantic=semantic)


def _summary(df) -> str:  # type: ignore[no-untyped-def]
    return df["workload_subcategory"].value_counts().to_string()


@pytest.mark.slow
def test_default_confidence_low(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    n_default = (classified_customer_df["classification_confidence"] == "default").sum()
    assert n_default <= 15, f"Too many 'default' VMs ({n_default}); summary:\n{_summary(classified_customer_df)}"


@pytest.mark.slow
def test_unknown_rate_not_regressed(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    """The semantic tier must classify the bulk of formerly-OS-fallback VMs.
    The v9 ruleset put ~940 VMs in os_fallback; semantic routing should pull
    most of those into real categories, leaving few as 'default' (Unknown)."""
    total = len(classified_customer_df)
    n_default = int((classified_customer_df["classification_confidence"] == "default").sum())
    assert n_default <= 300, f"Unknown/default rate too high: {n_default}/{total}\n{_summary(classified_customer_df)}"


@pytest.mark.slow
def test_sap_hana_bucket(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    n_hana = (classified_customer_df["workload_subcategory"] == "SAP HANA(S4)").sum()
    assert n_hana >= 12, f"Expected >=12 SAP HANA VMs, got {n_hana}\n{_summary(classified_customer_df)}"


@pytest.mark.slow
def test_email_bucket(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    n_email = (classified_customer_df["workload_category"] == "Email").sum()
    assert n_email >= 7, f"Expected >=7 Email VMs, got {n_email}\n{_summary(classified_customer_df)}"


@pytest.mark.slow
def test_ddve_bucket_nutanix(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    n_ddve = (classified_customer_df["workload_subcategory"] == "Data Domain Virtual Edition (DDVE)").sum()
    assert n_ddve >= 6, f"Expected >=6 DDVE (Nutanix CVM) VMs, got {n_ddve}\n{_summary(classified_customer_df)}"


@pytest.mark.slow
def test_v900_large_databearing_takes_unknown_volume(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    """The size-aware reroute (ADR-080) must still move a substantial number of
    large unknown VMs to File / General Purpose, and the residual generic
    'VMware / Hyper-V / KVM' bucket must stay small.

    This asserts the *invariant* (reroute materially active + generic bucket
    small), not a precise count: the exact number of rerouted VMs depends on the
    semantic exemplars and score threshold, which shift it (v9 os-fallback ruleset
    rerouted ~600; v10 with the curated exemplars reroutes ~380-460 because more
    formerly-generic VMs now get real semantic categories). On the May 2026 file
    (1373 VMs) we measure ~384 rerouted and a ~184-VM generic bucket. The bounds
    below carry generous margin so routine exemplar/threshold tuning does not
    break the test while still proving the reroute does meaningful work. Counted
    by classification_rule so genuinely-classified File/General Purpose servers
    are not conflated.
    """
    n_large = (classified_customer_df["classification_rule"] == "Large generic (>=100 GiB)").sum()
    n_generic = (
        classified_customer_df["workload_subcategory"] == "VMware / Hyper-V / KVM - No Database, File nor Email"
    ).sum()
    assert n_large >= 300, f"Expected >=300 size-rerouted VMs, got {n_large}\n{_summary(classified_customer_df)}"
    assert n_generic <= 350, (
        f"Generic VMware/Hyper-V bucket should stay small after the size-aware reroute, got {n_generic}\n"
        f"{_summary(classified_customer_df)}"
    )


@pytest.mark.slow
def test_powerflex_routes_to_containers(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    pflex = classified_customer_df[classified_customer_df["vm_folder"].str.contains("/PowerFlex", na=False)]
    if len(pflex) == 0:
        pytest.skip("No /PowerFlex VMs in this dataset")
    cats = set(pflex["workload_category"].unique())
    assert cats == {"Containers"}, f"PowerFlex VMs not routed to Containers: {cats}"
