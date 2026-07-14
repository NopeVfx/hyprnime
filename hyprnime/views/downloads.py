from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from .. import config
from ..backend import downloads as dl


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class DownloadsView(Gtk.Box):
    def __init__(self, toast_overlay: Adw.ToastOverlay):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.toast_overlay = toast_overlay
        self.cfg = config.load()
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(18)
        self.set_margin_end(18)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label="Offline Library", xalign=0, hexpand=True)
        title.add_css_class("anicli-hero-title")
        header.append(title)
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.append(refresh_btn)
        self.append(header)

        self.root_label = Gtk.Label(xalign=0)
        self.root_label.add_css_class("dim-label")
        self.append(self.root_label)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("anicli-empty-state")
        self.append(self.status)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.set_child(self.list_box)
        self.append(scroller)

        self.refresh()

    def _downloads_root(self) -> Path:
        custom = self.cfg.get("downloads_dir")
        return Path(custom) if custom else dl.default_downloads_root()

    def refresh(self):
        self.cfg = config.load()
        root = self._downloads_root()
        self.root_label.set_label(f"Folder: {root}")
        for child in list(self.list_box):
            self.list_box.remove(child)

        episodes = dl.scan_library(root)
        if not episodes:
            self.status.set_label(
                "Nothing downloaded yet. Use the Download button on an anime's episode list."
            )
            return
        self.status.set_label(f"{len(episodes)} episode(s) available offline")

        by_anime: dict[str, list[dl.DownloadedEpisode]] = {}
        for ep in episodes:
            by_anime.setdefault(ep.anime_title, []).append(ep)

        for anime_title, eps in sorted(by_anime.items()):
            header_row = Adw.ActionRow(title=anime_title, subtitle=f"{len(eps)} episode(s) downloaded")
            header_row.add_css_class("anicli-section-title")
            self.list_box.append(header_row)
            for ep in sorted(eps, key=lambda e: e.episode):
                self.list_box.append(self._build_episode_row(ep))

    def _build_episode_row(self, ep: dl.DownloadedEpisode) -> Gtk.Widget:
        row = Adw.ActionRow(title=f"Episode {ep.episode}", subtitle=_human_size(ep.size_bytes))

        play_btn = Gtk.Button(icon_name="media-playback-start-symbolic")
        play_btn.set_valign(Gtk.Align.CENTER)
        play_btn.connect("clicked", lambda *_: self._play(ep))
        row.add_suffix(play_btn)

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.add_css_class("flat")
        delete_btn.connect("clicked", lambda *_: self._delete(ep))
        row.add_suffix(delete_btn)

        return row

    def _play(self, ep: dl.DownloadedEpisode):
        try:
            dl.play_offline(ep.path, player=self.cfg.get("player", "mpv"))
            self._toast(f"Playing {ep.anime_title} — Episode {ep.episode} (offline)")
        except RuntimeError as exc:
            self._toast(str(exc))

    def _delete(self, ep: dl.DownloadedEpisode):
        dl.delete_download(ep.path)
        self._toast(f"Removed {ep.anime_title} — Episode {ep.episode}")
        self.refresh()

    def _toast(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=3))
