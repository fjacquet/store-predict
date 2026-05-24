"""Guard against runtime/packaging version drift.

``store_predict.__version__`` is derived from package metadata, so it must match
the version declared in ``pyproject.toml`` (the single source of truth). CI
installs the package before running tests, so the metadata is current here.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import store_predict


def test_runtime_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))
    declared = pyproject["project"]["version"]
    assert store_predict.__version__ == declared, (
        f"runtime __version__={store_predict.__version__!r} != pyproject version={declared!r}; "
        "reinstall the package (uv pip install -e .) so metadata is current"
    )
