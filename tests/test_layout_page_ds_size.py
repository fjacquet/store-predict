"""Custom datastore-size control: TiB→MiB conversion.

The Max DS capacity control is an editable TB value (plus preset shortcuts), so
arbitrary, non-power-of-two sizes must convert correctly to the MiB the layout
engine consumes.
"""

from __future__ import annotations

from store_predict.ui.pages.layout_page import _tib_to_mib


def test_preset_sizes_match_legacy_mib() -> None:
    # Same values the old fixed dropdown produced.
    assert _tib_to_mib(2) == 2 * 1024 * 1024
    assert _tib_to_mib(4) == 4 * 1024 * 1024
    assert _tib_to_mib(64) == 64 * 1024 * 1024


def test_custom_non_preset_sizes() -> None:
    assert _tib_to_mib(10) == 10 * 1024 * 1024
    assert _tib_to_mib(3) == 3 * 1024 * 1024


def test_fractional_rounds_to_whole_mib() -> None:
    assert _tib_to_mib(1.5) == round(1.5 * 1024 * 1024)
