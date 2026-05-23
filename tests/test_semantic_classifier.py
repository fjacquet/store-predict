"""Tests for SemanticClassifier using the real FastEmbed encoder.

These exercise real embeddings (no mocks, per project conventions). The model
is downloaded on first run and cached; tests are marked slow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from store_predict.pipeline.semantic_classifier import (
    SemanticClassifier,
    SemanticVerdict,
)
from store_predict.services.semantic_config import SemanticConfig

_FIXTURE = Path(__file__).parent / "fixtures" / "exemplars_min.yaml"


@pytest.fixture(scope="module")
def classifier() -> SemanticClassifier:
    cfg = SemanticConfig(score_threshold=0.3)
    return SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)


@pytest.mark.slow
def test_classifies_obvious_sql(classifier: SemanticClassifier) -> None:
    verdict = classifier.classify("production microsoft sql server database")
    assert verdict is not None
    assert verdict.category == "Database"
    assert verdict.subcategory == "Microsoft SQL"
    assert 0.0 <= verdict.score <= 1.0


@pytest.mark.slow
def test_classifies_kubernetes(classifier: SemanticClassifier) -> None:
    verdict = classifier.classify("kubernetes container worker node")
    assert verdict is not None
    assert verdict.category == "Containers"


@pytest.mark.slow
def test_below_threshold_returns_none() -> None:
    cfg = SemanticConfig(score_threshold=0.99)  # nothing will clear this
    clf = SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)
    assert clf.classify("xyzzy completely unrelated gibberish 12345") is None


@pytest.mark.slow
def test_empty_text_returns_none(classifier: SemanticClassifier) -> None:
    assert classifier.classify("   ") is None


@pytest.mark.slow
def test_self_learning_shifts_ambiguous_match() -> None:
    cfg = SemanticConfig(score_threshold=0.3)
    clf = SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)
    # Teach the SQL route a customer-specific naming token, then verify a
    # sibling host using that token routes to the learned category.
    clf.add_learned({("Database", "Microsoft SQL"): ["acme-dbx-01", "acme-dbx-02"]})
    verdict = clf.classify("acme-dbx-07")
    assert verdict is not None
    assert verdict.category == "Database"


def test_verdict_is_frozen() -> None:
    v = SemanticVerdict(
        category="Database", subcategory="Microsoft SQL", route_name="Database|Microsoft SQL", score=0.8
    )
    with pytest.raises(AttributeError):
        v.score = 0.1  # type: ignore[misc]
