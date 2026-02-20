"""LLM configuration settings for the classification fallback feature.

Reads configuration from environment variables with the ``LLM_`` prefix.

Default provider: OpenRouter with Mistral Small 3.1.
To use OpenRouter, set:

    LLM_ENABLED=true
    LLM_API_KEY=<your OpenRouter key>
    LLM_API_BASE=https://openrouter.ai/api/v1

For the free tier use model ``mistralai/mistral-small-3.1-24b-instruct:free``.
Set ``LLM_MODEL`` to override the default model.

The ``get_llm_config()`` singleton reads env vars once at first call.
Tests that need to override env vars should instantiate ``LLMConfig()``
directly — this bypasses the singleton cache, which is the correct testing
pattern.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuration for the LLM classification fallback.

    All fields are read from environment variables with the ``LLM_`` prefix
    (case-insensitive).  For example, ``LLM_ENABLED=true`` sets
    :attr:`enabled` to ``True``.

    Fields:
        enabled: Whether LLM classification is active. Defaults to ``False``.
        model: litellm model identifier. Defaults to
            ``mistralai/mistral-small-3.1-24b-instruct``.
        api_key: Provider API key. Stored as :class:`~pydantic.SecretStr` so
            the value is never exposed in ``repr()`` or ``str()``.
        api_base: Optional custom API base URL (e.g. OpenRouter endpoint).
        timeout: Per-request timeout in seconds. Defaults to ``30``.
        max_concurrent: Maximum simultaneous LLM calls. Defaults to ``5``.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)

    enabled: bool = False
    model: str = "mistralai/mistral-small-3.1-24b-instruct"
    api_key: SecretStr = SecretStr("")
    api_base: str | None = None
    timeout: int = 30
    max_concurrent: int = 5

    def get_api_key(self) -> str:
        """Return raw key string ONLY at call site — never log the return value."""
        return self.api_key.get_secret_value()


@lru_cache(maxsize=1)
def get_llm_config() -> LLMConfig:
    """Lazy singleton — reads env vars once at first call."""
    return LLMConfig()
