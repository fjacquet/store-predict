"""Tests for log sanitization and session isolation.

Verifies that pipeline modules never log DataFrame contents and that
session data uses tab-scoped storage for isolation.
"""

from __future__ import annotations

import re
from pathlib import Path

# Forbidden patterns: logging or printing DataFrame objects
_FORBIDDEN_PATTERNS = [
    re.compile(r"logger\.(debug|info|warning|error)\(\s*df\b"),
    re.compile(r"print\(\s*df\b"),
    re.compile(r"logging\.(debug|info|warning|error)\(\s*df\b"),
]

_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "src" / "store_predict" / "pipeline"
_PIPELINE_MODULES = ["ingestion.py", "classification.py", "validation.py"]


def test_pipeline_modules_do_not_log_dataframes() -> None:
    """Pipeline modules must not contain logger/print calls with DataFrame objects."""
    for module_name in _PIPELINE_MODULES:
        source_path = _PIPELINE_DIR / module_name
        assert source_path.exists(), f"Missing pipeline module: {source_path}"
        source = source_path.read_text()
        for pattern in _FORBIDDEN_PATTERNS:
            matches = pattern.findall(source)
            assert not matches, (
                f"Forbidden DataFrame logging in {module_name}: "
                f"found pattern {pattern.pattern}"
            )


def test_logging_config_has_sanitization_docstring() -> None:
    """logging_config.py must include a sanitization warning in its docstring."""
    config_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "store_predict"
        / "logging_config.py"
    )
    source = config_path.read_text()
    assert "NEVER log DataFrame" in source, (
        "logging_config.py must contain sanitization warning about DataFrame logging"
    )
    assert "customer-identifiable" in source.lower() or "customer" in source.lower(), (
        "logging_config.py must warn about customer data"
    )


def test_session_state_uses_tab_storage() -> None:
    """state.py must use app.storage.tab for per-session isolation (NFR-5.3)."""
    state_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "store_predict"
        / "ui"
        / "state.py"
    )
    source = state_path.read_text()
    assert "app.storage.tab" in source, (
        "state.py must use app.storage.tab for tab-scoped session isolation"
    )
    # Verify both save and load functions reference tab storage
    assert "save_session_data" in source, "state.py must define save_session_data"
    assert "load_session_data" in source, "state.py must define load_session_data"
