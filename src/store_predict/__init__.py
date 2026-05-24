"""StorePredict — Dell PowerStore DRR sizing tool.

``__version__`` is derived from the installed package metadata (single source of
truth: ``pyproject.toml``) so runtime and packaging versions never drift apart.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("store-predict")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

__all__ = ["__version__"]
