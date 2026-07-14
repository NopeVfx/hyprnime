"""Reads ani-cli's own history file so the launcher can show
'Continue Watching' the same way Hayase-style launchers do.

ani-cli stores history at $ANI_CLI_HIST_DIR/ani-cli/histfile
(default $XDG_STATE_HOME/ani-cli/histfile, or ~/.local/state/ani-cli/histfile).
Each line is tab-separated: episode_number, allanime_id, title
"""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HistoryEntry:
    episode: str
    anime_id: str
    title: str


def histfile_path() -> Path:
    hist_dir = os.environ.get("ANI_CLI_HIST_DIR")
    if not hist_dir:
        state_home = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
        hist_dir = state_home
    return Path(hist_dir) / "ani-cli" / "histfile"


def read_history(limit: int = 20) -> list[HistoryEntry]:
    path = histfile_path()
    if not path.exists():
        return []
    entries = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    except OSError:
        return []

    # Most recently watched last in the file -> show newest first.
    for line in reversed(lines):
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ep_no, anime_id, title = parts[0], parts[1], parts[2]
        entries.append(HistoryEntry(episode=ep_no, anime_id=anime_id, title=title))
        if len(entries) >= limit:
            break
    return entries
