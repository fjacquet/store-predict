"""Playwright-based PDF generation from the /report/print page.

Launches headless Chromium, navigates to the print-optimised NiceGUI page,
waits for ECharts to finish rendering, then exports to PDF bytes.
"""

from __future__ import annotations

from playwright.async_api import async_playwright


async def generate_pdf(token: str, port: int) -> bytes:
    """Navigate to ``/report/print?token=<token>`` and return PDF bytes.

    Args:
        token: One-time print-session token created by :mod:`print_session`.
        port:  The port the NiceGUI application is listening on.

    Returns:
        Raw PDF bytes suitable for passing to ``ui.download()``.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(
            f"http://localhost:{port}/report/print?token={token}",
            wait_until="networkidle",
            timeout=30_000,
        )
        # Give ECharts extra time to finish canvas rendering after network idle
        await page.wait_for_timeout(2000)
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "1.5cm", "right": "1.5cm", "bottom": "1.5cm", "left": "1.5cm"},
        )
        await browser.close()
    return pdf_bytes
