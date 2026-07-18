import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from .. import config
from ..backend import anicli
from ..theming.manager import ThemeManager

COLOR_SCHEMES = [("system", "Follow System"), ("light", "Light"), ("dark", "Dark")]
QUALITIES = ["best", "1080", "720", "480", "360", "worst"]
PLAYERS = [("mpv", "mpv"), ("vlc", "VLC")]


class SettingsView(Adw.PreferencesPage):
    def __init__(self, theme_manager: ThemeManager, toast_overlay: Adw.ToastOverlay = None):
        super().__init__()
        self.theme_manager = theme_manager
        self.toast_overlay = toast_overlay
        self.cfg = config.load()

        self._build_appearance_group()
        self._build_playback_group()
        self._build_subtitles_group()
        self._build_party_group()
        self._build_offline_group()
        self._build_advanced_group()

    # ------------------------------------------------------------------
    def _build_appearance_group(self):
        group = Adw.PreferencesGroup(title="Appearance", description="Pick a base mode, then optionally layer a colour scheme on top.")

        scheme_row = Adw.ComboRow(title="Mode", subtitle="Light, dark, or match your desktop")
        scheme_model = Gtk.StringList.new([label for _id, label in COLOR_SCHEMES])
        scheme_row.set_model(scheme_model)
        current_scheme = self.cfg.get("color_scheme", "system")
        ids = [i for i, _ in COLOR_SCHEMES]
        scheme_row.set_selected(ids.index(current_scheme) if current_scheme in ids else 0)
        scheme_row.connect("notify::selected", self._on_scheme_changed)
        self._scheme_ids = ids
        group.add(scheme_row)

        theme_row = Adw.ComboRow(title="Custom Theme", subtitle="Everforest, Tokyo Night, Catppuccin, Gruvbox, Nord and more")
        # ThemeManager.list_themes() returns [(id, (display_name, is_dark)), ...]
        themes = ThemeManager.list_themes()
        self._theme_ids = ["none"] + [tid for tid, _info in themes]
        display_names = ["None (plain Adwaita)"] + [name for _tid, (name, _dark) in themes]
        theme_row.set_model(Gtk.StringList.new(display_names))
        current_theme = self.cfg.get("custom_theme", "none")
        theme_row.set_selected(self._theme_ids.index(current_theme) if current_theme in self._theme_ids else 0)
        theme_row.connect("notify::selected", self._on_theme_changed)
        group.add(theme_row)

        self.add(group)

    def _on_scheme_changed(self, row, _pspec):
        scheme_id = self._scheme_ids[row.get_selected()]
        self.cfg = config.set_value("color_scheme", scheme_id)
        self._apply_theme_safely()

    def _on_theme_changed(self, row, _pspec):
        theme_id = self._theme_ids[row.get_selected()]
        self.cfg = config.set_value("custom_theme", theme_id)
        self._apply_theme_safely()

    def _apply_theme_safely(self):
        """theme_manager.apply() touches CSS providers and the display --
        if that ever fails (bad/missing CSS file, GTK error) it must not
        fail *silently*, or picking a theme just looks like it does
        nothing with no clue why."""
        try:
            self.theme_manager.apply(self.cfg["color_scheme"], self.cfg["custom_theme"])
        except Exception as exc:  # noqa: BLE001 -- surfacing this beats hiding it
            self._toast(f"Couldn't apply theme: {exc}")
        else:
            if self.cfg["custom_theme"] != "none":
                self._toast(f"Theme applied: {self.cfg['custom_theme']}")

    def _toast(self, message: str):
        if self.toast_overlay is not None:
            self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    # ------------------------------------------------------------------
    def _build_playback_group(self):
        group = Adw.PreferencesGroup(title="Playback", description="Defaults used for every new episode you play.")

        mode_row = Adw.ComboRow(title="Default audio", subtitle="Can still be changed per-anime")
        mode_row.set_model(Gtk.StringList.new(["Sub (Japanese + hardcoded subtitles)", "Dub (English)"]))
        mode_row.set_selected(1 if self.cfg.get("default_mode") == "dub" else 0)
        mode_row.connect("notify::selected", lambda r, _p: config.set_value(
            "default_mode", "dub" if r.get_selected() == 1 else "sub"))
        group.add(mode_row)

        quality_row = Adw.ComboRow(title="Default quality")
        quality_row.set_model(Gtk.StringList.new(QUALITIES))
        cur_q = self.cfg.get("default_quality", "best")
        quality_row.set_selected(QUALITIES.index(cur_q) if cur_q in QUALITIES else 0)
        quality_row.connect("notify::selected", lambda r, _p: config.set_value(
            "default_quality", QUALITIES[r.get_selected()]))
        group.add(quality_row)

        player_row = Adw.ComboRow(title="Media player")
        player_row.set_model(Gtk.StringList.new([label for _id, label in PLAYERS]))
        player_ids = [i for i, _ in PLAYERS]
        cur_p = self.cfg.get("player", "mpv")
        player_row.set_selected(player_ids.index(cur_p) if cur_p in player_ids else 0)
        player_row.connect("notify::selected", lambda r, _p: config.set_value(
            "player", player_ids[r.get_selected()]))
        group.add(player_row)

        skip_row = Adw.SwitchRow(title="Skip intros", subtitle="Uses ani-skip when available (mpv only)")
        skip_row.set_active(bool(self.cfg.get("skip_intro", False)))
        skip_row.connect("notify::active", lambda r, _p: config.set_value("skip_intro", r.get_active()))
        group.add(skip_row)

        self.add(group)

    # ------------------------------------------------------------------
    def _build_subtitles_group(self):
        group = Adw.PreferencesGroup(
            title="Subtitles & Audio Language",
            description="What's actually configurable, and what isn't.",
        )

        info = Adw.ActionRow(
            title="Subtitles are hardcoded by the source",
            subtitle=(
                "ani-cli streams from allanime, which burns subtitles directly into the "
                "video. There is no subtitle language switch and no way to turn them off "
                "-- this is a limitation of the source, not this app. The only real "
                "language choice is Sub (Japanese audio) vs Dub (English audio), set above."
            ),
        )
        info.set_icon_name("dialog-information-symbolic")
        group.add(info)

        self.add(group)

    # ------------------------------------------------------------------
    def _build_party_group(self):
        group = Adw.PreferencesGroup(
            title="Watch Party",
            description="Playback sync runs on Syncplay. Party discovery (search by name) needs "
                        "a Party Directory server -- self-host one with "
                        "'python3 -m hyprnime.partydirectory', see README.",
        )

        name_row = Adw.EntryRow(title="Your display name")
        name_row.set_text(self.cfg.get("party_username", ""))
        name_row.connect("changed", lambda r: config.set_value("party_username", r.get_text().strip()))
        group.add(name_row)

        syncplay_row = Adw.EntryRow(title="Syncplay server (host:port)")
        syncplay_row.set_text(self.cfg.get("syncplay_server", "syncplay.pl:8999"))
        syncplay_row.connect("changed", lambda r: config.set_value("syncplay_server", r.get_text().strip()))
        group.add(syncplay_row)

        directory_row = Adw.EntryRow(title="Party Directory server URL")
        directory_row.set_text(self.cfg.get("directory_server", ""))
        directory_row.connect("changed", lambda r: config.set_value("directory_server", r.get_text().strip()))
        group.add(directory_row)

        self.add(group)

    # ------------------------------------------------------------------
    def _build_offline_group(self):
        group = Adw.PreferencesGroup(
            title="Offline Mode",
            description="Downloaded episodes play with mpv directly -- no ani-cli or network needed.",
        )

        from ..backend import downloads as dl_backend
        dir_row = Adw.EntryRow(title="Downloads folder")
        dir_row.set_text(self.cfg.get("downloads_dir", "") or str(dl_backend.default_downloads_root()))
        dir_row.connect("changed", lambda r: config.set_value("downloads_dir", r.get_text().strip()))
        group.add(dir_row)

        self.add(group)

    # ------------------------------------------------------------------
    def _build_advanced_group(self):
        group = Adw.PreferencesGroup(title="Advanced")

        anicli_row = Adw.ActionRow(title="ani-cli")
        anicli_row.set_subtitle("Found on PATH" if anicli.is_installed() else "Not found -- install it, see README")
        anicli_row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if anicli.is_installed() else "dialog-warning-symbolic"))
        group.add(anicli_row)

        mpv_row = Adw.ActionRow(title="mpv")
        mpv_row.set_subtitle("Found on PATH" if anicli.mpv_installed() else "Not found")
        mpv_row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if anicli.mpv_installed() else "dialog-warning-symbolic"))
        group.add(mpv_row)

        vlc_row = Adw.ActionRow(title="VLC")
        vlc_row.set_subtitle("Found on PATH" if anicli.vlc_installed() else "Not found (optional)")
        vlc_row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if anicli.vlc_installed() else "dialog-warning-symbolic"))
        group.add(vlc_row)

        from ..backend import syncplay_backend as sp
        syncplay_row = Adw.ActionRow(title="Syncplay")
        syncplay_row.set_subtitle("Found on PATH" if sp.syncplay_installed() else "Not found -- needed for Watch Party")
        syncplay_row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if sp.syncplay_installed() else "dialog-warning-symbolic"))
        group.add(syncplay_row)

        hist_row = Adw.ActionRow(title="Watch history file")
        from ..backend import history as history_mod
        hist_row.set_subtitle(str(history_mod.histfile_path()))
        group.add(hist_row)

        self.add(group)
