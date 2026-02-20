"""i18n package: t() helper and configuration for python-i18n."""

from __future__ import annotations

from pathlib import Path

import i18n

_LOCALES_DIR = Path(__file__).parent / "locales"

# Configure once at import time — settings are idempotent globals
i18n.set("load_path", [str(_LOCALES_DIR)])
i18n.set("fallback", "en")
i18n.set("filename_format", "{locale}.{format}")
i18n.set("file_format", "yaml")
i18n.set("skip_locale_root_data", True)  # keys NOT prefixed with locale name in YAML


def t(key: str, **kwargs: object) -> str:
    """Return translated string for the current tab's locale.

    Reads locale from app.storage.tab on every call (tab-scoped, not global).
    Sets the python-i18n process-global locale immediately before the lookup —
    safe because NiceGUI's async event loop is single-threaded: no other coroutine
    can interleave within one synchronous t() call.

    Falls back to English if locale is unset or missing key in French.
    """
    from store_predict.i18n.locale import get_locale  # lazy to avoid circular import

    locale = get_locale()
    i18n.set("locale", locale)
    return str(i18n.t(key, **kwargs))


__all__ = ["t"]
