import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..backend import anilist, history
from ..backend.anilist import AniListError
from .widgets import AnimeCard


class HomeView(Gtk.Box):
    def __init__(self, on_open_anime):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.on_open_anime = on_open_anime
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(18)
        self.set_margin_end(18)

        # --- Continue Watching ---------------------------------------
        self.continue_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cont_label = Gtk.Label(label="Continue Watching", xalign=0)
        cont_label.add_css_class("anicli-section-title")
        self.continue_section.append(cont_label)

        self.continue_scroller = Gtk.ScrolledWindow()
        self.continue_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.continue_scroller.set_min_content_height(70)
        self.continue_list = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.continue_scroller.set_child(self.continue_list)
        self.continue_section.append(self.continue_scroller)
        self.append(self.continue_section)
        self._load_history()

        # --- Trending ---------------------------------------------------
        trend_label = Gtk.Label(label="Trending Now", xalign=0)
        trend_label.add_css_class("anicli-section-title")
        self.append(trend_label)

        self.spinner = Gtk.Spinner(spinning=True)
        self.spinner.set_margin_top(24)
        self.append(self.spinner)

        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(8)
        self.flow.set_row_spacing(16)
        self.flow.set_column_spacing(16)
        self.flow.set_homogeneous(False)
        self.flow.set_visible(False)
        self.append(self.flow)

        self._load_trending()

    def _load_history(self):
        entries = history.read_history(limit=10)
        if not entries:
            empty = Gtk.Label(label="Nothing watched yet -- search for something!", xalign=0)
            empty.add_css_class("anicli-empty-state")
            self.continue_list.append(empty)
            return
        for entry in entries:
            chip = Gtk.Button(label=f"{entry.title}  ·  Ep {entry.episode}")
            chip.add_css_class("pill")
            chip.connect("clicked", lambda _b, t=entry.title: self._resume(t))
            self.continue_list.append(chip)

    def _resume(self, title):
        # Resolve full metadata via AniList so the detail page has cover art etc.
        def worker():
            try:
                results = anilist.search(title, per_page=1)
            except AniListError:
                return  # a failed resume just does nothing; the error is already
                        # visible from the Trending/Search sections on this page
            if results:
                GLib.idle_add(self.on_open_anime, results[0])
        threading.Thread(target=worker, daemon=True).start()

    def _load_trending(self):
        def worker():
            try:
                results = anilist.trending(per_page=24)
                GLib.idle_add(self._populate_trending, results, None)
            except AniListError as exc:
                GLib.idle_add(self._populate_trending, [], str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def _populate_trending(self, results, error):
        self.spinner.set_visible(False)
        self.spinner.set_spinning(False)
        if error:
            empty = Gtk.Label(label=error, xalign=0, wrap=True)
            empty.add_css_class("anicli-empty-state")
            self.append(empty)
            return False
        if not results:
            empty = Gtk.Label(label="AniList returned no trending results right now.", xalign=0)
            empty.add_css_class("anicli-empty-state")
            self.append(empty)
            return False
        for res in results:
            card = AnimeCard(res, self.on_open_anime)
            self.flow.append(card)
        self.flow.set_visible(True)
        return False
