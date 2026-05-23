"""Accessibility regression tests for the theme (UI#5).

Guards three fixes: WCAG-AA contrast on the muted chip, the reduced-motion
media query, and removal of the redundant workflow step bar.
"""

from __future__ import annotations

from store_predict.ui.theme import _STYLESHEET


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.x relative-luminance contrast ratio between two hex colors."""

    def _lum(hexs: str) -> float:
        h = hexs.lstrip("#")
        channels = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
        linear = [(c / 12.92) if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    hi, lo = sorted((_lum(fg_hex), _lum(bg_hex)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_muted_strong_token_passes_aa_on_line() -> None:
    # .sp-chip-muted uses --sp-muted-strong (#556070, light) on --sp-line (#E2E8F0).
    # Small text must clear WCAG AA (>= 4.5:1); the previous --sp-muted (#64748B) was 3.86.
    assert _contrast_ratio("#556070", "#E2E8F0") >= 4.5


def test_chip_muted_uses_strong_token() -> None:
    assert "--sp-muted-strong" in _STYLESHEET
    # the muted chip's text color must reference the AA-safe token, not bare --sp-muted
    assert "color:var(--sp-muted-strong)" in _STYLESHEET


def test_reduced_motion_media_query_present() -> None:
    assert "prefers-reduced-motion" in _STYLESHEET


def test_step_bar_removed() -> None:
    # The numbered workflow step bar duplicated the header nav and was removed.
    assert "sp-step" not in _STYLESHEET
