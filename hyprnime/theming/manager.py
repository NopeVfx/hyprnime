"""Applies Light/Dark mode and optional 'custom theme' CSS overlays."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from pathlib import Path
from .build_themes import PALETTES

THEMES_DIR = Path(__file__).parent / "themes"
BASE_CSS = Path(__file__).parent / "style.css"

# id -> (display name, is_dark)
THEMES = {tid: (name, dark) for tid, (name, dark, _pal) in PALETTES.items()}

_COLOR_SCHEME_MAP = {
    "system": Adw.ColorScheme.DEFAULT,
    "light": Adw.ColorScheme.FORCE_LIGHT,
    "dark": Adw.ColorScheme.FORCE_DARK,
}


class ThemeManager:
    def __init__(self):
        self._base_provider = Gtk.CssProvider()
        self._custom_provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if BASE_CSS.exists():
            self._base_provider.load_from_path(str(BASE_CSS))
            Gtk.StyleContext.add_provider_for_display(
                display, self._base_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        Gtk.StyleContext.add_provider_for_display(
            display, self._custom_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

    def apply(self, color_scheme: str, custom_theme: str):
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(_COLOR_SCHEME_MAP.get(color_scheme, Adw.ColorScheme.DEFAULT))

        if custom_theme and custom_theme != "none" and custom_theme in THEMES:
            css_path = THEMES_DIR / f"{custom_theme}.css"
            if css_path.exists():
                self._custom_provider.load_from_path(str(css_path))
                # A custom scheme carries its own light/dark identity;
                # force Adwaita to match so contrast stays correct.
                is_dark = THEMES[custom_theme][1]
                style_manager.set_color_scheme(
                    Adw.ColorScheme.FORCE_DARK if is_dark else Adw.ColorScheme.FORCE_LIGHT
                )
                return
        # "none" -> clear any custom overlay, fall back to plain Adwaita light/dark
        self._custom_provider.load_from_data(b"")

    @staticmethod
    def list_themes():
        """Returns [(id, display_name), ...] sorted for a combo/dropdown."""
        return sorted(THEMES.items(), key=lambda kv: kv[1][0])
