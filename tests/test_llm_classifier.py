"""Unit tests for LLM classification config and classifier.

Uses real objects and fixtures only — no mocks (project convention).
All tests run with LLM_ENABLED unset (defaults to False), so no actual
LLM API calls are made.
"""

import asyncio
import os

from store_predict.pipeline.llm_classifier import classify_unknown_vms_async
from store_predict.services.drr_table import DRRTable
from store_predict.services.llm_config import LLMConfig


def test_llm_disabled_by_default() -> None:
    """LLMConfig.enabled defaults to False with no env vars set."""
    config = LLMConfig()
    assert config.enabled is False


def test_api_key_not_exposed_in_repr() -> None:
    """SecretStr must mask the API key in repr() and str()."""
    os.environ["LLM_API_KEY"] = "sk-secret-test-key"
    try:
        config = LLMConfig()
        assert "sk-secret-test-key" not in repr(config)
        assert "sk-secret-test-key" not in str(config)
    finally:
        del os.environ["LLM_API_KEY"]


def test_classifier_skips_when_disabled(drr_table: DRRTable) -> None:
    """classify_unknown_vms_async returns records unchanged when LLM is disabled."""
    records = [{"vm_name": "UNKNOWN-01", "os_name": "", "classification_confidence": "default"}]
    config = LLMConfig()  # enabled=False
    result = asyncio.run(classify_unknown_vms_async(records, drr_table, config))
    assert result[0]["classification_confidence"] == "default"


def test_classifier_skips_non_default_records(drr_table: DRRTable) -> None:
    """classify_unknown_vms_async leaves rule-matched records untouched."""
    records = [{"vm_name": "SQL-01", "os_name": "Windows", "classification_confidence": "rule_match"}]
    config = LLMConfig()  # enabled=False
    result = asyncio.run(classify_unknown_vms_async(records, drr_table, config))
    assert result[0]["classification_confidence"] == "rule_match"


def test_llm_config_max_concurrent_default() -> None:
    """max_concurrent defaults to 5."""
    config = LLMConfig()
    assert config.max_concurrent == 5


def test_llm_config_timeout_default() -> None:
    """timeout defaults to 30 seconds."""
    config = LLMConfig()
    assert config.timeout == 30


def test_get_api_key_returns_string() -> None:
    """get_api_key() returns the raw key string (not the SecretStr wrapper)."""
    os.environ["LLM_API_KEY"] = "test-key-value"
    try:
        config = LLMConfig()
        assert config.get_api_key() == "test-key-value"
    finally:
        del os.environ["LLM_API_KEY"]
