import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from . import config
from .theming.manager import ThemeManager
from .window import HyprnimeWindow

APP_ID = "dev.hyprnime.Hyprnime"


class HyprnimeApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.theme_manager = None

    def do_activate(self):
        cfg = config.load()
        if self.theme_manager is None:
            self.theme_manager = ThemeManager()
        self.theme_manager.apply(cfg.get("color_scheme", "system"), cfg.get("custom_theme", "none"))

        win = self.props.active_window
        if not win:
            win = HyprnimeWindow(self, self.theme_manager)
        win.present()


def main():
    app = HyprnimeApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
