# tests/test_classification_cascade.py
"""Tests for the override -> semantic -> default cascade in classify_dataframe."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

_FIXTURE = Path(__file__).parent / "fixtures" / "exemplars_min.yaml"


def _df(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_override_wins_and_is_labelled_override() -> None:
    df = _df([{"vm_name": "PRD-MSSQL-01", "os_name": "Windows Server 2019"}])
    reg = RuleRegistry(build_override_rules())
    out = classify_dataframe(df, reg)  # no semantic tier
    assert out.loc[0, "workload_category"] == "Database"
    assert out.loc[0, "classification_confidence"] == "override"
    assert out.loc[0, "classification_rule"].startswith("override:")


def test_unmatched_without_semantic_is_default() -> None:
    df = _df([{"vm_name": "GENERIC-APP-01", "os_name": "Windows Server 2019"}])
    reg = RuleRegistry(build_override_rules())
    out = classify_dataframe(df, reg)
    assert out.loc[0, "classification_confidence"] == "default"
    assert out.loc[0, "workload_subcategory"] == "Unknown (Reducible)"


@pytest.mark.slow
def test_semantic_classifies_unmatched() -> None:
    # "SMTP-RELAY-01" has no override-rule match (no Exchange/Zimbra/Mail keyword
    # at word boundary that override rules test for), but the combined text
    # "SMTP-RELAY-01 Linux zimbra mail server" is semantically close to Email
    # in the min-exemplars fixture and scores above threshold=0.3.
    df = _df([{"vm_name": "SMTP-RELAY-01", "os_name": "Linux zimbra mail server"}])
    reg = RuleRegistry(build_override_rules())
    sem = SemanticClassifier(config=SemanticConfig(score_threshold=0.3), exemplars_path=_FIXTURE)
    out = classify_dataframe(df, reg, semantic=sem)
    assert out.loc[0, "workload_category"] == "Email"
    assert out.loc[0, "classification_confidence"] == "semantic"
    assert out.loc[0, "classification_rule"].startswith("semantic:")


@pytest.mark.slow
def test_below_threshold_falls_to_default_not_crash() -> None:
    df = _df([{"vm_name": "zzz unrelated gibberish", "os_name": ""}])
    reg = RuleRegistry(build_override_rules())
    sem = SemanticClassifier(config=SemanticConfig(score_threshold=0.99), exemplars_path=_FIXTURE)
    out = classify_dataframe(df, reg, semantic=sem)
    assert out.loc[0, "classification_confidence"] == "default"
