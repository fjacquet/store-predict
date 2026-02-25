"""Shared font registration for ReportLab and matplotlib PDF rendering.

Imported by both pdf_report.py and pdf_charts.py to avoid circular imports.
"""

from __future__ import annotations

import os
from pathlib import Path

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VERA_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")

#: Absolute path to the bundled Open Sans Light TTF (may not exist in test envs).
FONT_PATH_LIGHT = _DATA_DIR / "OpenSansLight.ttf"
FONT_PATH_BOLD = _DATA_DIR / "OpenSansSemiBold.ttf"


def _register_fonts() -> tuple[str, str]:
    """Register Open Sans Light/SemiBold; fall back to Vera if not bundled."""
    if FONT_PATH_LIGHT.exists() and FONT_PATH_BOLD.exists():
        pdfmetrics.registerFont(TTFont("AppFont", str(FONT_PATH_LIGHT)))
        pdfmetrics.registerFont(TTFont("AppFontBd", str(FONT_PATH_BOLD)))
        return "AppFont", "AppFontBd"
    pdfmetrics.registerFont(TTFont("AppFont", os.path.join(_VERA_DIR, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("AppFontBd", os.path.join(_VERA_DIR, "VeraBd.ttf")))
    return "AppFont", "AppFontBd"


FONT_REGULAR, FONT_BOLD = _register_fonts()
