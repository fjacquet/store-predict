"""Dark mode toggle component with persistent user preference."""

from __future__ import annotations

from nicegui import app, ui

from store_predict.i18n import t


def add_dark_mode_toggle() -> None:
    """Add a dark mode toggle switch with auto OS-preference detection.

    On first visit (no stored preference), dark mode follows the browser/OS
    system setting automatically via ``ui.dark_mode().auto()``.  Once the user
    explicitly toggles the switch, their preference is persisted across sessions
    via ``app.storage.user``.
    """
    dark = ui.dark_mode()
    if "dark_mode" not in app.storage.user:
        dark.auto()
    dark.bind_value(app.storage.user, "dark_mode")
    ui.switch(t("layout.dark_mode")).bind_value(app.storage.user, "dark_mode").props("color=white")
