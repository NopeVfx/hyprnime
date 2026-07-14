"""Simple JSON-backed settings store for Hyprnime."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hyprnime"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "color_scheme": "system",      # system | light | dark
    "custom_theme": "none",        # "none" or a theme id from theming.manager.THEMES
    "default_mode": "sub",         # sub | dub
    "default_quality": "best",     # best | worst | 360 | 480 | 720 | 1080
    "player": "mpv",               # mpv | vlc
    "skip_intro": False,
    # Watch Party
    "party_username": "",          # shown to other party members; random name used if blank
    "syncplay_server": "syncplay.pl:8999",
    "directory_server": "",        # e.g. "http://192.168.1.20:8730" -- self-hosted, see partydirectory.py
    # Offline mode
    "downloads_dir": "",           # blank = ~/Videos/Hyprnime (see backend/downloads.py)
}


def load():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save(DEFAULTS)
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def set_value(key: str, value):
    cfg = load()
    cfg[key] = value
    save(cfg)
    return cfg
