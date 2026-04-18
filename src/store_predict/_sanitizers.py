"""Small, reusable sanitizers for user-controlled content that crosses into
mini-languages (ReportLab XML, spreadsheet formulas). Keep this module free of
third-party imports so every export surface can reach for it cheaply.
"""

from __future__ import annotations

from xml.sax.saxutils import escape as _xml_escape

__all__ = ["escape_xml", "safe_excel_cell"]

_FORMULA_LEADS: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def escape_xml(value: object) -> str:
    """Escape a value for ReportLab Paragraph or any mini-XML sink.

    ReportLab's Platypus parses a tiny HTML-like markup inside ``Paragraph``
    strings (``<b>``, ``<i>``, ``<link>``, ...). An unescaped ``&`` or ``<``
    in user-supplied VM names either crashes the renderer or injects markup.
    """
    return _xml_escape(str(value))


def safe_excel_cell(value: object) -> object:
    """Neutralize Excel/CSV formula injection (CWE-1236).

    Strings beginning with ``=``, ``+``, ``-``, ``@``, ``\\t`` or ``\\r`` are
    prefixed with a single quote so spreadsheet apps treat them as literal
    text rather than formulas. Non-strings (ints, floats, bools, None) pass
    through unchanged so numeric cells stay typed.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_LEADS):
        return "'" + value
    return value
