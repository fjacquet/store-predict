"""Tests for SemanticConfig (env-driven configuration via env-var settings pattern)."""

from __future__ import annotations

from store_predict.services.semantic_config import SemanticConfig


def test_defaults() -> None:
    cfg = SemanticConfig()
    assert cfg.enabled is True
    assert cfg.model == "BAAI/bge-small-en-v1.5"
    assert 0.0 < cfg.score_threshold < 1.0
    assert cfg.self_learning is True


def test_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SEMANTIC_ENABLED", "false")
    monkeypatch.setenv("SEMANTIC_SCORE_THRESHOLD", "0.42")
    cfg = SemanticConfig()
    assert cfg.enabled is False
    assert cfg.score_threshold == 0.42
