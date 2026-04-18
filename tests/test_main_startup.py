"""Tests for main._resolve_storage_secret fail-closed behavior."""

from __future__ import annotations

import pytest

from store_predict.main import _resolve_storage_secret


def test_production_requires_storage_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing STORAGE_SECRET in production must raise RuntimeError."""
    monkeypatch.delenv("STORAGE_SECRET", raising=False)
    monkeypatch.delenv("STORE_PREDICT_DEV", raising=False)
    with pytest.raises(RuntimeError, match="STORAGE_SECRET must be set"):
        _resolve_storage_secret()


def test_explicit_secret_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured STORAGE_SECRET flows through unchanged with is_dev=False by default."""
    monkeypatch.setenv("STORAGE_SECRET", "explicit-value")
    monkeypatch.delenv("STORE_PREDICT_DEV", raising=False)
    secret, is_dev = _resolve_storage_secret()
    assert secret == "explicit-value"
    assert is_dev is False


def test_dev_mode_without_secret_mints_ephemeral(monkeypatch: pytest.MonkeyPatch) -> None:
    """STORE_PREDICT_DEV=1 without STORAGE_SECRET mints an ephemeral (not fixed) secret."""
    monkeypatch.delenv("STORAGE_SECRET", raising=False)
    monkeypatch.setenv("STORE_PREDICT_DEV", "1")
    secret_a, is_dev = _resolve_storage_secret()
    assert is_dev is True
    assert secret_a  # non-empty
    assert secret_a != "dev-only-not-for-production"
    # Each call mints a fresh token — sessions must not survive process restart.
    secret_b, _ = _resolve_storage_secret()
    assert secret_a != secret_b


def test_dev_mode_with_secret_preserves_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit secret wins even in dev mode, so local setups stay reproducible."""
    monkeypatch.setenv("STORAGE_SECRET", "explicit-value")
    monkeypatch.setenv("STORE_PREDICT_DEV", "1")
    secret, is_dev = _resolve_storage_secret()
    assert secret == "explicit-value"
    assert is_dev is True
