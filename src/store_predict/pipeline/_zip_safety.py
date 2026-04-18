"""Shared ZIP archive safety helpers.

Centralizes zip-bomb and path-traversal defenses so every code path that
opens user-supplied archives applies the same rules.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from store_predict.pipeline.errors import IngestionError

if TYPE_CHECKING:
    import zipfile

__all__ = [
    "MAX_UNCOMPRESSED_BYTES",
    "assert_zip_within_limits",
    "safe_member_name",
]

MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


def assert_zip_within_limits(zf: zipfile.ZipFile) -> None:
    """Raise IngestionError if the total uncompressed size exceeds the limit.

    Reads the central directory only; no extraction is performed.
    """
    total = sum(info.file_size for info in zf.infolist())
    if total > MAX_UNCOMPRESSED_BYTES:
        raise IngestionError(
            f"ZIP archive uncompressed content exceeds the {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB limit"
        )


def safe_member_name(name: str) -> str:
    """Return the basename of a zip member after rejecting traversal attempts.

    Rejects absolute paths, ``..`` components, and empty names so a malicious
    archive cannot write outside the intended extraction directory even if the
    caller passes the returned name to an unsafe join.
    """
    if not name:
        raise IngestionError("Invalid archive member name: empty")
    pure = PurePosixPath(name.replace("\\", "/"))
    if pure.is_absolute() or any(part in {"..", ""} for part in pure.parts):
        raise IngestionError(f"Invalid archive member name: {name!r}")
    base = pure.name
    if not base or base in {".", ".."}:
        raise IngestionError(f"Invalid archive member name: {name!r}")
    return base
