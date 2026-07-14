"""Wrapper around the ani-cli shell tool.

ani-cli becomes fully non-interactive (no fzf/rofi/terminal prompt needed)
as soon as you give it BOTH -S <index> (select-nth search result) and
-e <episode>. That's what makes it possible to drive it from a GUI with
zero terminal interaction: mpv (or vlc) just opens as its own window.

Known, real limitations of ani-cli itself (not something this app can
work around, see the ani-cli FAQ):
  * Subtitles are hardcoded/burned into the video by the source
    (allanime). There is no language switch and no way to disable them.
  * Dub audio is English-only; there's no dub-language choice.
"""
import os
import shutil
import subprocess
from dataclasses import dataclass


class AniCliNotFound(RuntimeError):
    pass


def is_installed() -> bool:
    return shutil.which("ani-cli") is not None


def mpv_installed() -> bool:
    return shutil.which("mpv") is not None


def vlc_installed() -> bool:
    return shutil.which("vlc") is not None


@dataclass
class PlaybackRequest:
    title: str
    episode: int
    dub: bool = False
    quality: str = "best"
    player: str = "mpv"       # mpv | vlc
    skip_intro: bool = False
    search_index: int = 1     # which search result to auto-select


def build_command(req: PlaybackRequest) -> list[str]:
    cmd = ["ani-cli", req.title, "-S", str(req.search_index), "-e", str(req.episode), "-q", req.quality]
    if req.dub:
        cmd.append("--dub")
    if req.player == "vlc":
        cmd.append("--vlc")
    return cmd


def play(req: PlaybackRequest):
    """Launch ani-cli detached, fully non-interactive. Never opens a terminal."""
    if not is_installed():
        raise AniCliNotFound("ani-cli was not found on PATH. Install it first (see README).")

    env = os.environ.copy()
    if req.skip_intro:
        env["ANI_CLI_SKIP_INTRO"] = "1"

    cmd = build_command(req)
    # start_new_session detaches the child so closing this app doesn't kill playback,
    # and stdio is discarded since there is no terminal to show it in.
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
