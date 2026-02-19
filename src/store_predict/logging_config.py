"""Logging configuration for StorePredict.

SECURITY: NEVER log DataFrame contents, VM names, IPs, hostnames, or any
customer-identifiable data. Log only metadata: counts, format types, timing,
and error messages. This prevents accidental data leakage in production logs.
"""

from __future__ import annotations

import logging


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
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
