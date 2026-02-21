"""Playwright-based PDF generation from print-optimised pages.

Launches headless Chromium, navigates to a print-optimised NiceGUI page,
waits for rendering to complete, then exports to PDF bytes.
"""

from __future__ import annotations

from playwright.async_api import async_playwright


async def _render_page_to_pdf(url: str, wait_ms: int = 2000) -> bytes:
    """Navigate to *url*, wait for rendering, and return PDF bytes."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(wait_ms)
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "1.5cm", "right": "1.5cm", "bottom": "1.5cm", "left": "1.5cm"},
        )
        await browser.close()
    return pdf_bytes


async def generate_pdf(token: str, port: int) -> bytes:
    """Navigate to ``/report/print?token=<token>`` and return PDF bytes.

    Args:
        token: One-time print-session token created by :mod:`print_session`.
        port:  The port the NiceGUI application is listening on.

    Returns:
        Raw PDF bytes suitable for passing to ``ui.download()``.
    """
    return await _render_page_to_pdf(
        f"http://localhost:{port}/report/print?token={token}",
        wait_ms=2000,
    )


async def generate_layout_pdf(token: str, port: int) -> bytes:
    """Navigate to ``/layout/print?token=<token>`` and return PDF bytes.

    Args:
        token: One-time print-session token created by :mod:`print_session`.
        port:  The port the NiceGUI application is listening on.

    Returns:
        Raw PDF bytes suitable for passing to ``ui.download()``.
    """
    return await _render_page_to_pdf(
        f"http://localhost:{port}/layout/print?token={token}",
        wait_ms=500,
    )
