import getpass
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from .. import config
from ..backend import anilist, party_directory as pdir, syncplay_backend as sp
from .widgets import load_texture_async


class PartyView(Gtk.Box):
    def __init__(self, toast_overlay: Adw.ToastOverlay):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.toast_overlay = toast_overlay
        self.cfg = config.load()
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(18)
        self.set_margin_end(18)

        self.selected_anime: anilist.AnimeResult | None = None
        self.active_party: pdir.PartyListing | None = None
        self.active_token: str | None = None
        self._heartbeat_source = None

        title = Gtk.Label(label="Watch Party", xalign=0)
        title.add_css_class("anicli-hero-title")
        self.append(title)

        subtitle = Gtk.Label(
            xalign=0, wrap=True,
            label=("Host a party with a name, a background, and an anime -- friends find it by "
                   "searching that name. Playback stays in sync via Syncplay; each person streams "
                   "their own copy through ani-cli."),
        )
        subtitle.add_css_class("dim-label")
        self.append(subtitle)

        # Find/Host switch ---------------------------------------------------
        switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switcher_box.add_css_class("linked")
        self.find_btn = Gtk.ToggleButton(label="Find a Party")
        self.host_btn = Gtk.ToggleButton(label="Host a Party")
        self.find_btn.set_active(True)
        self.find_btn.connect("toggled", self._on_switch, "find")
        self.host_btn.connect("toggled", self._on_switch, "host")
        switcher_box.append(self.find_btn)
        switcher_box.append(self.host_btn)
        self.append(switcher_box)

        self.pages = Gtk.Stack()
        self.append(self.pages)

        self.pages.add_named(self._build_find_page(), "find")
        self.pages.add_named(self._build_host_page(), "host")
        self.pages.set_visible_child_name("find")

    def _on_switch(self, button, name):
        if button.get_active():
            self.pages.set_visible_child_name(name)

    def _default_username(self) -> str:
        return self.cfg.get("party_username") or getpass.getuser() or "Anonymous"

    # ================================================================== FIND
    def _build_find_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)

        self.find_entry = Gtk.SearchEntry(placeholder_text="Search party name…")
        self.find_entry.connect("activate", self._on_find)
        box.append(self.find_entry)

        self.find_status = Gtk.Label(xalign=0)
        self.find_status.add_css_class("anicli-empty-state")
        box.append(self.find_status)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        self.results_list = Gtk.ListBox()
        self.results_list.add_css_class("boxed-list")
        self.results_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.set_child(self.results_list)
        box.append(scroller)

        if not self.cfg.get("directory_server"):
            self.find_status.set_label(
                "No Party Directory server configured yet -- set one in Settings > Watch Party."
            )
        else:
            self.find_status.set_label("Search for a party name to join.")

        return box

    def _on_find(self, entry):
        server = self.cfg.get("directory_server", "")
        query = entry.get_text().strip()
        for child in list(self.results_list):
            self.results_list.remove(child)

        def worker():
            try:
                results = pdir.search_parties(server, query)
                GLib.idle_add(self._populate_results, results, None)
            except pdir.DirectoryError as exc:
                GLib.idle_add(self._populate_results, [], str(exc))

        threading.Thread(target=worker, daemon=True).start()
        self.find_status.set_label("Searching…")

    def _populate_results(self, results, error):
        if error:
            self.find_status.set_label(error)
            return False
        if not results:
            self.find_status.set_label("No open parties match that name.")
            return False
        self.find_status.set_label(f"{len(results)} part{'y' if len(results)==1 else 'ies'} found")
        for listing in results:
            self.results_list.append(self._build_party_row(listing))
        return False

    def _build_party_row(self, listing: pdir.PartyListing) -> Gtk.Widget:
        row = Adw.ActionRow(title=listing.name)
        subtitle_bits = [listing.anime_title]
        if listing.episode:
            subtitle_bits.append(f"Ep {listing.episode}")
        subtitle_bits.append("Dub" if listing.dub else "Sub")
        subtitle_bits.append(f"hosted by {listing.host}")
        subtitle_bits.append(f"{listing.member_count} reported watching")
        row.set_subtitle("  ·  ".join(subtitle_bits))

        if listing.background_url:
            pic = Gtk.Picture()
            pic.set_size_request(64, 64)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            row.add_prefix(pic)
            load_texture_async(listing.background_url, lambda t, p=pic: (p.set_paintable(t), False)[1])

        join_btn = Gtk.Button(label="Join")
        join_btn.add_css_class("suggested-action")
        join_btn.set_valign(Gtk.Align.CENTER)
        join_btn.connect("clicked", lambda _b, l=listing: self._join_party(l))
        row.add_suffix(join_btn)
        return row

    def _join_party(self, listing: pdir.PartyListing):
        self._toast(f"Resolving your own stream for {listing.anime_title}…")

        def worker():
            try:
                episode = int(listing.episode) if listing.episode else 1
                stream_url = sp.resolve_stream_url(
                    listing.anime_title, episode, dub=listing.dub, quality=listing.quality or "best",
                )
                server = listing.syncplay_server or self.cfg.get("syncplay_server", sp.DEFAULT_SYNCPLAY_SERVER)
                session = sp.PartySession(
                    room=listing.name, username=self._default_username(),
                    stream_url=stream_url, server=server, player=self.cfg.get("player", "mpv"),
                )
                sp.launch_syncplay(session)
                GLib.idle_add(self._toast, f"Joined “{listing.name}” -- Syncplay + mpv opening now.")
            except (sp.StreamResolveError, sp.SyncplayNotFound) as exc:
                GLib.idle_add(self._toast, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    # ================================================================== HOST
    def _build_host_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(10)

        group = Adw.PreferencesGroup()

        self.party_name_row = Adw.EntryRow(title="Party name")
        group.add(self.party_name_row)

        self.anime_search_row = Adw.EntryRow(title="Anime title")
        self.anime_search_row.connect("entry-activated", self._on_anime_search)
        group.add(self.anime_search_row)

        box.append(group)

        self.anime_results = Gtk.ListBox()
        self.anime_results.add_css_class("boxed-list")
        self.anime_results.set_selection_mode(Gtk.SelectionMode.NONE)
        box.append(self.anime_results)

        # Preview of the selected anime / background
        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.bg_preview = Gtk.Picture()
        self.bg_preview.set_size_request(160, 90)
        self.bg_preview.set_content_fit(Gtk.ContentFit.COVER)
        self.bg_preview.add_css_class("anicli-cover")
        preview_box.append(self.bg_preview)
        self.selected_label = Gtk.Label(label="No anime selected yet.", xalign=0, wrap=True)
        self.selected_label.set_hexpand(True)
        preview_box.append(self.selected_label)
        box.append(preview_box)

        self.bg_url_row = Adw.EntryRow(title="Background image URL (optional override)")
        group2 = Adw.PreferencesGroup()
        group2.add(self.bg_url_row)
        box.append(group2)

        # Episode / mode / quality controls
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.episode_spin = Gtk.SpinButton.new_with_range(1, 9999, 1)
        self.episode_spin.set_value(1)
        controls.append(Gtk.Label(label="Episode:"))
        controls.append(self.episode_spin)

        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        mode_box.add_css_class("linked")
        self._party_mode = self.cfg.get("default_mode", "sub")
        self.p_sub_btn = Gtk.ToggleButton(label="Sub")
        self.p_dub_btn = Gtk.ToggleButton(label="Dub")
        self.p_sub_btn.set_active(self._party_mode != "dub")
        self.p_dub_btn.set_active(self._party_mode == "dub")
        self.p_sub_btn.connect("toggled", self._on_party_mode, "sub")
        self.p_dub_btn.connect("toggled", self._on_party_mode, "dub")
        mode_box.append(self.p_sub_btn)
        mode_box.append(self.p_dub_btn)
        controls.append(mode_box)

        self.quality_dropdown = Gtk.DropDown.new_from_strings(["best", "1080", "720", "480", "360", "worst"])
        controls.append(self.quality_dropdown)
        box.append(controls)

        self.start_btn = Gtk.Button(label="Start Party")
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.add_css_class("pill")
        self.start_btn.connect("clicked", self._on_start_party)
        box.append(self.start_btn)

        self.host_status = Gtk.Label(xalign=0, wrap=True)
        self.host_status.add_css_class("anicli-empty-state")
        box.append(self.host_status)

        if not self.cfg.get("directory_server"):
            self.host_status.set_label(
                "No Party Directory server configured -- set one in Settings > Watch Party "
                "before hosting so others can find this party by name."
            )

        self.active_party_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.active_party_box.set_visible(False)
        box.append(self.active_party_box)

        return box

    def _on_party_mode(self, button, name):
        if not button.get_active():
            return
        self._party_mode = name
        if name == "sub":
            self.p_dub_btn.set_active(False)
        else:
            self.p_sub_btn.set_active(False)

    def _on_anime_search(self, entry):
        query = entry.get_text().strip()
        if not query:
            return
        for child in list(self.anime_results):
            self.anime_results.remove(child)

        def worker():
            try:
                results = anilist.search(query, per_page=8)
                GLib.idle_add(self._populate_anime_results, results, None)
            except anilist.AniListError as exc:
                GLib.idle_add(self._populate_anime_results, [], str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_anime_results(self, results, error):
        if error:
            row = Adw.ActionRow(title=error)
            self.anime_results.append(row)
            return False
        if not results:
            row = Adw.ActionRow(title="No matches found")
            self.anime_results.append(row)
            return False
        for res in results:
            subtitle = f"{res.episodes or '?'} episodes" if res.episodes else "Episode count unknown"
            row = Adw.ActionRow(title=res.title, subtitle=subtitle, activatable=True)
            row.connect("activated", lambda _r, r=res: self._select_anime(r))
            self.anime_results.append(row)
        return False

    def _select_anime(self, result: anilist.AnimeResult):
        self.selected_anime = result
        self.selected_label.set_label(f"Selected: {result.title}")
        bg = result.banner_url or result.cover_url
        if bg:
            load_texture_async(bg, lambda t: (self.bg_preview.set_paintable(t), False)[1])
        if result.episodes:
            self.episode_spin.set_range(1, result.episodes)

    def _on_start_party(self, _button):
        name = self.party_name_row.get_text().strip()
        if not name:
            self.host_status.set_label("Give your party a name first.")
            return
        if not self.selected_anime:
            self.host_status.set_label("Search for and select an anime first.")
            return

        directory_server = self.cfg.get("directory_server", "")
        syncplay_server = self.cfg.get("syncplay_server", sp.DEFAULT_SYNCPLAY_SERVER)
        episode = int(self.episode_spin.get_value())
        dub = self._party_mode == "dub"
        quality = ["best", "1080", "720", "480", "360", "worst"][self.quality_dropdown.get_selected()]
        background_url = self.bg_url_row.get_text().strip() or self.selected_anime.banner_url or self.selected_anime.cover_url
        anime_title = self.selected_anime.title
        username = self._default_username()

        self.start_btn.set_sensitive(False)
        self.host_status.set_label("Resolving your stream and registering the party…")

        def worker():
            try:
                stream_url = sp.resolve_stream_url(anime_title, episode, dub=dub, quality=quality)
                listing, token = None, None
                if directory_server:
                    listing, token = pdir.create_party(
                        directory_server, name, anime_title, username,
                        episode=episode, dub=dub, quality=quality,
                        background_url=background_url, syncplay_server=syncplay_server,
                    )
                session = sp.PartySession(
                    room=name, username=username, stream_url=stream_url,
                    server=syncplay_server, player=self.cfg.get("player", "mpv"),
                )
                sp.launch_syncplay(session)
                GLib.idle_add(self._party_started, listing, token, name)
            except (sp.StreamResolveError, sp.SyncplayNotFound, pdir.DirectoryError) as exc:
                GLib.idle_add(self._party_start_failed, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _party_start_failed(self, message):
        self.start_btn.set_sensitive(True)
        self.host_status.set_label(message)
        return False

    def _party_started(self, listing, token, name):
        self.start_btn.set_sensitive(True)
        self.active_party = listing
        self.active_token = token
        if listing:
            self.host_status.set_label(
                f"Party “{name}” is live and searchable by name. Syncplay + mpv are opening now."
            )
            self._schedule_heartbeat()
        else:
            self.host_status.set_label(
                f"Party “{name}” started (not registered anywhere findable -- no Directory "
                f"server is configured, so share the room name directly instead)."
            )
        self._show_active_party_controls(name)
        return False

    def _show_active_party_controls(self, name):
        for child in list(self.active_party_box):
            self.active_party_box.remove(child)
        self.active_party_box.set_visible(True)
        label = Gtk.Label(label=f"Hosting: {name}", xalign=0)
        label.add_css_class("anicli-section-title")
        self.active_party_box.append(label)
        close_btn = Gtk.Button(label="Close Party")
        close_btn.add_css_class("destructive-action")
        close_btn.set_halign(Gtk.Align.START)
        close_btn.connect("clicked", self._on_close_party)
        self.active_party_box.append(close_btn)

    def _schedule_heartbeat(self):
        if self._heartbeat_source:
            GLib.source_remove(self._heartbeat_source)
        self._heartbeat_source = GLib.timeout_add_seconds(120, self._send_heartbeat)

    def _send_heartbeat(self):
        if not self.active_party or not self.active_token:
            return False
        server = self.cfg.get("directory_server", "")

        def worker():
            try:
                pdir.heartbeat(server, self.active_party.id, self.active_token)
            except pdir.DirectoryError:
                pass

        threading.Thread(target=worker, daemon=True).start()
        return True  # keep repeating

    def _on_close_party(self, _button):
        if self._heartbeat_source:
            GLib.source_remove(self._heartbeat_source)
            self._heartbeat_source = None
        if self.active_party and self.active_token:
            server = self.cfg.get("directory_server", "")

            def worker():
                try:
                    pdir.close_party(server, self.active_party.id, self.active_token)
                except pdir.DirectoryError:
                    pass

            threading.Thread(target=worker, daemon=True).start()
        self.active_party = None
        self.active_token = None
        self.active_party_box.set_visible(False)
        self.host_status.set_label("Party closed. (Syncplay/mpv keep running until you close them.)")

    def _toast(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=3))
        return False
