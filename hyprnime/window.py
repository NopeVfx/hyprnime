import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from . import config
from .theming.manager import ThemeManager
from .views.home import HomeView
from .views.search import SearchView
from .views.detail import DetailView
from .views.settings import SettingsView
from .views.party import PartyView
from .views.downloads import DownloadsView


class HyprnimeWindow(Adw.ApplicationWindow):
    def __init__(self, app, theme_manager: ThemeManager):
        super().__init__(application=app, title="Hyprnime", default_width=1100, default_height=720)
        self.theme_manager = theme_manager
        self.cfg = config.load()

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        split = Adw.NavigationSplitView()
        self.toast_overlay.set_child(split)

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_header = Adw.HeaderBar(show_end_title_buttons=False)
        sidebar_toolbar.add_top_bar(sidebar_header)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        nav_items = [
            ("go-home-symbolic", "Home"),
            ("edit-find-symbolic", "Search"),
            ("system-users-symbolic", "Watch Party"),
            ("folder-download-symbolic", "Downloads"),
            ("emblem-system-symbolic", "Settings"),
        ]
        for icon, label in nav_items:
            row = Adw.ActionRow(title=label)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self.sidebar_list.append(row)
        self.sidebar_list.connect("row-selected", self._on_sidebar_selected)
        sidebar_toolbar.set_content(self.sidebar_list)

        sidebar_page = Adw.NavigationPage(title="Hyprnime", child=sidebar_toolbar)
        split.set_sidebar(sidebar_page)

        self.content_nav = Adw.NavigationView()

        self.stack = Gtk.Stack()
        self.home_view = HomeView(self.open_anime)
        self.search_view = SearchView(self.open_anime)
        self.party_view = PartyView(self.toast_overlay)
        self.downloads_view = DownloadsView(self.toast_overlay)
        self.settings_view = SettingsView(self.theme_manager, self.toast_overlay)

        view_map = [
            ("home", self.home_view),
            ("search", self.search_view),
            ("party", self.party_view),
            ("downloads", self.downloads_view),
            ("settings", self.settings_view),
        ]
        for name, widget in view_map:
            scroller = Gtk.ScrolledWindow()
            scroller.set_child(widget)
            self.stack.add_named(scroller, name)

        content_toolbar = Adw.ToolbarView()
        content_toolbar.add_top_bar(Adw.HeaderBar())
        content_toolbar.set_content(self.stack)

        root_page = Adw.NavigationPage(title="Home", child=content_toolbar)
        self.content_nav.push(root_page)

        content_nav_page = Adw.NavigationPage(title="Hyprnime", child=self.content_nav)
        split.set_content(content_nav_page)

        self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True
        return False

    def _toggle_fullscreen(self):
        # Query the window's actual state (the "fullscreened" GObject
        # property) rather than tracking our own flag, so this stays
        # correct even if something else (the compositor, a WM keybind)
        # changed fullscreen state since we last touched it.
        if self.get_property("fullscreened"):
            self.unfullscreen()
        else:
            self.fullscreen()

    def _on_sidebar_selected(self, _listbox, row):
        if row is None:
            return
        index = row.get_index()
        names = ["home", "search", "party", "downloads", "settings"]
        name = names[index]
        self.stack.set_visible_child_name(name)
        if name == "search":
            self.search_view.focus_entry()
        elif name == "downloads":
            self.downloads_view.refresh()

    def open_anime(self, result):
        detail = DetailView(result, self.toast_overlay)
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        scroller = Gtk.ScrolledWindow()
        scroller.set_child(detail)
        toolbar.set_content(scroller)
        page = Adw.NavigationPage(title=result.title, child=toolbar)
        self.content_nav.push(page)
        return False
