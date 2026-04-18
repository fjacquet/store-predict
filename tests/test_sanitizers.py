"""Unit tests for store_predict._sanitizers."""

from __future__ import annotations

from store_predict._sanitizers import escape_xml, safe_excel_cell


class TestEscapeXml:
    def test_escapes_ampersand(self) -> None:
        assert escape_xml("A & B") == "A &amp; B"

    def test_escapes_angle_brackets(self) -> None:
        assert escape_xml("<b>evil</b>") == "&lt;b&gt;evil&lt;/b&gt;"

    def test_passes_safe_text(self) -> None:
        assert escape_xml("server-01") == "server-01"

    def test_coerces_non_string(self) -> None:
        assert escape_xml(42) == "42"
        assert escape_xml(None) == "None"

    def test_roundtrips_empty(self) -> None:
        assert escape_xml("") == ""


class TestSafeExcelCell:
    def test_neutralizes_equals(self) -> None:
        assert safe_excel_cell("=cmd|'/c calc'!A1") == "'=cmd|'/c calc'!A1"

    def test_neutralizes_plus(self) -> None:
        assert safe_excel_cell("+SUM(A1:A3)") == "'+SUM(A1:A3)"

    def test_neutralizes_minus(self) -> None:
        assert safe_excel_cell("-1+1") == "'-1+1"

    def test_neutralizes_at(self) -> None:
        assert safe_excel_cell("@IMPORT") == "'@IMPORT"

    def test_neutralizes_tab_and_cr(self) -> None:
        assert safe_excel_cell("\tinjected") == "'\tinjected"
        assert safe_excel_cell("\rinjected") == "'\rinjected"

    def test_passes_safe_string(self) -> None:
        assert safe_excel_cell("server-01") == "server-01"

    def test_passes_numbers_unchanged(self) -> None:
        assert safe_excel_cell(42) == 42
        assert safe_excel_cell(3.14) == 3.14

    def test_passes_none(self) -> None:
        assert safe_excel_cell(None) is None

    def test_passes_bool(self) -> None:
        # bool is a subclass of int — must not be wrapped.
        assert safe_excel_cell(True) is True
        assert safe_excel_cell(False) is False

    def test_passes_empty_string(self) -> None:
        assert safe_excel_cell("") == ""
