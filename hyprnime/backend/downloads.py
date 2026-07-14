"""Offline mode: download episodes with ani-cli's own -d flag and keep
a scannable local library, so playback later needs no network and no
ani-cli call at all -- just mpv pointed at a local file.
"""
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi"}

# ani-cli names downloaded files "<Title>Episode <N>.mp4" (no space between
# title and "Episode" -- see its --force-media-title pattern). We parse
# tolerantly: if a file doesn't match, it's still listed, just unparsed.
_EPISODE_RE = re.compile(r"^(?P<title>.*?)Episode\s*(?P<ep>\d+)$", re.IGNORECASE)


@dataclass
class DownloadedEpisode:
    path: Path
    anime_title: str
    episode: str
    size_bytes: int


def default_downloads_root() -> Path:
    return Path.home() / "Videos" / "Hyprnime"


def sanitize_dirname(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return cleaned or "Unknown"


def anime_download_dir(root: Path, anime_title: str) -> Path:
    return root / sanitize_dirname(anime_title)


def trigger_download(anime_title: str, episode: int, dub: bool = False,
                      quality: str = "best", root: Path | None = None,
                      search_index: int = 1):
    """Fire-and-forget: shells out to `ani-cli -d`, saving into a
    per-anime subfolder of the downloads root. No terminal is opened."""
    if shutil.which("ani-cli") is None:
        raise RuntimeError("ani-cli was not found on PATH.")

    root = root or default_downloads_root()
    target_dir = anime_download_dir(root, anime_title)
    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["ani-cli", anime_title, "-S", str(search_index), "-e", str(episode), "-q", quality, "-d"]
    if dub:
        cmd.append("--dub")

    env = os.environ.copy()
    env["ANI_CLI_DOWNLOAD_DIR"] = str(target_dir)

    return subprocess.Popen(
        cmd, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def scan_library(root: Path | None = None) -> list[DownloadedEpisode]:
    root = root or default_downloads_root()
    if not root.exists():
        return []
    results = []
    for anime_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for file in sorted(anime_dir.iterdir()):
            if file.suffix.lower() not in VIDEO_EXTS:
                continue
            stem = file.stem
            match = _EPISODE_RE.match(stem)
            if match:
                title = match.group("title").strip() or anime_dir.name
                ep = match.group("ep")
            else:
                title = anime_dir.name
                ep = stem
            try:
                size = file.stat().st_size
            except OSError:
                size = 0
            results.append(DownloadedEpisode(path=file, anime_title=title, episode=ep, size_bytes=size))
    return results


def play_offline(path: Path, player: str = "mpv"):
    binary = "mpv" if player != "vlc" else "vlc"
    if shutil.which(binary) is None:
        raise RuntimeError(f"{binary} was not found on PATH.")
    return subprocess.Popen(
        [binary, str(path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def delete_download(path: Path):
    path.unlink(missing_ok=True)
