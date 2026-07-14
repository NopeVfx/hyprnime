import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from .. import config
from ..backend import anicli, anilist, downloads as dl_backend
from .widgets import load_texture_async

QUALITIES = ["best", "1080", "720", "480", "360", "worst"]


class DetailView(Gtk.Box):
    def __init__(self, result: "anilist.AnimeResult", toast_overlay: Adw.ToastOverlay):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.result = result
        self.toast_overlay = toast_overlay
        self.cfg = config.load()
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(18)
        self.set_margin_end(18)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        self.cover = Gtk.Picture()
        self.cover.set_content_fit(Gtk.ContentFit.COVER)
        self.cover.set_size_request(200, 280)
        self.cover.add_css_class("anicli-cover")
        header.append(self.cover)
        load_texture_async(result.cover_url, lambda t: (self.cover.set_paintable(t), False)[1])

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info.set_hexpand(True)

        title = Gtk.Label(label=result.title, xalign=0, wrap=True)
        title.add_css_class("anicli-hero-title")
        info.append(title)

        meta_bits = []
        if result.format:
            meta_bits.append(result.format.replace("_", " ").title())
        if result.episodes:
            meta_bits.append(f"{result.episodes} episodes")
        if result.status:
            meta_bits.append(result.status.replace("_", " ").title())
        if result.score:
            meta_bits.append(f"★ {result.score / 10:.1f}/10")
        meta = Gtk.Label(label="  ·  ".join(meta_bits), xalign=0)
        meta.add_css_class("dim-label")
        info.append(meta)

        if result.genres:
            genres = Gtk.Label(label=", ".join(result.genres[:5]), xalign=0)
            genres.add_css_class("anicli-subtitle")
            info.append(genres)

        desc = Gtk.Label(label=result.description or "No synopsis available.", xalign=0, wrap=True)
        desc.set_lines(6)
        desc.set_ellipsize(3)
        desc.set_margin_top(6)
        info.append(desc)

        header.append(info)
        self.append(header)

        # --- Playback controls -------------------------------------------
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_margin_top(10)

        # Segmented Sub/Dub control -- plain linked ToggleButtons so this
        # works on any libadwaita version (Adw.ToggleGroup needs 1.7+).
        self._mode = self.cfg.get("default_mode", "sub")
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        mode_box.add_css_class("linked")
        self.sub_btn = Gtk.ToggleButton(label="Sub")
        self.dub_btn = Gtk.ToggleButton(label="Dub")
        self.sub_btn.set_active(self._mode != "dub")
        self.dub_btn.set_active(self._mode == "dub")
        self.sub_btn.connect("toggled", self._on_mode_toggled, "sub")
        self.dub_btn.connect("toggled", self._on_mode_toggled, "dub")
        mode_box.append(self.sub_btn)
        mode_box.append(self.dub_btn)
        controls.append(Gtk.Label(label="Audio:"))
        controls.append(mode_box)

        self.quality_dropdown = Gtk.DropDown.new_from_strings(QUALITIES)
        default_q = self.cfg.get("default_quality", "best")
        if default_q in QUALITIES:
            self.quality_dropdown.set_selected(QUALITIES.index(default_q))
        controls.append(Gtk.Label(label="Quality:"))
        controls.append(self.quality_dropdown)

        self.append(controls)

        note = Gtk.Label(
            label="Subtitles are provided hardcoded (burned-in) by the source ani-cli uses -- "
                  "there's no language switch. Choosing Dub plays the English dub track instead. "
                  "See Settings → Subtitles & Audio for details.",
            xalign=0, wrap=True,
        )
        note.add_css_class("anicli-empty-state")
        self.append(note)

        # --- Episode grid --------------------------------------------------
        ep_label = Gtk.Label(label="Episodes", xalign=0)
        ep_label.add_css_class("anicli-section-title")
        ep_label.set_margin_top(6)
        self.append(ep_label)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        self.ep_flow = Gtk.FlowBox()
        self.ep_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.ep_flow.set_max_children_per_line(12)
        self.ep_flow.set_row_spacing(8)
        self.ep_flow.set_column_spacing(8)
        scroller.set_child(self.ep_flow)
        self.append(scroller)

        total_eps = result.episodes or 24
        for ep in range(1, total_eps + 1):
            cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            cell.add_css_class("linked")
            play_btn = Gtk.Button(label=str(ep))
            play_btn.set_tooltip_text(f"Play episode {ep}")
            play_btn.connect("clicked", self._on_play, ep)
            dl_btn = Gtk.Button(icon_name="folder-download-symbolic")
            dl_btn.set_tooltip_text(f"Download episode {ep} for offline viewing")
            dl_btn.connect("clicked", self._on_download, ep)
            cell.append(play_btn)
            cell.append(dl_btn)
            self.ep_flow.append(cell)

    def _on_mode_toggled(self, button, name):
        if not button.get_active():
            return
        self._mode = name
        if name == "sub":
            self.dub_btn.set_active(False)
        else:
            self.sub_btn.set_active(False)

    def _on_play(self, _button, episode: int):
        dub = self._mode == "dub"
        quality = QUALITIES[self.quality_dropdown.get_selected()]
        player = self.cfg.get("player", "mpv")
        skip_intro = self.cfg.get("skip_intro", False)

        req = anicli.PlaybackRequest(
            title=self.result.title,
            episode=episode,
            dub=dub,
            quality=quality,
            player=player,
            skip_intro=skip_intro,
        )

        def worker():
            try:
                anicli.play(req)
                GLib.idle_add(self._toast, f"Playing {self.result.title} — Episode {episode}")
            except anicli.AniCliNotFound as e:
                GLib.idle_add(self._toast, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download(self, _button, episode: int):
        dub = self._mode == "dub"
        quality = QUALITIES[self.quality_dropdown.get_selected()]
        custom_dir = self.cfg.get("downloads_dir")
        root = None
        if custom_dir:
            from pathlib import Path
            root = Path(custom_dir)

        self._toast(f"Downloading {self.result.title} — Episode {episode}…")

        def worker():
            try:
                dl_backend.trigger_download(self.result.title, episode, dub=dub, quality=quality, root=root)
                GLib.idle_add(self._toast, f"Download started for Episode {episode} — check Offline Library")
            except RuntimeError as e:
                GLib.idle_add(self._toast, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _toast(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=3))
        return False
