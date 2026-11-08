"""client_ready() must report a pruned client so pages stop building on it."""

from __future__ import annotations

import asyncio

from nicegui import Client, ui

from store_predict.ui.layout import client_ready


def test_client_ready_false_after_client_deleted() -> None:
    """A never-connected client pruned by NiceGUI makes connected() return; page must bail out."""

    async def run() -> bool:
        client = Client(ui.page("/_t"))
        with client:
            client.delete()
            return await client_ready()

    assert asyncio.run(run()) is False
