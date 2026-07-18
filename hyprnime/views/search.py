import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..backend import anilist
from ..backend.anilist import AniListError
from .widgets import AnimeCard


class SearchView(Gtk.Box):
    def __init__(self, on_open_anime):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.on_open_anime = on_open_anime
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(18)
        self.set_margin_end(18)

        self.entry = Gtk.SearchEntry(placeholder_text="Search anime…")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self._on_search)
        self.append(self.entry)

        self.spinner = Gtk.Spinner()
        self.append(self.spinner)

        self.status = Gtk.Label(label="Type a title and press Enter.")
        self.status.add_css_class("anicli-empty-state")
        self.append(self.status)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(8)
        self.flow.set_row_spacing(16)
        self.flow.set_column_spacing(16)
        scroller.set_child(self.flow)
        self.append(scroller)

    def focus_entry(self):
        self.entry.grab_focus()

    def _on_search(self, entry):
        query = entry.get_text().strip()
        if not query:
            return
        for child in list(self.flow):
            self.flow.remove(child)
        self.status.set_label(f"Searching for “{query}”…")
        self.spinner.set_spinning(True)

        def worker():
            try:
                results = anilist.search(query, per_page=30)
                GLib.idle_add(self._populate, results, query, None)
            except AniListError as exc:
                GLib.idle_add(self._populate, [], query, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, results, query, error):
        self.spinner.set_spinning(False)
        if error:
            self.status.set_label(error)
            return False
        if not results:
            self.status.set_label(f"No results for “{query}”.")
            return False
        self.status.set_label(f"{len(results)} result(s) for “{query}”")
        for res in results:
            self.flow.append(AnimeCard(res, self.on_open_anime))
        return False
