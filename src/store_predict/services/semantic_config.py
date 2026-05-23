"""Configuration for the semantic-router classification tier.

Reads from environment variables with the ``SEMANTIC_`` prefix (case-insensitive),
mirroring the ``LLMConfig`` pattern. The ``get_semantic_config()`` singleton reads
env vars once at first call. Tests override by instantiating ``SemanticConfig()``
directly, which bypasses the singleton cache.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SemanticConfig(BaseSettings):
    """Settings for the FastEmbed semantic classifier.

    Fields:
        enabled: Whether the semantic tier runs. Default ``True``.
        model: FastEmbed ONNX model name. Default ``BAAI/bge-small-en-v1.5``.
        score_threshold: Global minimum similarity for a route to win. Default
            ``0.5``; tuned per-route via ``scripts/tune_semantic_thresholds.py``.
        self_learning: Whether same-file override hits seed extra utterances.
            Default ``True``.
    """

    model_config = SettingsConfigDict(env_prefix="SEMANTIC_", case_sensitive=False)

    enabled: bool = True
    model: str = "BAAI/bge-small-en-v1.5"
    score_threshold: float = 0.5
    self_learning: bool = True


@lru_cache(maxsize=1)
def get_semantic_config() -> SemanticConfig:
    """Lazy singleton — reads env vars once at first call."""
    return SemanticConfig()
