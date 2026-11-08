"""Chunk upload endpoint: reassembly, size cap, token gate, temp-file purge."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from store_predict import chunk_upload as cu


@pytest.fixture(autouse=True)
def _clean() -> None:
    cu._store.clear()
    cu._tokens.clear()


def test_receive_chunk_in_order_with_duplicate_assembles() -> None:
    assert cu._receive_chunk("t", "a.csv", b"hello", 0, 10) is None
    assert cu._receive_chunk("t", "a.csv", b"hello", 0, 10) is None  # retried chunk, same offset
    path = cu._receive_chunk("t", "a.csv", b"world", 5, 10)
    assert path is not None
    assert path.read_bytes() == b"helloworld"
    assert path.name.startswith(cu.TEMP_PREFIX)
    path.unlink()


def test_receive_chunk_rejects_more_than_cap() -> None:
    with pytest.raises(ValueError, match="size limit"):
        cu._receive_chunk("t", "a.csv", b"x" * (cu.MAX_UPLOAD_BYTES + 1), 0, cu.MAX_UPLOAD_BYTES + 1)
    assert not cu._store


def _client() -> TestClient:
    async def endpoint(request):  # type: ignore[no-untyped-def]
        return await cu._handle_chunk(request, request.path_params["token"])

    return TestClient(Starlette(routes=[Route("/api/upload/{token}", endpoint, methods=["POST"])]))


def test_unknown_token_is_rejected() -> None:
    r = _client().post("/api/upload/nope", files={"f": ("a.csv", b"x")})
    assert r.status_code == 403


def test_declared_total_over_cap_is_rejected() -> None:
    cu.register_token("ok")
    big = cu.MAX_UPLOAD_BYTES + 1
    r = _client().post(
        "/api/upload/ok",
        files={"f": ("a.csv", b"x")},
        headers={"Content-Range": f"bytes 0-0/{big}"},
    )
    assert r.status_code == 413
    assert not cu._store


def test_purge_removes_only_old_prefixed_files() -> None:
    old = Path(tempfile.mkstemp(prefix=cu.TEMP_PREFIX)[1])
    new = Path(tempfile.mkstemp(prefix=cu.TEMP_PREFIX)[1])
    other = Path(tempfile.mkstemp(prefix="unrelated_")[1])
    os.utime(old, (time.time() - 7 * 3600,) * 2)
    cu.purge_stale_temp_files()
    assert not old.exists()
    assert new.exists()
    assert other.exists()
    new.unlink()
    other.unlink()
