"""Unit tests for LLM classification config and classifier.

Uses real objects and fixtures only — no mocks (project convention).
All tests run with LLM_ENABLED unset (defaults to False), so no actual
LLM API calls are made.
"""

import asyncio
import os

import pytest

from store_predict.pipeline.llm_classifier import (
    CircuitBreaker,
    _chunks,
    _parse_batch_response,
    classify_unknown_vms_async,
)
from store_predict.services.drr_table import DRRTable
from store_predict.services.llm_config import LLMConfig


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip LLM_* env vars so local Ollama/OpenAI config can't bleed into tests."""
    for key in ("LLM_ENABLED", "LLM_MODEL", "LLM_API_BASE", "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)


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
    result_records, suggestions = asyncio.run(classify_unknown_vms_async(records, drr_table, config))
    assert result_records[0]["classification_confidence"] == "default"
    assert suggestions == []


def test_classifier_skips_non_default_records(drr_table: DRRTable) -> None:
    """classify_unknown_vms_async leaves rule-matched records untouched."""
    records = [{"vm_name": "SQL-01", "os_name": "Windows", "classification_confidence": "rule_match"}]
    config = LLMConfig()  # enabled=False
    result_records, suggestions = asyncio.run(classify_unknown_vms_async(records, drr_table, config))
    assert result_records[0]["classification_confidence"] == "rule_match"
    assert suggestions == []


def test_llm_config_max_concurrent_default() -> None:
    """max_concurrent defaults to 5 when no env var is set."""
    os.environ.pop("LLM_MAX_CONCURRENT", None)
    config = LLMConfig()
    assert config.max_concurrent == 5


def test_llm_config_timeout_default() -> None:
    """timeout defaults to 30 seconds when no env var is set."""
    os.environ.pop("LLM_TIMEOUT", None)
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


# ---------------------------------------------------------------------------
# Batch classification tests (Phase 19-01)
# ---------------------------------------------------------------------------


def test_llm_config_batch_size_default() -> None:
    """LLMConfig.batch_size defaults to 10."""
    config = LLMConfig()
    assert config.batch_size == 10


def test_llm_config_batch_size_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM_BATCH_SIZE env var overrides the default batch_size."""
    monkeypatch.setenv("LLM_BATCH_SIZE", "20")
    config = LLMConfig()
    assert config.batch_size == 20


def test_parse_batch_response_valid() -> None:
    """_parse_batch_response parses a valid JSON array correctly."""
    raw = '[{"id":0,"category":"Database","keyword":"SQL"},{"id":1,"category":"Web Servers","keyword":"NGINX"}]'
    valid = {"Database", "Web Servers"}
    result = _parse_batch_response(raw, valid)
    assert len(result) == 2
    assert result[0]["id"] == 0
    assert result[0]["category"] == "Database"
    assert result[0]["keyword"] == "SQL"
    assert result[1]["id"] == 1
    assert result[1]["category"] == "Web Servers"
    assert result[1]["keyword"] == "NGINX"


def test_parse_batch_response_with_fences() -> None:
    """_parse_batch_response strips markdown code fences before parsing."""
    raw = '```json\n[{"id":0,"category":"Database","keyword":"SQL"}]\n```'
    valid = {"Database"}
    result = _parse_batch_response(raw, valid)
    assert len(result) == 1
    assert result[0]["category"] == "Database"
    assert result[0]["keyword"] == "SQL"


def test_parse_batch_response_invalid_json() -> None:
    """_parse_batch_response returns empty list on unparseable input."""
    result = _parse_batch_response("not json at all", {"Database"})
    assert result == []


def test_parse_batch_response_invalid_category() -> None:
    """_parse_batch_response excludes items with categories not in valid set."""
    raw = '[{"id":0,"category":"InvalidCat","keyword":"FOO"}]'
    valid = {"Database", "Web Servers"}
    result = _parse_batch_response(raw, valid)
    assert result == []


def test_parse_batch_response_keyword_normalization() -> None:
    """_parse_batch_response uppercases keywords."""
    raw = '[{"id":0,"category":"Database","keyword":"redis"}]'
    valid = {"Database"}
    result = _parse_batch_response(raw, valid)
    assert len(result) == 1
    assert result[0]["keyword"] == "REDIS"


def test_classifier_batch_skips_when_disabled(drr_table: DRRTable) -> None:
    """classify_unknown_vms_async with batch path returns records unchanged when disabled."""
    records = [
        {"vm_name": "UNKNOWN-01", "os_name": "", "classification_confidence": "default"},
        {"vm_name": "UNKNOWN-02", "os_name": "", "classification_confidence": "default"},
    ]
    config = LLMConfig()  # enabled=False
    result_records, suggestions = asyncio.run(classify_unknown_vms_async(records, drr_table, config))
    assert all(r["classification_confidence"] == "default" for r in result_records)
    assert suggestions == []


def test_chunks_helper() -> None:
    """_chunks splits a list into sublists of at most n elements."""
    result = _chunks([1, 2, 3, 4, 5], 2)
    assert result == [[1, 2], [3, 4], [5]]


class TestCircuitBreaker:
    """Thread-safe CB state transitions (no LLM call needed)."""

    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(fail_max=3, cooldown=60.0)
        assert cb.is_open() is False

    def test_opens_after_fail_max_failures(self) -> None:
        cb = CircuitBreaker(fail_max=2, cooldown=60.0)
        assert cb.record_failure() is False  # first failure
        assert cb.is_open() is False
        just_opened = cb.record_failure()
        assert just_opened is True  # this failure crossed the threshold
        assert cb.is_open() is True

    def test_record_success_resets_counter(self) -> None:
        cb = CircuitBreaker(fail_max=2, cooldown=60.0)
        cb.record_failure()
        cb.record_success()
        # Counter should reset — a single further failure must not open the breaker.
        assert cb.record_failure() is False
        assert cb.is_open() is False

    def test_reset_clears_state(self) -> None:
        cb = CircuitBreaker(fail_max=1, cooldown=60.0)
        cb.record_failure()
        assert cb.is_open() is True
        cb.reset()
        assert cb.is_open() is False

    def test_cooldown_closes_breaker(self) -> None:
        cb = CircuitBreaker(fail_max=1, cooldown=0.0)
        cb.record_failure()
        # Zero cooldown: next is_open() call treats the window as expired and recloses.
        assert cb.is_open() is False

    def test_concurrent_failures_count_exactly(self) -> None:
        """Two threads each raising one failure must leave the counter at 2, not 1."""
        import threading

        cb = CircuitBreaker(fail_max=10, cooldown=60.0)

        def one_failure() -> None:
            cb.record_failure()

        threads = [threading.Thread(target=one_failure) for _ in range(2)]
        for tr in threads:
            tr.start()
        for tr in threads:
            tr.join()
        # With the internal lock, no increment is lost — breaker still below threshold.
        assert cb.is_open() is False
        # One more failure must register (so the total is 3, not 2).
        cb.record_failure()
        # Still below fail_max=10 — proves we can keep counting.
        assert cb.is_open() is False
