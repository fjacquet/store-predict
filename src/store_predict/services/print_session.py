"""One-time token store for print session data.

Tokens are consumed on first read to prevent replay access.
Each token maps to a dict of serialisable session data (vm_data, project_name, locale, logo).
"""

from __future__ import annotations

import uuid
from typing import Any

_sessions: dict[str, dict[str, Any]] = {}


def create(data: dict[str, Any]) -> str:
    """Store *data* under a new UUID token and return the token string."""
    token = str(uuid.uuid4())
    _sessions[token] = data
    return token


def consume(token: str) -> dict[str, Any] | None:
    """Return and delete the data for *token*. Returns ``None`` if not found."""
    return _sessions.pop(token, None)
