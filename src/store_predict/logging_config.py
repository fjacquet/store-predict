"""Logging configuration for StorePredict.

SECURITY: NEVER log DataFrame contents, VM names, IPs, hostnames, or any
customer-identifiable data. Log only metadata: counts, format types, timing,
and error messages. This prevents accidental data leakage in production logs.
"""

from __future__ import annotations

import hashlib
import logging


def hash_name(name: str) -> str:
    """Return a short deterministic hash of a filename for safe logging.

    Filenames often encode project/customer identifiers; logging them raw leaks
    PII into aggregated log stores. A truncated SHA-256 is still useful for
    correlating events without disclosing the source name.
    """
    return hashlib.sha256(name.encode("utf-8", "replace")).hexdigest()[:12]


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the ``store_predict`` logger.

    Sets up a StreamHandler with a standard format including timestamp,
    level, and logger name. Safe to call multiple times -- handlers are
    only added if the logger has none.

    Args:
        level: Logging level (default: ``logging.INFO``).

    Returns:
        The configured ``store_predict`` logger instance.
    """
    logger = logging.getLogger("store_predict")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)

    return logger
