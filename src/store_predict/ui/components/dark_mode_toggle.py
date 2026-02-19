"""Dark mode toggle component with persistent user preference."""

from __future__ import annotations

from nicegui import app, ui


def add_dark_mode_toggle() -> None:
    """Add a dark mode toggle switch bound to user storage.

    The preference persists across pages and browser sessions via
    ``app.storage.user``.
    """
    ui.dark_mode().bind_value(app.storage.user, "dark_mode")
    ui.switch("Dark Mode").bind_value(app.storage.user, "dark_mode").props("color=white")
