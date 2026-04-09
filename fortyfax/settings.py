"""Application settings persistence."""

import json
import logging
from pathlib import Path

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw

log = logging.getLogger(__name__)

_SETTINGS_FILE = Path.home() / ".config" / "fortyfax" / "settings.json"

# Maps stored string -> Adw.ColorScheme
THEME_CHOICES = {
    "system": Adw.ColorScheme.DEFAULT,
    "light": Adw.ColorScheme.FORCE_LIGHT,
    "dark": Adw.ColorScheme.FORCE_DARK,
}

_DEFAULTS = {
    "theme": "system",
    "notifications": True,
    "sso_browser": "auto",  # "auto", "chrome", "edge", "xdg-open"
}


def _load_raw() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Impossibile leggere le impostazioni: %s", e)
    return {}


def _save_raw(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(_SETTINGS_FILE)


def get(key: str):
    data = _load_raw()
    return data.get(key, _DEFAULTS.get(key))


def set(key: str, value) -> None:
    data = _load_raw()
    data[key] = value
    _save_raw(data)


def get_color_scheme() -> Adw.ColorScheme:
    theme = get("theme")
    return THEME_CHOICES.get(theme, Adw.ColorScheme.DEFAULT)


def apply_theme() -> None:
    """Apply the stored theme preference to the Adw.StyleManager."""
    style_mgr = Adw.StyleManager.get_default()
    style_mgr.set_color_scheme(get_color_scheme())
