"""Chunked file upload endpoint for corporate proxy compatibility.

Corporate proxies often time out large HTTP requests mid-transfer.
This module provides a /api/upload/{token} endpoint that accepts
Quasar QUploader chunks (2 MB each) and reassembles them server-side.
When all chunks for a token+filename pair are received, the assembled
file info is appended to a per-token queue in app.storage.general so the
upload page timer can pick it up sequentially.
"""

from __future__ import annotations

import logging
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from starlette.datastructures import UploadFile
from starlette.requests import Request  # noqa: TC002 — must be runtime import for FastAPI param resolution
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_STALE_SECONDS = 300  # purge incomplete uploads after 5 minutes


@dataclass
class _UploadEntry:
    chunks: dict[int, bytes] = field(default_factory=dict)
    total_size: int = 0
    filename: str = ""
    created: float = field(default_factory=time.monotonic)


_store: dict[str, _UploadEntry] = {}
_lock = Lock()


def _purge_stale() -> None:
    """Remove entries older than _STALE_SECONDS. Must be called with _lock held."""
    cutoff = time.monotonic() - _STALE_SECONDS
    stale = [k for k, v in _store.items() if v.created < cutoff]
    for k in stale:
        del _store[k]
        logger.debug("Purged stale upload entry %s", k)


def _receive_chunk(token: str, filename: str, data: bytes, start: int, total_size: int) -> Path | None:
    """Store one chunk; return assembled temp-file Path when all bytes received.

    Assembly is triggered when *either*:
    - ``received >= total_size`` (normal case), or
    - the highest byte position written reaches ``total_size - 1``
      (guards against an off-by-one in Quasar's Content-Range total).
    """
    store_key = f"{token}:{filename}"
    with _lock:
        _purge_stale()
        if store_key not in _store:
            _store[store_key] = _UploadEntry(total_size=total_size, filename=filename)
        entry = _store[store_key]
        entry.chunks[start] = data
        received = sum(len(c) for c in entry.chunks.values())
        max_end = max(s + len(c) for s, c in entry.chunks.items())
        # Assemble when all bytes received OR last chunk reaches the declared end.
        if received < total_size and max_end < total_size:
            logger.debug(
                "Chunk stored, waiting: token=%s file=%s received=%d max_end=%d total=%d",
                token,
                filename,
                received,
                max_end,
                total_size,
            )
            return None
        assembled = b"".join(v for _, v in sorted(entry.chunks.items()))
        del _store[store_key]

    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(assembled)
        logger.info("Upload assembled: token=%s file=%s size=%d", token, filename, total_size)
        return Path(f.name)


async def _handle_chunk(request: Request, token: str) -> JSONResponse:
    """Receive a chunk (or complete file) and enqueue completed uploads."""
    try:
        form = await request.form()
        upload_file: UploadFile | None = next(
            (v for _, v in form.multi_items() if isinstance(v, UploadFile)),
            None,
        )
        if upload_file is None:
            return JSONResponse({"error": "no file in form"}, status_code=400)

        filename: str = upload_file.filename or "upload.bin"
        data: bytes = await upload_file.read()

        content_range = request.headers.get("Content-Range", "")
        if content_range:
            # Format: "bytes start-end/total"
            _, range_info = content_range.split(" ", 1)
            range_part, total_str = range_info.split("/")
            start = int(range_part.split("-")[0])
            total_size = int(total_str)
        else:
            start = 0
            total_size = len(data)

        logger.debug(
            "Chunk received: token=%s file=%s start=%d total=%d data_len=%d range=%r",
            token,
            filename,
            start,
            total_size,
            len(data),
            content_range,
        )
        assembled = _receive_chunk(token, filename, data, start, total_size)
        if assembled is not None:
            from nicegui import app

            queue_key = f"upload_queue_{token}"
            queue: list[dict[str, str]] = app.storage.general.get(queue_key, [])
            queue.append({"path": str(assembled), "filename": filename})
            app.storage.general[queue_key] = queue
            logger.info("Upload queued: token=%s file=%s path=%s", token, filename, assembled)

        return JSONResponse({"status": "ok"})

    except Exception:
        logger.exception("Error handling upload chunk for token %s", token)
        return JSONResponse({"error": "upload failed"}, status_code=500)


def register_routes() -> None:
    """Register the chunked upload endpoint with the NiceGUI/FastAPI app."""
    from nicegui import app

    @app.post("/api/upload/{token}")
    async def _upload_chunk(token: str, request: Request) -> JSONResponse:
        return await _handle_chunk(request, token)

    _ = _upload_chunk  # registered via decorator; suppress unused-variable lints
