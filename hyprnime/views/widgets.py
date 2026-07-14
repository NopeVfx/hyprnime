import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio

from ..backend import anilist


def load_texture_async(url: str, on_ready):
    """Fetch an image URL in a background thread, then hand a Gdk.Texture
    back to on_ready() on the GTK main thread. Never blocks the UI."""
    if not url:
        return

    def worker():
        data = anilist.fetch_image_bytes(url)
        if not data:
            return
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        except GLib.Error:
            return
        GLib.idle_add(on_ready, texture)

    threading.Thread(target=worker, daemon=True).start()


class AnimeCard(Gtk.Button):
    """A poster card, like the grid tiles in Hayase-style launchers."""

    def __init__(self, result: "anilist.AnimeResult", on_click):
        super().__init__()
        self.result = result
        self.add_css_class("flat")
        self.add_css_class("anicli-card")
        self.set_has_frame(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(150, -1)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_size_request(150, 210)
        self.picture.add_css_class("anicli-cover")
        box.append(self.picture)

        title = Gtk.Label(label=result.title, xalign=0)
        title.add_css_class("anicli-title")
        title.set_wrap(True)
        title.set_max_width_chars(18)
        title.set_lines(2)
        title.set_ellipsize(3)  # Pango.EllipsizeMode.END
        box.append(title)

        meta_bits = []
        if result.format:
            meta_bits.append(result.format.replace("_", " ").title())
        if result.episodes:
            meta_bits.append(f"{result.episodes} ep")
        if result.score:
            meta_bits.append(f"★ {result.score / 10:.1f}")
        if meta_bits:
            meta = Gtk.Label(label=" · ".join(meta_bits), xalign=0)
            meta.add_css_class("anicli-subtitle")
            meta.add_css_class("dim-label")
            box.append(meta)

        self.set_child(box)
        self.connect("clicked", lambda *_: on_click(result))

        load_texture_async(result.cover_url, self._set_cover)

    def _set_cover(self, texture):
        self.picture.set_paintable(texture)
        return False
